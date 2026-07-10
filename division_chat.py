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


def div_send_message(match_id: int, sender_id: int, text: str) -> tuple[bool, str]:
    """Sabablar: ok, match_not_found, not_participant, empty, too_long."""
    text = (text or "").strip()
    if not text:
        return False, "empty"
    if len(text) > MAX_MESSAGE_LEN:
        return False, "too_long"
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _match_participants(cursor, match_id)
        if parts is None:
            return False, "match_not_found"
        if sender_id not in parts:
            return False, "not_participant"
        cursor.execute(
            "INSERT INTO div_messages (match_id, sender_id, text) VALUES (?, ?, ?)",
            (match_id, sender_id, text),
        )
        conn.commit()
        return True, "ok"
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
        cursor.execute(
            "SELECT dm.id, dm.sender_id, dm.text, dm.created_at "
            "FROM div_messages dm WHERE dm.match_id = ? ORDER BY dm.id",
            (match_id,),
        )
        out = []
        for r in cursor.fetchall():
            d = dict(r)
            d["mine"] = d["sender_id"] == requester_id
            d["is_read"] = True   # Divizionda o'qilganlik kuzatilmaydi — ✓✓ ko'rsatiladi
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
            return {"online": False, "typing": False,
                    "last_seen_seconds": None, "opponent_username": None}
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
                "opponent_username": username}
    finally:
        conn.close()
