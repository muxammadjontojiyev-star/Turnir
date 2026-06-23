"""
queries.py — User, League, Registration uchun CRUD funksiyalari.

Match generatsiyasi va jadval (schedule) bilan bog'liq funksiyalar
uchun schedule.py ga qarang.
"""

from datetime import datetime, timezone, timedelta

from models import get_connection
from config import (
    LEAGUE_STATUS_OPEN, DEFAULT_LANGUAGE,
    TOURNAMENT_TIMEZONE_OFFSET, MATCHDAY_UNLOCK_HOUR, TOTAL_MATCHDAYS,
)


# ============ USERS ============

def get_or_create_user(telegram_id: int, nickname: str, username: str | None = None) -> dict:
    """
    Foydalanuvchini topadi, topilmasa yangi yaratadi.

    username (Telegram @username) berilsa: yangi user yaratilganda yoziladi,
    mavjud user'da esa yangilanadi (foydalanuvchi keyinroq username
    qo'shishi yoki o'zgartirishi mumkin).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            "INSERT INTO users (telegram_id, nickname, username, language) VALUES (?, ?, ?, ?)",
            (telegram_id, nickname, username, DEFAULT_LANGUAGE),
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
    elif username is not None and row["username"] != username:
        # Mavjud user — username o'zgargan bo'lsa yangilaymiz
        cursor.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()

    conn.close()
    return dict(row)


def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    """Telegram ID bo'yicha foydalanuvchini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """Internal user.id bo'yicha foydalanuvchini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_language(user_id: int, language: str) -> None:
    """Foydalanuvchi tilini yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
    conn.commit()
    conn.close()


def update_user_nickname(user_id: int, nickname: str) -> None:
    """Foydalanuvchi nickname'ini yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET nickname = ? WHERE id = ?", (nickname, user_id))
    conn.commit()
    conn.close()


