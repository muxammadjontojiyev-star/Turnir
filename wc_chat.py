"""
wc_chat.py — World Cup chati (liga chatidan alohida).

Liga queries.py'dagi chat funksiyalarining WC versiyasi: matches→wc_matches,
messages→wc_messages, chat_notify→wc_chat_notify, chat_typing→wc_chat_typing.
WC'da o'yinchi nomi: wc_registrations.team_name (liga'da registrations.club_name).

Liga chat kodiga UMUMAN tegmaydi — to'liq parallel.
"""

from models import get_connection
from queries import (
    get_user_by_telegram_id,
    CHAT_ACTIVE_MATCH_STATUSES, CHAT_NOTIFY_THROTTLE_SECONDS,
    ONLINE_THRESHOLD_SECONDS, TYPING_THRESHOLD_SECONDS,
)


def _wc_chat_access(match_id: int, requester_telegram_id: int, is_playoff: int = 0) -> dict | None:
    """
    WC chat xavfsizlik tekshiruvi (liga _chat_match_access naqshi).
    is_playoff=0 → wc_matches (guruh), is_playoff=1 → wc_playoff_matches (play-off).
    Requester shu WC matchning ishtirokchimi va match aktivmi.
    Qaytaradi: {"match_id","my_user_id","opponent_user_id","status","is_playoff"} yoki None.
    """
    table = "wc_playoff_matches" if is_playoff else "wc_matches"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT m.id AS match_id, m.status AS status,
               m.player1_id AS p1, m.player2_id AS p2,
               u1.telegram_id AS p1_tg, u2.telegram_id AS p2_tg
        FROM {table} m
        LEFT JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        WHERE m.id = ?
        """,
        (match_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    m = dict(row)
    if m["status"] not in CHAT_ACTIVE_MATCH_STATUSES:
        return None

    if m["p1_tg"] == requester_telegram_id:
        my_id, opp_id = m["p1"], m["p2"]
    elif m["p2_tg"] == requester_telegram_id:
        my_id, opp_id = m["p2"], m["p1"]
    else:
        return None

    return {
        "match_id": m["match_id"],
        "my_user_id": my_id,
        "opponent_user_id": opp_id,
        "status": m["status"],
        "is_playoff": is_playoff,
    }


def wc_send_chat_message(match_id: int, sender_telegram_id: int, text: str, is_playoff: int = 0):
    """WC chat xabarini yozadi. Liga send_chat_message naqshi. Qaytaradi: (ok, reason, notify)."""
    text = (text or "").strip()
    if not text:
        return False, "empty", None
    if len(text) > 2000:
        text = text[:2000]

    access = _wc_chat_access(match_id, sender_telegram_id, is_playoff)
    if access is None:
        return False, "no_access", None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO wc_messages (match_id, sender_id, text, is_playoff) VALUES (?, ?, ?, ?)",
        (match_id, access["my_user_id"], text, is_playoff),
    )
    conn.commit()

    cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (access["opponent_user_id"],))
    opp_row = cursor.fetchone()
    recipient_tg = dict(opp_row)["telegram_id"] if opp_row else None

    notify = None
    if recipient_tg is not None:
        cursor.execute(
            "SELECT last_notified_at FROM wc_chat_notify WHERE match_id = ? AND recipient_id = ? AND is_playoff = ?",
            (match_id, access["opponent_user_id"], is_playoff),
        )
        nrow = cursor.fetchone()
        send_it = True
        if nrow is not None:
            last = dict(nrow).get("last_notified_at")
            if last:
                cursor.execute("SELECT (julianday('now') - julianday(?)) * 86400.0", (last,))
                elapsed = cursor.fetchone()[0]
                if elapsed is not None and elapsed < CHAT_NOTIFY_THROTTLE_SECONDS:
                    send_it = False

        if send_it:
            cursor.execute(
                "INSERT INTO wc_chat_notify (match_id, recipient_id, is_playoff, last_notified_at) "
                "VALUES (?, ?, ?, datetime('now')) "
                "ON CONFLICT(match_id, recipient_id, is_playoff) DO UPDATE SET last_notified_at = datetime('now')",
                (match_id, access["opponent_user_id"], is_playoff),
            )
            conn.commit()
            preview = text if len(text) <= 50 else text[:50] + "..."
            notify = {"recipient_telegram_id": recipient_tg, "text_preview": preview}

    conn.close()
    return True, "ok", notify


def wc_count_unread_messages(requester_telegram_id: int) -> dict:
    """WC o'qilmagan xabarlar soni. Format: {"total", "by_match"}.
    Guruh matchlari kaliti — match_id (son). Play-off matchlari kaliti — "p{match_id}"
    (guruh/play-off ID to'qnashuvidan qochish uchun)."""
    user = get_user_by_telegram_id(requester_telegram_id)
    if user is None:
        return {"total": 0, "by_match": {}}
    my_id = user["id"]

    conn = get_connection()
    cursor = conn.cursor()
    # Guruh o'yinlari o'qilmagan xabarlari
    cursor.execute(
        """
        SELECT msg.match_id AS match_id, COUNT(*) AS cnt
        FROM wc_messages msg
        JOIN wc_matches m ON m.id = msg.match_id
        WHERE msg.is_read = 0
          AND msg.is_playoff = 0
          AND msg.sender_id != ?
          AND (m.player1_id = ? OR m.player2_id = ?)
          AND m.status IN ('pending', 'awaiting_confirmation')
        GROUP BY msg.match_id
        """,
        (my_id, my_id, my_id),
    )
    group_rows = cursor.fetchall()

    # Play-off o'yinlari o'qilmagan xabarlari (alohida jadval)
    cursor.execute(
        """
        SELECT msg.match_id AS match_id, COUNT(*) AS cnt
        FROM wc_messages msg
        JOIN wc_playoff_matches m ON m.id = msg.match_id
        WHERE msg.is_read = 0
          AND msg.is_playoff = 1
          AND msg.sender_id != ?
          AND (m.player1_id = ? OR m.player2_id = ?)
          AND m.status IN ('pending', 'awaiting_confirmation')
        GROUP BY msg.match_id
        """,
        (my_id, my_id, my_id),
    )
    playoff_rows = cursor.fetchall()
    conn.close()

    by_match = {}
    total = 0
    for r in group_rows:
        d = dict(r)
        by_match[d["match_id"]] = d["cnt"]
        total += d["cnt"]
    for r in playoff_rows:
        d = dict(r)
        by_match[f"p{d['match_id']}"] = d["cnt"]
        total += d["cnt"]
    return {"total": total, "by_match": by_match}


def wc_set_typing(match_id: int, requester_telegram_id: int, is_playoff: int = 0) -> bool:
    """WC "yozmoqda" signali (upsert)."""
    access = _wc_chat_access(match_id, requester_telegram_id, is_playoff)
    if access is None:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO wc_chat_typing (match_id, user_id, is_playoff, typing_at) VALUES (?, ?, ?, datetime('now')) "
        "ON CONFLICT(match_id, user_id, is_playoff) DO UPDATE SET typing_at = datetime('now')",
        (match_id, access["my_user_id"], is_playoff),
    )
    conn.commit()
    conn.close()
    return True


