"""
queries_matches.py — Liga o'yinlari: ro'yxat, natija kiritish/tasdiqlash, auto-resolve, admin resolve/fix.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from models import get_connection


# ============ MATCHES ============

def get_user_matches(user_id: int) -> list[dict]:
    """Foydalanuvchi ishtirok etgan barcha matchlarni qaytaradi (player1 yoki player2)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.*,
               r1.club_name AS player1_club,
               r2.club_name AS player2_club,
               u1.telegram_id AS player1_telegram_id,
               u1.username    AS player1_username,
               u1.nickname    AS player1_nickname,
               u2.telegram_id AS player2_telegram_id,
               u2.username    AS player2_username,
               u2.nickname    AS player2_nickname
        FROM matches m
        LEFT JOIN registrations r1 ON r1.user_id = m.player1_id
        LEFT JOIN registrations r2 ON r2.user_id = m.player2_id
        LEFT JOIN users u1 ON u1.id = m.player1_id
        LEFT JOIN users u2 ON u2.id = m.player2_id
        WHERE m.player1_id = ? OR m.player2_id = ?
        ORDER BY m.matchday ASC
        """,
        (user_id, user_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_match_by_id(match_id: int) -> dict | None:
    """ID bo'yicha matchni qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# WebApp chat faqat AKTIV (o'ynalmagan / tasdiq kutilayotgan) o'yinlarda ishlaydi.
CHAT_ACTIVE_MATCH_STATUSES = ("pending", "awaiting_confirmation")

# Bot bildirishnomasi anti-spam: shu (match, raqib) uchun ketma-ket bot xabarlari
# orasidagi minimal vaqt (soniya). 60s = 1 daqiqada bir martadan ko'p emas.
CHAT_NOTIFY_THROTTLE_SECONDS = 60

# Online deb hisoblash chegarasi: oxirgi faollikdan shuncha soniyada online.
ONLINE_THRESHOLD_SECONDS = 35
# "Yozmoqda" signali shuncha soniyagacha amal qiladi (yangilanmasa o'chadi).
TYPING_THRESHOLD_SECONDS = 6


def submit_match_result(match_id: int, score1: int, score2: int, submitted_by: int) -> tuple[bool, str]:
    """
    Match natijasini kiritadi (faqat o'sha matchning player1 yoki player2 kira oladi).

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "match_not_found", "not_participant", "already_submitted"
    """
    match = get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"

    if submitted_by not in (match["player1_id"], match["player2_id"]):
        return False, "not_participant"

    if match["status"] != "pending":
        return False, "already_submitted"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE matches
        SET score1 = ?, score2 = ?, submitted_by = ?, status = 'awaiting_confirmation'
        WHERE id = ?
        """,
        (score1, score2, submitted_by, match_id),
    )
    conn.commit()
    conn.close()
    return True, "ok"


def confirm_or_reject_match(match_id: int, action: str, confirmed_by: int) -> tuple[bool, str]:
    """
    Raqib tomonidan natijani tasdiqlaydi yoki rad etadi.

    action: "confirm" yoki "reject"
    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "match_not_found", "not_opponent", "wrong_status", "invalid_action"
    """
    match = get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"

    if match["status"] != "awaiting_confirmation":
        return False, "wrong_status"

    # Faqat natija kiritmagan tomon tasdiqlashi mumkin
    if confirmed_by == match["submitted_by"]:
        return False, "not_opponent"

    if confirmed_by not in (match["player1_id"], match["player2_id"]):
        return False, "not_opponent"

    if action not in ("confirm", "reject"):
        return False, "invalid_action"

    conn = get_connection()
    cursor = conn.cursor()
    if action == "confirm":
        # Tasdiqlandi — natija o'zgarmaydi, status 'confirmed'
        cursor.execute(
            "UPDATE matches SET status = 'confirmed' WHERE id = ?",
            (match_id,),
        )
    else:
        # Rad etildi — natija TOZALANADI va 'pending'ga qaytadi, shunda ikkala tomon
        # (ayniqsa rad etgan tomon) TO'G'RI natijani qaytadan kirita oladi.
        # Eski (rad etilgan) natija admin ko'rishi uchun kerak bo'lsa — log/notify orqali.
        cursor.execute(
            """
            UPDATE matches
            SET status = 'pending', score1 = NULL, score2 = NULL, submitted_by = NULL
            WHERE id = ?
            """,
            (match_id,),
        )
    conn.commit()
    conn.close()
    return True, "ok"


def auto_resolve_matches(league_id: int, up_to_matchday: int) -> dict:
    """
    Deadline o'tgan (up_to_matchday va undan oldingi turlar) hal qilinmagan
    o'yinlarni avtomatik tasdiqlaydi. Har kuni 01:00 da scheduler chaqiradi.

    Qoidalar:
    - status 'pending' (hech kim kiritmagan) → 0:0 durang, 'confirmed'.
    - status 'awaiting_confirmation' (bir tomon kiritgan, raqib javob bermagan)
      → kiritilgan natija saqlanadi, 'confirmed' (avtomatik tasdiq).
    - 'confirmed' va 'rejected' o'yinlarga TEGILMAYDI (allaqachon hal qilingan).

    up_to_matchday: shu raqamgacha (shu raqam ham kiradi) bo'lgan turlar deadline'i o'tgan.

    Qaytaradi: {pending_resolved, awaiting_resolved}.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1) Hech kim kiritmagan (pending) → 0:0 durang, tasdiqlangan
    cursor.execute(
        """
        UPDATE matches
        SET score1 = 0, score2 = 0, status = 'confirmed'
        WHERE league_id = ? AND matchday <= ? AND status = 'pending'
        """,
        (league_id, up_to_matchday),
    )
    pending_resolved = cursor.rowcount

    # 2) Bir tomon kiritgan, tasdiqlanmagan → kiritilgan natija tasdiqlanadi
    cursor.execute(
        """
        UPDATE matches
        SET status = 'confirmed'
        WHERE league_id = ? AND matchday <= ? AND status = 'awaiting_confirmation'
        """,
        (league_id, up_to_matchday),
    )
    awaiting_resolved = cursor.rowcount

    conn.commit()
    conn.close()
    return {
        "pending_resolved": pending_resolved,
        "awaiting_resolved": awaiting_resolved,
    }


