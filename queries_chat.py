"""
queries_chat.py — Liga o'yin ichidagi chat: access, xabarlar, unread, typing, last_seen.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from models import get_connection
from queries_users import get_user_by_telegram_id

# (2026-07-03 hotfix: bo'lishda queries_matches.py'ga tushib qolgan edi — o'z joyiga qaytarildi.
#  wc_chat.py bularni `from queries import ...` orqali oladi — facade eksporti saqlanadi.)
# WebApp chat faqat AKTIV (o'ynalmagan / tasdiq kutilayotgan) o'yinlarda ishlaydi.
CHAT_ACTIVE_MATCH_STATUSES = ("pending", "awaiting_confirmation")

# Bot bildirishnomasi anti-spam: shu (match, raqib) uchun ketma-ket bot xabarlari
# orasidagi minimal vaqt (soniya). 60s = 1 daqiqada bir martadan ko'p emas.
CHAT_NOTIFY_THROTTLE_SECONDS = 60

# Online deb hisoblash chegarasi: oxirgi faollikdan shuncha soniyada online.
ONLINE_THRESHOLD_SECONDS = 35
# "Yozmoqda" signali shuncha soniyagacha amal qiladi (yangilanmasa o'chadi).
TYPING_THRESHOLD_SECONDS = 6


def _chat_match_access(match_id: int, requester_telegram_id: int) -> dict | None:
    """
    Chat xavfsizlik tekshiruvi. Requester shu matchning ishtirokchimi va match
    aktivmi tekshiradi. Shart bajarilsa raqib/o'zi ma'lumotini qaytaradi, aks holda None.

    Qaytaradi:
      {"match_id", "my_user_id", "opponent_user_id", "status"}
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.id AS match_id, m.status AS status,
               m.player1_id AS p1, m.player2_id AS p2,
               u1.telegram_id AS p1_tg, u2.telegram_id AS p2_tg
        FROM matches m
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
    }


def send_chat_message(match_id: int, sender_telegram_id: int, text: str):
    """
    Chat xabarini yozadi. Faqat aktiv match ishtirokchisi yuborar oladi.

    Qaytaradi: (muvaffaqiyat: bool, sabab: str, notify: dict | None)
      - notify None bo'lmasa, chaqiruvchi raqibga bot xabari yuborishi kerak:
        {"recipient_telegram_id": int, "sender_label": None, "text_preview": str}
        (sender_label api tomonda to'ldiriladi). Anti-spam: oxirgi bot xabaridan
        CHAT_NOTIFY_THROTTLE_SECONDS o'tgan bo'lsagina notify qaytadi.
    """
    text = (text or "").strip()
    if not text:
        return False, "empty", None
    if len(text) > 2000:
        text = text[:2000]

    access = _chat_match_access(match_id, sender_telegram_id)
    if access is None:
        return False, "no_access", None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (match_id, sender_id, text) VALUES (?, ?, ?)",
        (match_id, access["my_user_id"], text),
    )
    conn.commit()

    # Raqibning telegram_id'sini olamiz (bot xabari uchun)
    cursor.execute("SELECT telegram_id FROM users WHERE id = ?", (access["opponent_user_id"],))
    opp_row = cursor.fetchone()
    recipient_tg = dict(opp_row)["telegram_id"] if opp_row else None

    notify = None
    if recipient_tg is not None:
        # Anti-spam: shu (match, raqib) uchun oxirgi bot xabaridan beri qancha o'tgan?
        cursor.execute(
            "SELECT last_notified_at FROM chat_notify WHERE match_id = ? AND recipient_id = ?",
            (match_id, access["opponent_user_id"]),
        )
        nrow = cursor.fetchone()
        send_it = True
        if nrow is not None:
            last = dict(nrow).get("last_notified_at")
            if last:
                cursor.execute(
                    "SELECT (julianday('now') - julianday(?)) * 86400.0",
                    (last,),
                )
                elapsed = cursor.fetchone()[0]
                if elapsed is not None and elapsed < CHAT_NOTIFY_THROTTLE_SECONDS:
                    send_it = False

        if send_it:
            # last_notified_at ni hozirgi vaqtga yangilaymiz (upsert)
            cursor.execute(
                "INSERT INTO chat_notify (match_id, recipient_id, last_notified_at) "
                "VALUES (?, ?, datetime('now')) "
                "ON CONFLICT(match_id, recipient_id) DO UPDATE SET last_notified_at = datetime('now')",
                (match_id, access["opponent_user_id"]),
            )
            conn.commit()
            preview = text if len(text) <= 50 else text[:50] + "..."
            notify = {
                "recipient_telegram_id": recipient_tg,
                "text_preview": preview,
            }

    conn.close()
    return True, "ok", notify


