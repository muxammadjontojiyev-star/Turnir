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
    """Xabarlar (eski->yangi). Ishtirokchi bo'lmasa None (qoida #34)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _match_participants(cursor, match_id)
        if parts is None or requester_id not in parts:
            return None
        cursor.execute(
            "SELECT dm.id, dm.sender_id, dm.text, dm.created_at, u.nickname "
            "FROM div_messages dm JOIN users u ON u.id = dm.sender_id "
            "WHERE dm.match_id = ? ORDER BY dm.id",
            (match_id,),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
