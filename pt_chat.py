"""
pt_chat.py — SHAXSIY turnir o'yin chati (2026-10-02, 4b). el_chat.py naqshi.

Javob formatlari api.js openWebChat bilan mos (rasmiy turnirlar chati qayta ishlatiladi).
Ruxsat: faqat shu o'yin ishtirokchilari (qoida #34). Guruhda kelajak turlarning
chati yopiq (round_closed) — joriy va o'tgan turlar ochiq. Matn bazaga XOM yoziladi,
ko'rsatishda haqoratli so'zlar "***" (mask_text); frontend escHtml qiladi (qoida #35).
"""

import time as _time

from models import get_connection
from profanity import mask_text

MAX_MESSAGE_LEN = 500
_PREVIEW_LEN = 80
_TYPING_SECONDS = 6
_ONLINE_SECONDS = 70
_TYPING: dict[tuple[int, int], float] = {}     # (match_id, user_id) -> vaqt


def _match(cursor, match_id: int):
    cursor.execute(
        "SELECT m.player1_id, m.player2_id, m.stage, m.round, t.current_round, t.status, t.name "
        "FROM pt_matches m JOIN pt_tournaments t ON t.id = m.tournament_id WHERE m.id = ?", (match_id,))
    r = cursor.fetchone()
    if r is None or not r["player1_id"] or not r["player2_id"]:
        return None
    return r


def _open(m) -> bool:
    """Guruhda joriy/o'tgan tur ochiq; pley-off (5-bosqich) — juftlik to'lgan bo'lsa ochiq."""
    if m["status"] not in ("running", "finished"):
        return False
    return m["stage"] != "group" or m["round"] <= m["current_round"]


def pt_send_message(match_id: int, sender_id: int, text: str) -> tuple[bool, str, dict | None]:
    """(ok, sabab, notify). Sabablar: empty, too_long, match_not_found, not_participant, round_closed."""
    text = (text or "").strip()
    if not text:
        return False, "empty", None
    if len(text) > MAX_MESSAGE_LEN:
        return False, "too_long", None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _match(cursor, match_id)
        if m is None:
            return False, "match_not_found", None
        if sender_id not in (m["player1_id"], m["player2_id"]):
            return False, "not_participant", None
        if not _open(m):
            return False, "round_closed", None
        cursor.execute("INSERT INTO pt_messages (match_id, sender_id, text) VALUES (?, ?, ?)",
                       (match_id, sender_id, text))
        conn.commit()
        opp = m["player2_id"] if m["player1_id"] == sender_id else m["player1_id"]
        cursor.execute("SELECT telegram_id, language FROM users WHERE id = ?", (opp,))
        o = cursor.fetchone()
    finally:
        conn.close()
    if not o:
        return True, "ok", None
    safe, _ = mask_text(text)
    preview = safe if len(safe) <= _PREVIEW_LEN else safe[:_PREVIEW_LEN - 3] + "…"
    return True, "ok", {"recipient_telegram_id": o["telegram_id"], "language": o["language"],
                        "text_preview": preview}


def pt_get_messages(match_id: int, requester_id: int) -> list[dict] | None:
    """Xabarlar (openWebChat formati). Ruxsatsiz yoki yopiq bo'lsa None. Raqibnikini o'qildi qiladi."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _match(cursor, match_id)
        if m is None or requester_id not in (m["player1_id"], m["player2_id"]) or not _open(m):
            return None
        cursor.execute("UPDATE pt_messages SET is_read = 1, read_at = datetime('now') "
                       "WHERE match_id = ? AND sender_id != ? AND is_read = 0", (match_id, requester_id))
        conn.commit()
        cursor.execute("SELECT id, sender_id, text, created_at, is_read FROM pt_messages "
                       "WHERE match_id = ? ORDER BY id", (match_id,))
        out = []
        for r in cursor.fetchall():
            d = dict(r)
            d["mine"] = d["sender_id"] == requester_id
            d["is_read"] = bool(d["is_read"])
            d["club_name"] = None
            d["text"], _ = mask_text(d["text"])
            out.append(d)
        return out
    finally:
        conn.close()


def pt_set_typing(match_id: int, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _match(cursor, match_id)
    finally:
        conn.close()
    if m is None or user_id not in (m["player1_id"], m["player2_id"]):
        return False
    _TYPING[(match_id, user_id)] = _time.time()
    return True


def pt_chat_state(match_id: int, requester_id: int) -> dict | None:
    """{online, typing, last_seen_seconds, opponent_username, opponent_user_id}"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        m = _match(cursor, match_id)
        if m is None or requester_id not in (m["player1_id"], m["player2_id"]):
            return None
        opp = m["player2_id"] if m["player1_id"] == requester_id else m["player1_id"]
        cursor.execute("SELECT username, (julianday('now') - julianday(last_seen)) * 86400.0 AS secs "
                       "FROM users WHERE id = ?", (opp,))
        u = cursor.fetchone()
    finally:
        conn.close()
    secs = int(u["secs"]) if u and u["secs"] is not None else None
    online = secs is not None and secs <= _ONLINE_SECONDS
    typing = (_time.time() - _TYPING.get((match_id, opp), 0)) <= _TYPING_SECONDS
    return {"online": online, "typing": typing, "last_seen_seconds": 0 if online else secs,
            "opponent_username": u["username"] if u else None, "opponent_user_id": opp}


def pt_count_unread(user_id: int) -> dict:
    """O'qilmagan xabarlar (raqibdan): {"total", "by_match": {match_id: soni}}."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT msg.match_id AS match_id, COUNT(*) AS cnt FROM pt_messages msg "
            "JOIN pt_matches m ON m.id = msg.match_id WHERE msg.is_read = 0 AND msg.sender_id != ? "
            "AND (m.player1_id = ? OR m.player2_id = ?) GROUP BY msg.match_id", (user_id, user_id, user_id))
        by_match = {r["match_id"]: r["cnt"] for r in cursor.fetchall()}
    finally:
        conn.close()
    return {"total": sum(by_match.values()), "by_match": by_match}