def count_unread_messages(requester_telegram_id: int) -> dict:
    """
    Foydalanuvchi uchun o'qilmagan xabarlar sonini qaytaradi.

    Qaytaradi:
      {"total": int, "by_match": {match_id: count, ...}}
    Faqat AKTIV matchlardagi, raqib yuborgan, o'qilmagan xabarlar sanaladi.
    """
    user = get_user_by_telegram_id(requester_telegram_id)
    if user is None:
        return {"total": 0, "by_match": {}}
    my_id = user["id"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT msg.match_id AS match_id, COUNT(*) AS cnt
        FROM messages msg
        JOIN matches m ON m.id = msg.match_id
        WHERE msg.is_read = 0
          AND msg.sender_id != ?
          AND (m.player1_id = ? OR m.player2_id = ?)
          AND m.status IN ('pending', 'awaiting_confirmation')
        GROUP BY msg.match_id
        """,
        (my_id, my_id, my_id),
    )
    rows = cursor.fetchall()
    conn.close()

    by_match = {}
    total = 0
    for r in rows:
        d = dict(r)
        by_match[d["match_id"]] = d["cnt"]
        total += d["cnt"]
    return {"total": total, "by_match": by_match}


def touch_last_seen(telegram_id: int) -> None:
    """Foydalanuvchining oxirgi faollik vaqtini (online uchun) hozirgiga yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET last_seen = datetime('now') WHERE telegram_id = ?",
        (telegram_id,),
    )
    conn.commit()
    conn.close()


def set_typing(match_id: int, requester_telegram_id: int) -> bool:
    """
    "Yozmoqda" signalini yozadi (upsert). Faqat aktiv match ishtirokchisi.
    Qaytaradi: True (muvaffaqiyat) yoki False (access yo'q).
    """
    access = _chat_match_access(match_id, requester_telegram_id)
    if access is None:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_typing (match_id, user_id, typing_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(match_id, user_id) DO UPDATE SET typing_at = datetime('now')",
        (match_id, access["my_user_id"]),
    )
    conn.commit()
    conn.close()
    return True


def get_chat_state(match_id: int, requester_telegram_id: int) -> dict | None:
    """
    Raqibning holatini qaytaradi (chat header uchun):
      {"online": bool, "typing": bool, "last_seen_seconds": int | None}
        - online: raqib oxirgi ONLINE_THRESHOLD_SECONDS ichida faol bo'lganmi
        - typing: raqib oxirgi TYPING_THRESHOLD_SECONDS ichida "yozmoqda" signal berdimi
        - last_seen_seconds: raqib oxirgi marta necha soniya oldin ko'ringan (online bo'lsa 0)
    Access yo'q bo'lsa None.
    """
    access = _chat_match_access(match_id, requester_telegram_id)
    if access is None:
        return None
    opp_id = access["opponent_user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    # Raqib oxirgi faolligi (online) + username
    cursor.execute("SELECT last_seen, username FROM users WHERE id = ?", (opp_id,))
    row = cursor.fetchone()
    last_seen_seconds = None
    online = False
    opponent_username = None
    if row is not None:
        rd = dict(row)
        opponent_username = rd.get("username")
        if rd.get("last_seen"):
            cursor.execute(
                "SELECT (julianday('now') - julianday(?)) * 86400.0",
                (rd["last_seen"],),
            )
            elapsed = cursor.fetchone()[0]
            if elapsed is not None:
                last_seen_seconds = int(elapsed)
                online = elapsed < ONLINE_THRESHOLD_SECONDS

    # Raqib "yozmoqda"mi
    typing = False
    cursor.execute(
        "SELECT typing_at FROM chat_typing WHERE match_id = ? AND user_id = ?",
        (match_id, opp_id),
    )
    trow = cursor.fetchone()
    if trow is not None and dict(trow).get("typing_at"):
        cursor.execute(
            "SELECT (julianday('now') - julianday(?)) * 86400.0",
            (dict(trow)["typing_at"],),
        )
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


def get_chat_messages(match_id: int, requester_telegram_id: int) -> list[dict] | None:
    """
    Match xabarlarini (vaqt tartibida) qaytaradi. Yon ta'sir: raqib yuborgan
    o'qilmagan xabarlarni "o'qilgan" deb belgilaydi (ikkita ✓ uchun).

    Har bir xabar: {"id", "text", "created_at", "is_read", "mine"}
      - mine: True = men yuborganman, False = raqib yuborgan.
    Access yo'q bo'lsa None.
    """
    access = _chat_match_access(match_id, requester_telegram_id)
    if access is None:
        return None

    my_id = access["my_user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    # Raqib yuborgan o'qilmaganlarni o'qilgan deb belgilaymiz
    cursor.execute(
        "UPDATE messages SET is_read = 1 WHERE match_id = ? AND sender_id != ? AND is_read = 0",
        (match_id, my_id),
    )
    conn.commit()

    cursor.execute(
        """
        SELECT msg.id AS id, msg.sender_id AS sender_id, msg.text AS text,
               msg.is_read AS is_read, msg.created_at AS created_at,
               reg.club_name AS club_name
        FROM messages msg
        LEFT JOIN registrations reg ON reg.user_id = msg.sender_id
        WHERE msg.match_id = ?
        ORDER BY msg.id ASC
        """,
        (match_id,),
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