def get_rejected_matches() -> list[dict]:
    """
    Statusi 'rejected' bo'lgan barcha matchlarni, ikkala o'yinchining
    nickname'i bilan birga qaytaradi (admin panel uchun).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT matches.*,
               p1.nickname AS player1_nickname,
               p2.nickname AS player2_nickname
        FROM matches
        JOIN users AS p1 ON p1.id = matches.player1_id
        JOIN users AS p2 ON p2.id = matches.player2_id
        WHERE matches.status = 'rejected'
        ORDER BY matches.matchday ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def admin_resolve_match(match_id: int, action: str, score1: int | None, score2: int | None) -> tuple[bool, str]:
    """
    Admin 'rejected' holatdagi matchni hal qiladi.

    action: "set_result" (score1/score2 kiritib 'confirmed' qiladi)
            yoki "reset" (natijani tozalab 'pending'ga qaytaradi)
    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "match_not_found", "wrong_status", "invalid_action", "score_missing"
    """
    match = get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"

    if match["status"] != "rejected":
        return False, "wrong_status"

    if action not in ("set_result", "reset"):
        return False, "invalid_action"

    conn = get_connection()
    cursor = conn.cursor()

    if action == "set_result":
        if score1 is None or score2 is None:
            conn.close()
            return False, "score_missing"
        cursor.execute(
            """
            UPDATE matches
            SET score1 = ?, score2 = ?, status = 'confirmed'
            WHERE id = ?
            """,
            (score1, score2, match_id),
        )
    else:  # reset
        cursor.execute(
            """
            UPDATE matches
            SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending'
            WHERE id = ?
            """,
            (match_id,),
        )

    conn.commit()
    conn.close()
    return True, "ok"


def admin_fix_confirmed_match(match_id: int, score1: int, score2: int) -> tuple[bool, str]:
    """
    Admin allaqachon 'confirmed' (ikki tomon tasdiqlagan) matchning
    noto'g'ri kiritilgan natijasini qo'lda tuzatadi. Status o'zgarmaydi,
    faqat score1/score2 yangilanadi.

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "match_not_found", "wrong_status"
    """
    match = get_match_by_id(match_id)
    if match is None:
        return False, "match_not_found"

    if match["status"] != "confirmed":
        return False, "wrong_status"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE matches SET score1 = ?, score2 = ? WHERE id = ?",
        (score1, score2, match_id),
    )
    conn.commit()
    conn.close()
    return True, "ok"
