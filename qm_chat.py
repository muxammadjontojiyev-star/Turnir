"""
qm_chat.py — TEZKOR O'YIN: 1v1 chat (2026-10-19). tb_chat.py naqshi; javob formatlari api.js
openWebChat bilan mos (prefiks /qm/matches). Ruxsat — faqat shu o'yinning ikki o'yinchisi (qoida #34).
Matn bazaga xom yoziladi, ko'rsatishda mask_text; frontend escHtml qiladi (qoida #35).
"""

import time as _time

from models import get_connection
from profanity import mask_text

MAX_MESSAGE_LEN = 500
_PREVIEW_LEN = 80
_TYPING_SECONDS = 6
_ONLINE_SECONDS = 70
_TYPING: dict[tuple[int, int], float] = {}


def _players(cur, match_id: int):
    return cur.execute("SELECT player1_id AS p1, player2_id AS p2, status FROM qm_matches WHERE id = ?",
                       (match_id,)).fetchone()


def qm_send_message(match_id: int, sender_id: int, text: str) -> tuple[bool, str, dict | None]:
    """Sabablar: empty, too_long, match_not_found, not_participant."""
    text = (text or "").strip()
    if not text:
        return False, "empty", None
    if len(text) > MAX_MESSAGE_LEN:
        return False, "too_long", None
    conn = get_connection()
    cur = conn.cursor()
    try:
        g = _players(cur, match_id)
        if g is None:
            return False, "match_not_found", None
        if sender_id not in (g["p1"], g["p2"]):
            return False, "not_participant", None
        cur.execute("INSERT INTO qm_messages (match_id, sender_id, text) VALUES (?, ?, ?)", (match_id, sender_id, text))
        conn.commit()
        opp = g["p2"] if g["p1"] == sender_id else g["p1"]
        o = cur.execute("SELECT telegram_id, language FROM users WHERE id = ?", (opp,)).fetchone()
    finally:
        conn.close()
    if not o:
        return True, "ok", None
    safe, _ = mask_text(text)
    preview = safe if len(safe) <= _PREVIEW_LEN else safe[:_PREVIEW_LEN - 3] + "…"
    return True, "ok", {"recipient_telegram_id": o["telegram_id"], "language": o["language"], "text_preview": preview}


def qm_get_messages(match_id: int, requester_id: int) -> list[dict] | None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        g = _players(cur, match_id)
        if g is None or requester_id not in (g["p1"], g["p2"]):
            return None
        cur.execute("UPDATE qm_messages SET is_read = 1, read_at = datetime('now') "
                    "WHERE match_id = ? AND sender_id != ? AND is_read = 0", (match_id, requester_id))
        conn.commit()
        cur.execute("SELECT id, sender_id, text, created_at, is_read FROM qm_messages WHERE match_id = ? ORDER BY id",
                    (match_id,))
        out = []
        for r in cur.fetchall():
            d = dict(r)
            d["mine"] = d["sender_id"] == requester_id
            d["is_read"] = bool(d["is_read"])
            d["club_name"] = None
            d["text"], _ = mask_text(d["text"])
            out.append(d)
        return out
    finally:
        conn.close()


def qm_set_typing(match_id: int, user_id: int) -> bool:
    conn = get_connection()
    try:
        g = _players(conn.cursor(), match_id)
    finally:
        conn.close()
    if g is None or user_id not in (g["p1"], g["p2"]):
        return False
    _TYPING[(match_id, user_id)] = _time.time()
    return True


def qm_chat_state(match_id: int, requester_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        g = _players(cur, match_id)
        if g is None or requester_id not in (g["p1"], g["p2"]):
            return None
        opp = g["p2"] if g["p1"] == requester_id else g["p1"]
        u = cur.execute("SELECT username, (julianday('now') - julianday(last_seen)) * 86400.0 AS secs "
                        "FROM users WHERE id = ?", (opp,)).fetchone()
    finally:
        conn.close()
    secs = int(u["secs"]) if u and u["secs"] is not None else None
    online = secs is not None and secs <= _ONLINE_SECONDS
    typing = (_time.time() - _TYPING.get((match_id, opp), 0)) <= _TYPING_SECONDS
    return {"online": online, "typing": typing, "last_seen_seconds": 0 if online else secs,
            "opponent_username": u["username"] if u else None, "opponent_user_id": opp}


def qm_count_unread(user_id: int, match_id: int | None) -> int:
    if not match_id:
        return 0
    conn = get_connection()
    try:
        return conn.cursor().execute("SELECT COUNT(*) AS c FROM qm_messages WHERE match_id = ? AND sender_id != ? "
                                     "AND is_read = 0", (match_id, user_id)).fetchone()["c"]
    finally:
        conn.close()
