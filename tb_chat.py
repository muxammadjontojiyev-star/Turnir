"""
tb_chat.py — "TEAMLAR JANGI": 1v1 o'yin chati (2026-10-16, 3-bosqich). pt_chat.py naqshi.

Javob formatlari api.js openWebChat bilan mos (prefiks /tb/matches). match_id = tb_games.id.
Ruxsat: faqat shu o'yinning ikki o'yinchisi (qoida #34). Yozish — bahs ochiq yoki yakunlangan
bo'lsa (kelajak turlarda o'yin hali yaratilmagan). Matn bazaga XOM yoziladi, ko'rsatishda
haqoratli so'zlar "***" (mask_text); frontend escHtml qiladi (qoida #35).
"""

import time as _time

from models import get_connection
from profanity import mask_text

MAX_MESSAGE_LEN = 500
_PREVIEW_LEN = 80
_TYPING_SECONDS = 6
_ONLINE_SECONDS = 70
_TYPING: dict[tuple[int, int], float] = {}     # (game_id, user_id) -> vaqt


def _game(cursor, game_id: int):
    cursor.execute("SELECT g.home_user_id AS p1, g.away_user_id AS p2, f.status AS fst "
                   "FROM tb_games g JOIN tb_fixtures f ON f.id = g.fixture_id WHERE g.id = ?", (game_id,))
    return cursor.fetchone()


def tb_send_message(game_id: int, sender_id: int, text: str) -> tuple[bool, str, dict | None]:
    """(ok, sabab, notify). Sabablar: empty, too_long, match_not_found, not_participant."""
    text = (text or "").strip()
    if not text:
        return False, "empty", None
    if len(text) > MAX_MESSAGE_LEN:
        return False, "too_long", None
    conn = get_connection()
    cursor = conn.cursor()
    try:
        g = _game(cursor, game_id)
        if g is None:
            return False, "match_not_found", None
        if sender_id not in (g["p1"], g["p2"]):
            return False, "not_participant", None
        cursor.execute("INSERT INTO tb_messages (match_id, sender_id, text) VALUES (?, ?, ?)",
                       (game_id, sender_id, text))
        conn.commit()
        opp = g["p2"] if g["p1"] == sender_id else g["p1"]
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


def tb_get_messages(game_id: int, requester_id: int) -> list[dict] | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        g = _game(cursor, game_id)
        if g is None or requester_id not in (g["p1"], g["p2"]):
            return None
        cursor.execute("UPDATE tb_messages SET is_read = 1, read_at = datetime('now') "
                       "WHERE match_id = ? AND sender_id != ? AND is_read = 0", (game_id, requester_id))
        conn.commit()
        cursor.execute("SELECT id, sender_id, text, created_at, is_read FROM tb_messages "
                       "WHERE match_id = ? ORDER BY id", (game_id,))
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


def tb_set_typing(game_id: int, user_id: int) -> bool:
    conn = get_connection()
    try:
        g = _game(conn.cursor(), game_id)
    finally:
        conn.close()
    if g is None or user_id not in (g["p1"], g["p2"]):
        return False
    _TYPING[(game_id, user_id)] = _time.time()
    return True


def tb_chat_state(game_id: int, requester_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        g = _game(cursor, game_id)
        if g is None or requester_id not in (g["p1"], g["p2"]):
            return None
        opp = g["p2"] if g["p1"] == requester_id else g["p1"]
        cursor.execute("SELECT username, (julianday('now') - julianday(last_seen)) * 86400.0 AS secs "
                       "FROM users WHERE id = ?", (opp,))
        u = cursor.fetchone()
    finally:
        conn.close()
    secs = int(u["secs"]) if u and u["secs"] is not None else None
    online = secs is not None and secs <= _ONLINE_SECONDS
    typing = (_time.time() - _TYPING.get((game_id, opp), 0)) <= _TYPING_SECONDS
    return {"online": online, "typing": typing, "last_seen_seconds": 0 if online else secs,
            "opponent_username": u["username"] if u else None, "opponent_user_id": opp}


def tb_count_unread(user_id: int) -> dict:
    """{"total", "by_match": {game_id: soni}} — faqat ochiq bahslardagi o'yinlar."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT msg.match_id AS match_id, COUNT(*) AS cnt FROM tb_messages msg "
            "JOIN tb_games g ON g.id = msg.match_id JOIN tb_fixtures f ON f.id = g.fixture_id "
            "WHERE msg.is_read = 0 AND msg.sender_id != ? AND f.status = 'open' "
            "AND (g.home_user_id = ? OR g.away_user_id = ?) GROUP BY msg.match_id",
            (user_id, user_id, user_id))
        by_match = {r["match_id"]: r["cnt"] for r in cursor.fetchall()}
    finally:
        conn.close()
    return {"total": sum(by_match.values()), "by_match": by_match}