def wc_get_chat_state(match_id: int, requester_telegram_id: int, is_playoff: int = 0) -> dict | None:
    """WC raqib holati (online/typing/last_seen). Liga get_chat_state naqshi."""
    access = _wc_chat_access(match_id, requester_telegram_id, is_playoff)
    if access is None:
        return None
    opp_id = access["opponent_user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT last_seen, username FROM users WHERE id = ?", (opp_id,))
    row = cursor.fetchone()
    last_seen_seconds = None
    online = False
    opponent_username = None
    if row is not None:
        rd = dict(row)
        opponent_username = rd.get("username")
        if rd.get("last_seen"):
            cursor.execute("SELECT (julianday('now') - julianday(?)) * 86400.0", (rd["last_seen"],))
            elapsed = cursor.fetchone()[0]
            if elapsed is not None:
                last_seen_seconds = int(elapsed)
                online = elapsed < ONLINE_THRESHOLD_SECONDS

    typing = False
    cursor.execute(
        "SELECT typing_at FROM wc_chat_typing WHERE match_id = ? AND user_id = ? AND is_playoff = ?",
        (match_id, opp_id, is_playoff),
    )
    trow = cursor.fetchone()
    if trow is not None and dict(trow).get("typing_at"):
        cursor.execute("SELECT (julianday('now') - julianday(?)) * 86400.0", (dict(trow)["typing_at"],))
        t_elapsed = cursor.fetchone()[0]
        if t_elapsed is not None:
            typing = t_elapsed < TYPING_THRESHOLD_SECONDS

    conn.close()
    return {
        "online": online,
        "typing": typing,
        "last_seen_seconds": 0 if online else last_seen_seconds,
        "opponent_user_id": opp_id,
        "opponent_username": opponent_username,
    }


def wc_get_chat_messages(match_id: int, requester_telegram_id: int, is_playoff: int = 0) -> list[dict] | None:
    """WC match xabarlari (vaqt tartibida). Yon ta'sir: raqib xabarlarini o'qilgan deb belgilaydi."""
    access = _wc_chat_access(match_id, requester_telegram_id, is_playoff)
    if access is None:
        return None

    my_id = access["my_user_id"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE wc_messages SET is_read = 1 WHERE match_id = ? AND sender_id != ? AND is_read = 0 AND is_playoff = ?",
        (match_id, my_id, is_playoff),
    )
    conn.commit()

    cursor.execute(
        """
        SELECT msg.id AS id, msg.sender_id AS sender_id, msg.text AS text,
               msg.is_read AS is_read, msg.created_at AS created_at,
               reg.team_name AS club_name
        FROM wc_messages msg
        LEFT JOIN wc_registrations reg ON reg.user_id = msg.sender_id
        WHERE msg.match_id = ? AND msg.is_playoff = ?
        ORDER BY msg.id ASC
        """,
        (match_id, is_playoff),
    )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        result.append({
            "id": d["id"],
            "text": d["text"],
            "created_at": d["created_at"],
            "is_read": bool(d["is_read"]),
            "mine": d["sender_id"] == my_id,
            "club_name": d.get("club_name"),
        })
    return result
