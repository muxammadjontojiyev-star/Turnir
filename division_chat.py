"""
division_chat.py — Divizion o'yin ichidagi sodda chat (bot chati).

Faqat o'yin ishtirokchilari yozishi/o'qishi mumkin (qoida #34).
Matn WebApp'da escHtml bilan chiqariladi (frontend, qoida #35); bazaga xom
saqlanadi (liga chat bilan bir xil yondashuv).
"""

from models import get_connection

MAX_MESSAGE_LEN = 500


def _match_participants(cursor, match_id: int) -> tuple[int, int | None] | None:
    cursor.execute(
        "SELECT player1_id, player2_id FROM div_matches WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return row["player1_id"], row["player2_id"]


def div_send_message(match_id: int, sender_id: int,
                     text: str) -> tuple[bool, str, dict | None]:
    """
    Divizion chatiga xabar yozadi.

    Qaytaradi: (ok, sabab, notify)
      notify — raqibga bot bildirishnomasi uchun (liga bilan bir xil shakl):
        {"recipient_telegram_id": ..., "text_preview": "..."}
      Bye o'yinda (raqib yo'q) yoki xatoda None.

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
        parts = _match_participants(cursor, match_id)
        if parts is None:
            return False, "match_not_found", None
        if sender_id not in parts:
            return False, "not_participant", None
        cursor.execute(
            "INSERT INTO div_messages (match_id, sender_id, text) VALUES (?, ?, ?)",
            (match_id, sender_id, text),
        )
        conn.commit()

        # Raqibning telegram_id'si (bot bildirishnomasi uchun)
        opp_id = parts[1] if parts[0] == sender_id else parts[0]
        notify = None
        if opp_id is not None:      # bye o'yinda raqib yo'q
            cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (opp_id,))
            row = cursor.fetchone()
            if row and row["telegram_id"]:
                preview = text if len(text) <= 80 else text[:77] + "…"
                notify = {"recipient_telegram_id": row["telegram_id"],
                          "text_preview": preview}
        return True, "ok", notify
    finally:
        conn.close()


def div_get_messages(match_id: int, requester_id: int) -> list[dict] | None:
    """
    Xabarlar liga chat formatida (frontend renderWebChatMessages bilan mos):
      {id, text, created_at, mine (bool), is_read (bool), club_name: None}
    Ishtirokchi bo'lmasa None (qoida #34).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _match_participants(cursor, match_id)
        if parts is None or requester_id not in parts:
            return None
        # Raqib yozgan xabarlarni MEN o'qidim — belgilaymiz (✓✓ raqibda paydo bo'ladi)
        cursor.execute(
            "UPDATE div_messages SET is_read = 1 "
            "WHERE match_id = ? AND sender_id != ? AND is_read = 0",
            (match_id, requester_id),
        )
        conn.commit()
        cursor.execute(
            "SELECT dm.id, dm.sender_id, dm.text, dm.created_at, dm.is_read "
            "FROM div_messages dm WHERE dm.match_id = ? ORDER BY dm.id",
            (match_id,),
        )
        out = []
        for r in cursor.fetchall():
            d = dict(r)
            d["mine"] = d["sender_id"] == requester_id
            d["is_read"] = bool(d["is_read"])  # haqiqiy o'qilganlik (✓ / ✓✓)
            d["club_name"] = None  # Divizionda klub yo'q
            out.append(d)
        return out
    finally:
        conn.close()


# --- Typing / holat (liga chat header'i bilan mos, engil in-memory) ---
import time as _time

_DIV_TYPING: dict[tuple[int, int], float] = {}  # (match_id, user_id) -> timestamp
_TYPING_THRESHOLD_SECONDS = 6


def div_set_typing(match_id: int, user_id: int) -> bool:
    """'Yozmoqda' signali. Ishtirokchi bo'lmasa False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _match_participants(cursor, match_id)
    finally:
        conn.close()
    if parts is None or user_id not in parts:
        return False
    _DIV_TYPING[(match_id, user_id)] = _time.time()
    return True


def div_get_chat_state(match_id: int, requester_id: int) -> dict | None:
    """
    Chat header holati (liga get_chat_state shakli):
      {"online": bool, "typing": bool, "last_seen_seconds": int|None,
       "opponent_username": str|None}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _match_participants(cursor, match_id)
        if parts is None or requester_id not in parts:
            return None
        opp_id = parts[1] if parts[0] == requester_id else parts[0]
        if opp_id is None:  # bye o'yin — raqib yo'q
            return {"online": False, "typing": False, "last_seen_seconds": None,
                    "opponent_username": None, "opponent_user_id": None}
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
        typing = (_time.time() - _DIV_TYPING.get((match_id, opp_id), 0)
                  ) <= _TYPING_THRESHOLD_SECONDS
        return {"online": online, "typing": typing,
                "last_seen_seconds": 0 if online else last_seen_seconds,
                "opponent_username": username, "opponent_user_id": opp_id}
    finally:
        conn.close()


def div_count_unread(user_id: int) -> dict:
    """
    2026-07-19: Divizion o'qilmagan xabarlar soni (qizil rozetka).
    Liga queries_chat.count_unread_messages naqshi, div_matches/div_messages ustida.
    Faqat AKTIV (pending/awaiting_confirmation) o'yinlardagi, raqib yuborgan,
    o'qilmagan xabarlar sanaladi.

    Qaytaradi: {"total": int, "by_match": {match_id: count, ...}}
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT msg.match_id AS match_id, COUNT(*) AS cnt
            FROM div_messages msg
            JOIN div_matches m ON m.id = msg.match_id
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
        by_match[d["match_id"]] = d["cnt"]
        total += d["cnt"]
    return {"total": total, "by_match": by_match}