def get_all_users_with_registration() -> list[dict]:
    """
    Barcha foydalanuvchilarni, ro'yxatdan o'tgan ligasi va klubi bilan birga
    qaytaradi (admin panel uchun). Ro'yxatdan o'tmagan foydalanuvchilarda
    league_id va club_name = None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT users.id, users.telegram_id, users.nickname, users.username,
               registrations.league_id, registrations.club_name
        FROM users
        LEFT JOIN registrations ON registrations.user_id = users.id
        ORDER BY users.id ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def remove_user_completely(user_id: int) -> tuple[bool, str]:
    """
    Foydalanuvchini butunlay o'chiradi: uning matchlari, ro'yxatdan
    o'tgan yozuvi va user qatorining o'zi (admin uchun).

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "user_not_found"
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if cursor.fetchone() is None:
        conn.close()
        return False, "user_not_found"

    cursor.execute(
        "DELETE FROM matches WHERE player1_id = ? OR player2_id = ?",
        (user_id, user_id),
    )
    cursor.execute("DELETE FROM registrations WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

    conn.commit()
    conn.close()
    return True, "ok"


# ============ LEAGUES ============

def get_all_leagues() -> list[dict]:
    """Barcha ligalarni qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leagues")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_league_by_id(league_id: int) -> dict | None:
    """ID bo'yicha ligani qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leagues WHERE id = ?", (league_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def count_league_players(league_id: int) -> int:
    """Ligadagi ro'yxatdan o'tgan ishtirokchilar sonini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM registrations WHERE league_id = ?", (league_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"]


def get_taken_clubs(league_id: int) -> list[str]:
    """Shu ligada allaqachon band qilingan klub nomlari ro'yxatini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT club_name FROM registrations WHERE league_id = ? AND club_name IS NOT NULL",
        (league_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["club_name"] for row in rows]


def update_league_status(league_id: int, status: str) -> None:
    """Liga statusini yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leagues SET status = ? WHERE id = ?", (status, league_id))
    conn.commit()
    conn.close()


def league_has_matches(league_id: int) -> bool:
    """Liga uchun allaqachon match (jadval) yaratilganmi — qur'a takror o'tkazilishini oldini olish uchun."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM matches WHERE league_id = ? LIMIT 1", (league_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def delete_league_matches(league_id: int) -> int:
    """
    Liga uchun barcha matchlarni o'chiradi (qayta qur'a uchun).

    ⚠️ DIQQAT: bu kiritilgan natijalarni ham o'chiradi. Faqat to'liq qayta qur'a
    (redraw) uchun ishlatiladi. last_notified_matchday ham 0 ga qaytariladi,
    chunki yangi jadvalda turlar yangidan ochiladi.

    Qaytaradi: o'chirilgan matchlar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM matches WHERE league_id = ?", (league_id,))
    count = cursor.fetchone()["cnt"]
    cursor.execute("DELETE FROM matches WHERE league_id = ?", (league_id,))
    cursor.execute(
        "UPDATE leagues SET last_notified_matchday = 0 WHERE id = ?", (league_id,)
    )
    conn.commit()
    conn.close()
    return count


# ============ TURNIR VAQT JADVALI (matchday qulfi) ============

def _tournament_now() -> datetime:
    """Hozirgi vaqtni turnir mintaqasida (Toshkent UTC+5) qaytaradi."""
    tz = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
    return datetime.now(tz)


def _parse_draw_date(raw) -> datetime | None:
    """
    draw_date'ni (ISO string yoki datetime) turnir mintaqasidagi datetime'ga aylantiradi.
    None yoki noto'g'ri qiymatda None qaytaradi.
    """
    if raw is None:
        return None
    tz = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
    if isinstance(raw, datetime):
        dt = raw
    else:
        try:
            dt = datetime.fromisoformat(str(raw))
        except ValueError:
            return None
    # Naive bo'lsa — turnir mintaqasida deb hisoblaymiz (biz shunday yozamiz)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def set_league_draw_date(league_id: int, dt: datetime | None = None) -> None:
    """
    Liga qur'a sanasini yozadi (turnir mintaqasi, ISO format). dt berilmasa — hozir.
    Bu sana asosida har kuni bitta yangi tur ochiladi (get_open_matchday).
    """
    if dt is None:
        dt = _tournament_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leagues SET draw_date = ? WHERE id = ?",
        (dt.isoformat(), league_id),
    )
    conn.commit()
    conn.close()


def get_open_matchday(league_id: int) -> int:
    """
    Shu liga uchun hozir ochiq bo'lgan eng yuqori matchday raqamini qaytaradi.

    Mantiq: qur'a kuni 1-tur ochiq. Keyin har kuni MATCHDAY_UNLOCK_HOUR (01:00)
    da bitta yangi tur ochiladi. Ochiq turlar soni = 1 + (kun farqi), kun farqi
    "unlock soatiga moslangan kalendar kun" bo'yicha hisoblanadi (Toshkent vaqti).

    draw_date yo'q bo'lsa (qur'a o'tkazilmagan) — 0 (hech qaysi tur ochiq emas).
    Natija 1..TOTAL_MATCHDAYS oralig'ida cheklanadi.
    """
    league = get_league_by_id(league_id)
    if league is None:
        return 0
    draw_dt = _parse_draw_date(league["draw_date"] if "draw_date" in league.keys() else None)
    if draw_dt is None:
        return 0

    now = _tournament_now()

    # "Unlock kuni" = soatni MATCHDAY_UNLOCK_HOUR ga siljitib, faqat sanani olamiz.
    # Masalan unlock soati 01:00 bo'lsa, 00:30 hali "kechagi kun"ga tegishli.
    def unlock_day(d: datetime):
        shifted = d - timedelta(hours=MATCHDAY_UNLOCK_HOUR)
        return shifted.date()

    days_passed = (unlock_day(now) - unlock_day(draw_dt)).days
    open_count = 1 + days_passed

    if open_count < 1:
        return 0
    if open_count > TOTAL_MATCHDAYS:
        return TOTAL_MATCHDAYS
    return open_count


def set_last_notified_matchday(league_id: int, matchday: int) -> None:
    """Liga uchun oxirgi 'tur ochildi' xabari yuborilgan matchday raqamini yozadi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leagues SET last_notified_matchday = ? WHERE id = ?",
        (matchday, league_id),
    )
    conn.commit()
    conn.close()


def get_leagues_needing_matchday_notice() -> list[dict]:
    """
    Yangi tur ochilgani haqida xabar yuborilishi kerak bo'lgan ligalarni qaytaradi.

    Liga uchun hozir ochiq matchday (get_open_matchday) last_notified_matchday'dan
    katta bo'lsa — yangi tur(lar) ochilgan, xabar kerak. Faqat draw_date bor
    (qur'a o'tkazilgan) ligalar tekshiriladi.

    Qaytaradi: [{league_id, name, open_matchday}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, last_notified_matchday FROM leagues WHERE draw_date IS NOT NULL"
    )
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        open_md = get_open_matchday(row["id"])
        if open_md > row["last_notified_matchday"]:
            result.append({
                "league_id": row["id"],
                "name": row["name"],
                "open_matchday": open_md,
            })
    return result


# ============ REGISTRATIONS ============

def get_user_registration(user_id: int) -> dict | None:
    """Foydalanuvchining ro'yxatdan o'tgan ligasini qaytaradi (agar bor bo'lsa)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registrations WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_league_members_for_notify(league_id: int) -> list[dict]:
    """
    Ligadagi barcha ishtirokchilarning telegram_id va language'ini qaytaradi
    (inline bildirishnoma yuborish uchun). Format: [{telegram_id, language}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT users.telegram_id, users.language
        FROM registrations
        JOIN users ON users.id = registrations.user_id
        WHERE registrations.league_id = ?
        """,
        (league_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def register_user_to_league(user_id: int, league_id: int, club_name: str | None = None) -> tuple[bool, str]:
    """
    Foydalanuvchini ligaga ro'yxatdan o'tkazadi.

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "already_registered", "league_full", "club_taken"
    """
    existing = get_user_registration(user_id)
    if existing is not None:
        return False, "already_registered"

    league = get_league_by_id(league_id)
    if league is None:
        return False, "league_not_found"

    current_count = count_league_players(league_id)
    if current_count >= league["max_players"]:
        return False, "league_full"

    if club_name is not None:
        taken = get_taken_clubs(league_id)
        if club_name in taken:
            return False, "club_taken"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO registrations (user_id, league_id, club_name) VALUES (?, ?, ?)",
        (user_id, league_id, club_name),
    )
    conn.commit()
    conn.close()
    return True, "ok"


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

    new_status = "confirmed" if action == "confirm" else "rejected"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE matches SET status = ? WHERE id = ?",
        (new_status, match_id),
    )
    conn.commit()
    conn.close()
    return True, "ok"


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
