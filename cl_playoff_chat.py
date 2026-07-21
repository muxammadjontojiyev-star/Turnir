"""
cl_playoff_chat.py — ChL PLAY-OFF o'yin ichidagi chat (2026-07-21).

cl_chat.py (guruh o'yinlari chati) naqshi, cl_po_messages jadvali ustida.
Farqlar: kirish tekshiruvi cl_playoff_matches'da; tur (matchday) qulfi YO'Q —
play-off o'yini yaratilgan zahoti chat ochiq (2-o'yin baribir 1-o'yin
tasdiqlangach yaratiladi).

Faqat o'yin ishtirokchilari yozishi/o'qishi mumkin (qoida #34).
"""

import time as _time

from models import get_connection

MAX_MESSAGE_LEN = 500

_CLPO_TYPING: dict[tuple[int, int], float] = {}  # (match_id, user_id) -> timestamp
_TYPING_THRESHOLD_SECONDS = 6


def _po_participants(cursor, match_id: int) -> tuple[int, int] | None:
    cursor.execute(
        "SELECT player1_id, player2_id FROM cl_playoff_matches WHERE id = ?",
        (match_id,))
    row = cursor.fetchone()
    if not row or not row["player1_id"] or not row["player2_id"]:
        return None  # juftlik hali to'lmagan — chat yo'q
    return row["player1_id"], row["player2_id"]


def cl_po_send_message(match_id: int, sender_id: int,
                       text: str) -> tuple[bool, str, dict | None]:
    """
    Play-off chatiga xabar yozadi (cl_send_message bilan bir xil shakl).
    Qaytaradi: (ok, sabab, notify) — notify: {"recipient_telegram_id", "text_preview"}.
    Sabablar: ok, match_not_found, not_participant, empty, too_long.
    """
    text = (text or "").strip()
    if not text:
        return False, "empty", None
    if len(text) > MAX_MESSAGE_LEN:
        return False, "too_long", None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _po_participants(cursor, match_id)
        if parts is None:
            return False, "match_not_found", None
        if sender_id not in parts:
            return False, "not_participant", None
        cursor.execute(
            "INSERT INTO cl_po_messages (match_id, sender_id, text) VALUES (?, ?, ?)",
            (match_id, sender_id, text),
        )
        conn.commit()

        # Raqib telegram_id (bot bildirishnomasi) — cl_chat bilan bir xil zaxira
        opp_id = parts[1] if parts[0] == sender_id else parts[0]
        cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (opp_id,))
        row = cursor.fetchone()
        recipient_tg = row["telegram_id"] if (row and row["telegram_id"]) else None
        if recipient_tg is None:
            cursor.execute(
                "SELECT telegram_id FROM cl_participants "
                "WHERE user_id = ? ORDER BY season DESC LIMIT 1",
                (opp_id,),
            )
            prow = cursor.fetchone()
            if prow and prow["telegram_id"]:
                recipient_tg = prow["telegram_id"]
        notify = None
        if recipient_tg is not None:
            preview = text if len(text) <= 80 else text[:77] + "…"
            notify = {"recipient_telegram_id": recipient_tg,
                      "text_preview": preview}
        return True, "ok", notify
    finally:
        conn.close()


def cl_po_get_messages(match_id: int, requester_id: int) -> list[dict] | None:
    """
    Xabarlar liga chat formatida: {id, text, created_at, mine, is_read, club_name: None}.
    Ochilganda raqib xabarlari o'qilgan deb belgilanadi (rozetka o'chadi).
    Ishtirokchi bo'lmasa None (qoida #34).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _po_participants(cursor, match_id)
        if parts is None or requester_id not in parts:
            return None
        cursor.execute(
            "UPDATE cl_po_messages SET is_read = 1 "
            "WHERE match_id = ? AND sender_id != ? AND is_read = 0",
            (match_id, requester_id),
        )
        conn.commit()
        cursor.execute(
            "SELECT id, sender_id, text, created_at, is_read "
            "FROM cl_po_messages WHERE match_id = ? ORDER BY id",
            (match_id,),
        )
        out = []
        for r in cursor.fetchall():
            d = dict(r)
            d["mine"] = d["sender_id"] == requester_id
            d["is_read"] = bool(d["is_read"])
            d["club_name"] = None
            out.append(d)
        return out
    finally:
        conn.close()


def cl_po_set_typing(match_id: int, user_id: int) -> bool:
    """'Yozmoqda' signali (cl_chat bilan bir xil, engil in-memory)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _po_participants(cursor, match_id)
    finally:
        conn.close()
    if parts is None or user_id not in parts:
        return False
    _CLPO_TYPING[(match_id, user_id)] = _time.time()
    return True


def cl_po_get_chat_state(match_id: int, requester_id: int) -> dict | None:
    """Chat header holati (cl_get_chat_state bilan bir xil shakl)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _po_participants(cursor, match_id)
        if parts is None or requester_id not in parts:
            return None
        opp_id = parts[1] if parts[0] == requester_id else parts[0]
        cursor.execute("SELECT last_seen, username FROM users WHERE id = ?", (opp_id,))
        row = cursor.fetchone()
        online = False
        last_seen_seconds = None
        username = None
        if row is not None:
            rd = dict(row)
            username = rd.get("username")
            if rd.get("last_seen"):
                cursor.execute(
                    "SELECT (julianday('now') - julianday(?)) * 86400.0",
                    (rd["last_seen"],),
                )
                secs = cursor.fetchone()[0]
                if secs is not None:
                    last_seen_seconds = max(0, int(secs))
                    online = last_seen_seconds <= 70
        typing = (_time.time() - _CLPO_TYPING.get((match_id, opp_id), 0)
                  ) <= _TYPING_THRESHOLD_SECONDS
        return {"online": online, "typing": typing,
                "last_seen_seconds": 0 if online else last_seen_seconds,
                "opponent_username": username, "opponent_user_id": opp_id}
    finally:
        conn.close()


def cl_po_count_unread(user_id: int) -> dict:
    """
    Play-off o'qilmagan xabarlar (qizil rozetka). Kalitlar "p{id}" —
    WC wc_count_unread_messages naqshi (guruh raqamli kalitlari bilan
    to'qnashmasligi uchun). Faqat aktiv (pending/awaiting) o'yinlar.
    Qaytaradi: {"total": int, "by_match": {"p{id}": count}}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT msg.match_id AS match_id, COUNT(*) AS cnt
            FROM cl_po_messages msg
            JOIN cl_playoff_matches m ON m.id = msg.match_id
            WHERE msg.is_read = 0
              AND msg.sender_id != ?
              AND (m.player1_id = ? OR m.player2_id = ?)
              AND m.status IN ('pending', 'awaiting_confirmation')
            GROUP BY msg.match_id
            """,
            (user_id, user_id, user_id),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    by_match = {}
    total = 0
    for r in rows:
        d = dict(r)
        by_match["p" + str(d["match_id"])] = d["cnt"]
        total += d["cnt"]
    return {"total": total, "by_match": by_match}
