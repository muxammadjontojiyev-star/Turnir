"""
el_chat.py — Yevropa ligasi o'yin ichidagi chat (cl_chat / cl_playoff_chat naqshi).

Bitta modul IKKI turdagi o'yinga xizmat qiladi (qoida #26 — kod takrorlanmasin):
  kind="group" — liga bosqichi (el_matches/el_messages): kelajak turlarda chat yopiq.
  kind="po"    — play-off (el_playoff_matches/el_po_messages): tur qulfi yo'q, lekin
                 juftlik to'lmagan (o'yinchi NULL) bo'lsa chat yo'q.
Faqat o'yin ishtirokchilari yozadi/o'qiydi (qoida #34), server tomonida (qoida #41).
Matn bazaga XOM saqlanadi; ko'rsatishda haqoratli so'z "***" bilan yashiriladi
(asl matn nizo hisobotida ko'rinadi). Frontend escHtml qiladi (qoida #35).
"""

import time as _time

from models import get_connection
from profanity import mask_text

MAX_MESSAGE_LEN = 500
_PREVIEW_LEN = 80
_TYPING_THRESHOLD_SECONDS = 6
_ONLINE_THRESHOLD_SECONDS = 70

# Jadval nomlari KODDAN keladi (foydalanuvchidan emas) — SQL injection yo'q (qoida #29).
# unread_prefix: play-off rozetka kalitlari "p{id}" (guruh raqamli kalitlari bilan
# to'qnashmasligi uchun — ChL /cl/matches/unread bilan bir xil format).
_KINDS = {
    "group": {"match_table": "el_matches", "msg_table": "el_messages",
              "round_lock": True, "unread_prefix": ""},
    "po":    {"match_table": "el_playoff_matches", "msg_table": "el_po_messages",
              "round_lock": False, "unread_prefix": "p"},
}

# (kind, match_id, user_id) -> timestamp. kind kalitda SHART: guruh va play-off
# o'yinlarining id'lari bir xil bo'lishi mumkin (alohida jadvallar).
_EL_TYPING: dict[tuple[str, int, int], float] = {}


def _cfg(kind: str) -> dict:
    if kind not in _KINDS:
        raise ValueError(f"el_chat: noma'lum kind {kind!r}")
    return _KINDS[kind]


def _match_row(cursor, match_id: int, kind: str = "group"):
    """O'yin qatori; play-off'da juftlik to'lmagan bo'lsa None (chat yo'q)."""
    cfg = _cfg(kind)
    extra = "matchday, season" if cfg["round_lock"] else "season"
    cursor.execute(
        f"SELECT player1_id, player2_id, {extra} FROM {cfg['match_table']} WHERE id = ?",
        (match_id,),
    )
    row = cursor.fetchone()
    if row is None or not row["player1_id"] or not row["player2_id"]:
        return None
    return row


def _round_open(cursor, m, kind: str = "group") -> bool:
    """Tur ochiqmi? Play-off'da qulf yo'q. Guruhda turlar boshlanmagan bo'lsa yopiq."""
    if not _cfg(kind)["round_lock"]:
        return True
    cursor.execute(
        "SELECT started, current_matchday FROM el_state WHERE season = ?", (m["season"],))
    st = cursor.fetchone()
    return bool(st and st["started"]) and m["matchday"] <= st["current_matchday"]


def _recipient_telegram_id(cursor, user_id: int) -> int | None:
    """Raqib telegram_id: users'dan, topilmasa el_participants snapshotidan (zaxira)."""
    cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row["telegram_id"]:
        return row["telegram_id"]
    cursor.execute(
        "SELECT telegram_id FROM el_participants WHERE user_id = ? "
        "ORDER BY season DESC LIMIT 1", (user_id,))
    prow = cursor.fetchone()
    return prow["telegram_id"] if prow and prow["telegram_id"] else None


def el_send_message(match_id: int, sender_id: int, text: str,
                    kind: str = "group") -> tuple[bool, str, dict | None]:
    """
    Qaytaradi: (ok, sabab, notify)
      notify: {"recipient_telegram_id", "text_preview"} — raqibga bot bildirishnomasi.
    Sabablar: ok, empty, too_long, match_not_found, not_participant, round_closed.
    """
    text = (text or "").strip()
    if not text:
        return False, "empty", None
    if len(text) > MAX_MESSAGE_LEN:
        return False, "too_long", None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _match_row(cursor, match_id, kind)
        if m is None:
            return False, "match_not_found", None
        parts = (m["player1_id"], m["player2_id"])
        if sender_id not in parts:
            return False, "not_participant", None
        if not _round_open(cursor, m, kind):
            return False, "round_closed", None
        cursor.execute(
            f"INSERT INTO {_cfg(kind)['msg_table']} (match_id, sender_id, text) VALUES (?, ?, ?)",
            (match_id, sender_id, text),
        )
        conn.commit()

        opp_id = parts[1] if parts[0] == sender_id else parts[0]
        recipient_tg = _recipient_telegram_id(cursor, opp_id) if opp_id else None
        if recipient_tg is None:
            return True, "ok", None
        safe, _ = mask_text(text)   # bildirishnomada ham yashiriladi (qoida #11)
        preview = safe if len(safe) <= _PREVIEW_LEN else safe[:_PREVIEW_LEN - 3] + "…"
        return True, "ok", {"recipient_telegram_id": recipient_tg, "text_preview": preview}
    finally:
        conn.close()


