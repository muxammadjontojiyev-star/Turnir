"""
cl_chat.py — Chempionlar ligasi o'yin ichidagi sodda chat (bot chati).

Faqat o'yin ishtirokchilari yozishi/o'qishi mumkin (qoida #34).
Matn WebApp'da escHtml bilan chiqariladi (frontend, qoida #35); bazaga xom
saqlanadi (liga chat bilan bir xil yondashuv).
"""

from models import get_connection

MAX_MESSAGE_LEN = 500


def _match_participants(cursor, match_id: int) -> tuple[int, int | None] | None:
    cursor.execute(
        "SELECT player1_id, player2_id FROM cl_matches WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return row["player1_id"], row["player2_id"]


def _round_open(cursor, match_id: int) -> bool:
    """
    2026-07-16: O'yin turi ochiqmi? Joriy tur va o'tgan turlar (tarix) — ochiq;
    KELAJAK (hali ochilmagan) turlar — yopiq. Turlar boshlanmagan bo'lsa —
    hammasi yopiq. Yopiq turda chat ochilmasin (server tomonida ham, qoida #41).
    """
    cursor.execute("SELECT matchday, season FROM cl_matches WHERE id = ?", (match_id,))
    m = cursor.fetchone()
    if not m:
        return False
    cursor.execute(
        "SELECT started, current_matchday FROM cl_state WHERE season = ?",
        (m["season"],),
    )
    st = cursor.fetchone()
    if not st or not st["started"]:
        return False
    return m["matchday"] <= st["current_matchday"]


def cl_send_message(match_id: int, sender_id: int,
                     text: str) -> tuple[bool, str, dict | None]:
    """
    ChL chatiga xabar yozadi.

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
        if not _round_open(cursor, match_id):
            # Yopiq (hali ochilmagan) turda chatga yozib bo'lmaydi
            return False, "round_closed", None
        cursor.execute(
            "INSERT INTO cl_messages (match_id, sender_id, text) VALUES (?, ?, ?)",
            (match_id, sender_id, text),
        )
        conn.commit()

        # Raqibning telegram_id'si (bot bildirishnomasi uchun)
        opp_id = parts[1] if parts[0] == sender_id else parts[0]
        notify = None
        if opp_id is not None:      # bye o'yinda raqib yo'q
            cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (opp_id,))
            row = cursor.fetchone()
            recipient_tg = row["telegram_id"] if (row and row["telegram_id"]) else None
            if recipient_tg is None:
                # 2026-07-16: users'da topilmasa (mavsum reset / o'chirilgan
                # akkount) — cl_participants snapshotidagi telegram_id (zaxira).
                # Shu bilan ChL chat bildirishnomasi har doim yetkaziladi.
                cursor.execute(
                    "SELECT telegram_id FROM cl_participants "
                    "WHERE user_id = ? ORDER BY season DESC LIMIT 1",
                    (opp_id,),
                )
                prow = cursor.fetchone()
                if prow and prow["telegram_id"]:
                    recipient_tg = prow["telegram_id"]
            if recipient_tg is not None:
                preview = text if len(text) <= 80 else text[:77] + "…"
                notify = {"recipient_telegram_id": recipient_tg,
                          "text_preview": preview}
        return True, "ok", notify
    finally:
        conn.close()


def cl_get_messages(match_id: int, requester_id: int) -> list[dict] | None:
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
        if not _round_open(cursor, match_id):
            # Yopiq (hali ochilmagan) turda chat ochilmaydi (server tomonida ham, qoida #41)
            return None
        # Raqib yozgan xabarlarni MEN o'qidim — belgilaymiz (✓✓ raqibda paydo bo'ladi)
        cursor.execute(
            "UPDATE cl_messages SET is_read = 1 "
            "WHERE match_id = ? AND sender_id != ? AND is_read = 0",
            (match_id, requester_id),
        )
        conn.commit()
        cursor.execute(
            "SELECT dm.id, dm.sender_id, dm.text, dm.created_at, dm.is_read "
            "FROM cl_messages dm WHERE dm.match_id = ? ORDER BY dm.id",
            (match_id,),
        )
        out = []
        for r in cursor.fetchall():
            d = dict(r)
            d["mine"] = d["sender_id"] == requester_id
            d["is_read"] = bool(d["is_read"])  # haqiqiy o'qilganlik (✓ / ✓✓)
            d["club_name"] = None  # ChL: klub logosi frontendda
            out.append(d)
        return out
    finally:
        conn.close()


# --- Typing / holat (liga chat header'i bilan mos, engil in-memory) ---
import time as _time

_CL_TYPING: dict[tuple[int, int], float] = {}  # (match_id, user_id) -> timestamp
_TYPING_THRESHOLD_SECONDS = 6


def cl_set_typing(match_id: int, user_id: int) -> bool:
    """'Yozmoqda' signali. Ishtirokchi bo'lmasa False."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        parts = _match_participants(cursor, match_id)
    finally:
        conn.close()
    if parts is None or user_id not in parts:
        return False
    _CL_TYPING[(match_id, user_id)] = _time.time()
    return True


def cl_get_chat_state(match_id: int, requester_id: int) -> dict | None:
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
        typing = (_time.time() - _CL_TYPING.get((match_id, opp_id), 0)
                  ) <= _TYPING_THRESHOLD_SECONDS
        return {"online": online, "typing": typing,
                "last_seen_seconds": 0 if online else last_seen_seconds,
                "opponent_username": username, "opponent_user_id": opp_id}
    finally:
        conn.close()


def cl_count_unread(user_id: int) -> dict:
    """
    2026-07-19: ChL o'qilmagan xabarlar soni (qizil rozetka).
    Liga queries_chat.count_unread_messages naqshi, cl_matches/cl_messages ustida.
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
            FROM cl_messages msg
            JOIN cl_matches m ON m.id = msg.match_id
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