def el_get_messages(match_id: int, requester_id: int,
                    kind: str = "group") -> list[dict] | None:
    """
    Xabarlar liga chat formatida (renderWebChatMessages bilan mos):
      {id, sender_id, text, created_at, mine, is_read, club_name: None}
    Ishtirokchi bo'lmasa yoki tur yopiq bo'lsa None. Raqib xabarlari o'qildi deb
    belgilanadi (is_read + read_at — nizo hisoboti uchun).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _match_row(cursor, match_id, kind)
        if m is None or requester_id not in (m["player1_id"], m["player2_id"]):
            return None
        if not _round_open(cursor, m, kind):
            return None
        msg_table = _cfg(kind)["msg_table"]
        cursor.execute(
            f"UPDATE {msg_table} SET is_read = 1, read_at = datetime('now') "
            "WHERE match_id = ? AND sender_id != ? AND is_read = 0",
            (match_id, requester_id),
        )
        conn.commit()
        cursor.execute(
            "SELECT id, sender_id, text, created_at, is_read "
            f"FROM {msg_table} WHERE match_id = ? ORDER BY id",
            (match_id,),
        )
        out = []
        for r in cursor.fetchall():
            d = dict(r)
            d["mine"] = d["sender_id"] == requester_id
            d["is_read"] = bool(d["is_read"])
            d["club_name"] = None   # klub logosi frontendda
            d["text"], _ = mask_text(d["text"])
            out.append(d)
        return out
    finally:
        conn.close()


def el_set_typing(match_id: int, user_id: int, kind: str = "group") -> bool:
    """'Yozmoqda' signali (in-memory). Ishtirokchi bo'lmasa False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _match_row(cursor, match_id, kind)
    finally:
        conn.close()
    if m is None or user_id not in (m["player1_id"], m["player2_id"]):
        return False
    _EL_TYPING[(kind, match_id, user_id)] = _time.time()
    return True


def el_get_chat_state(match_id: int, requester_id: int,
                      kind: str = "group") -> dict | None:
    """
    Chat header holati: {online, typing, last_seen_seconds, opponent_username,
    opponent_user_id}. Ishtirokchi bo'lmasa None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _match_row(cursor, match_id, kind)
        if m is None or requester_id not in (m["player1_id"], m["player2_id"]):
            return None
        opp_id = m["player2_id"] if m["player1_id"] == requester_id else m["player1_id"]
        cursor.execute("SELECT last_seen, username FROM users WHERE id = ?", (opp_id,))
        row = cursor.fetchone()
        online, last_seen_seconds, username = False, None, None
        if row is not None:
            username = row["username"]
            if row["last_seen"]:
                cursor.execute(
                    "SELECT (julianday('now') - julianday(?)) * 86400.0",
                    (row["last_seen"],),
                )
                secs = cursor.fetchone()[0]
                if secs is not None:
                    last_seen_seconds = max(0, int(secs))
                    online = last_seen_seconds <= _ONLINE_THRESHOLD_SECONDS
    finally:
        conn.close()
    typing = (_time.time() - _EL_TYPING.get((kind, match_id, opp_id), 0)
              ) <= _TYPING_THRESHOLD_SECONDS
    return {"online": online, "typing": typing,
            "last_seen_seconds": 0 if online else last_seen_seconds,
            "opponent_username": username, "opponent_user_id": opp_id}


def el_count_unread(user_id: int, kind: str = "group") -> dict:
    """
    O'qilmagan xabarlar (qizil rozetka): raqib yuborgan, is_read=0.
    Status filtri yo'q — chat o'yin tasdiqlangach ham ochiq (ChL 2026-09-22 bilan bir xil).
    Qaytaradi: {"total": int, "by_match": {match_id | "p{id}": count}}
    """
    cfg = _cfg(kind)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT msg.match_id AS match_id, COUNT(*) AS cnt
            FROM {cfg['msg_table']} msg
            JOIN {cfg['match_table']} m ON m.id = msg.match_id
            WHERE msg.is_read = 0 AND msg.sender_id != ?
              AND (m.player1_id = ? OR m.player2_id = ?)
            GROUP BY msg.match_id
            """,
            (user_id, user_id, user_id),
        )
        prefix = cfg["unread_prefix"]
        by_match = {(f"{prefix}{r['match_id']}" if prefix else r["match_id"]): r["cnt"]
                    for r in cursor.fetchall()}
    finally:
        conn.close()
    return {"total": sum(by_match.values()), "by_match": by_match}
