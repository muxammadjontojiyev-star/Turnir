"""
queries.py — User, League, Registration uchun CRUD funksiyalari.

Match generatsiyasi va jadval (schedule) bilan bog'liq funksiyalar
uchun schedule.py ga qarang.
"""

from datetime import datetime, timezone, timedelta

from models import get_connection
from config import (
    LEAGUE_STATUS_OPEN, DEFAULT_LANGUAGE,
    TOURNAMENT_TIMEZONE_OFFSET, MATCHDAY_UNLOCK_HOUR, MATCHDAY_UNLOCK_MINUTE, TOTAL_MATCHDAYS,
    MATCHDAYS_PER_UNLOCK, RESULT_ENTRY_DELAY_MINUTES,
    ENTRY_CUTOFF_BEFORE_DEADLINE_MINUTES,
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


def get_played_results(league_id: int) -> list[dict]:
    """
    Liga uchun NATIJA kiritilgan matchlarni qaytaradi (qayta qur'ada saqlash uchun).

    Faqat score'i bor (confirmed/awaiting_confirmation/rejected) matchlar.
    Qaytaradi: [{player1_id, player2_id, score1, score2, submitted_by, status}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT player1_id, player2_id, score1, score2, submitted_by, status
        FROM matches
        WHERE league_id = ? AND score1 IS NOT NULL
        """,
        (league_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def restore_results_to_schedule(league_id: int, played: list[dict]) -> int:
    """
    Saqlangan natijalarni (get_played_results) yangi jadvalga ko'chiradi.

    Har bir saqlangan natija uchun yangi jadvaldan O'SHA ikki o'yinchi o'rtasidagi
    matchni topadi (uy/mehmon tartibi muhim — player1 vs player2 aniq mos kelishi
    kerak) va score/status'ni yozadi.

    Qaytaradi: muvaffaqiyatli ko'chirilgan natijalar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    restored = 0
    for r in played:
        # Yangi jadvalda aynan shu yo'nalishdagi (p1 uy, p2 mehmon) matchni topamiz
        cursor.execute(
            """
            UPDATE matches
            SET score1 = ?, score2 = ?, submitted_by = ?, status = ?
            WHERE league_id = ? AND player1_id = ? AND player2_id = ?
              AND score1 IS NULL
            """,
            (r["score1"], r["score2"], r["submitted_by"], r["status"],
             league_id, r["player1_id"], r["player2_id"]),
        )
        if cursor.rowcount > 0:
            restored += 1
    conn.commit()
    conn.close()
    return restored

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


def reset_awaiting_in_range(league_id: int, from_md: int, to_md: int) -> int:
    """
    Berilgan ORALIQDAGI (from_md < matchday <= to_md) TASDIQLANMAGAN
    (awaiting_confirmation) natijalarni qayta 'pending' qiladi (score tozalanadi).

    Bu turlar hali o'ynalmagan bo'lsa-yu, kimdir yolg'on natija kiritib qo'ygan,
    raqib esa tasdiqlamagan ham rad qilmagan bo'lsa — ularni dastlabki (toza) holatga
    qaytaradi. CONFIRMED (tasdiqlangan) natijalarga TEGMAYDI — faqat awaiting.

    Qaytaradi: tozalangan turlar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE matches
        SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending'
        WHERE league_id = ? AND matchday > ? AND matchday <= ?
          AND status = 'awaiting_confirmation'
        """,
        (league_id, from_md, to_md),
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def reopen_matchday_range(league_id: int, from_md: int, to_md: int) -> int:
    """
    Berilgan ORALIQDAGI (from_md < matchday <= to_md) avtomatik 0:0 tasdiqlangan
    turlarni qayta 'pending' qiladi. reopen_matchdays'dan farqi — pastki chegara ham
    bor, shuning uchun deadline o'tib tasdiqlangan turlarga (1-2) TEGMAYDI.

    Masalan from_md=2, to_md=4 → faqat 3-4 turdagi 0:0'lar qaytariladi.
    Faqat score 0:0 confirmed (qo'lda natijalarga tegmaydi).

    Qaytaradi: qayta ochilgan turlar soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE matches
        SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending'
        WHERE league_id = ? AND matchday > ? AND matchday <= ?
          AND status = 'confirmed' AND score1 = 0 AND score2 = 0
        """,
        (league_id, from_md, to_md),
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def reopen_matchdays(league_id: int, up_to_matchday: int) -> int:
    """
    Berilgan turgacha (up_to_matchday) bo'lgan AVTOMATIK 0:0 tasdiqlangan turlarni
    qayta 'pending' holatiga qaytaradi (xato avtomatik tasdiqni bekor qilish uchun).

    Faqat score 0:0 va confirmed bo'lganlarni qaytaradi (qo'lda kiritilган haqiqiy
    natijalarga TEGMAYDI — ular 0:0 emas yoki boshqa status).

    Qaytaradi: qayta ochilgan turlar (match) soni.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE matches
        SET score1 = NULL, score2 = NULL, submitted_by = NULL, status = 'pending'
        WHERE league_id = ? AND matchday <= ?
          AND status = 'confirmed' AND score1 = 0 AND score2 = 0
        """,
        (league_id, up_to_matchday),
    )
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def get_deadline_passed_matchday(league_id: int) -> int:
    """
    Deadline (01:00) o'tgan eng yuqori matchday raqamini qaytaradi.

    Bu get_open_matchday'dan FARQ qiladi: ochiq turlar ichida BUGUN ochilganlarning
    deadline'i hali o'tmagan. Deadline o'tgan = qur'a kunidan keyingi kunlarda
    ochilganlar (bugun ochilgan MATCHDAYS_PER_UNLOCK ta turdan oldingilari).

    Mantiq:
    - days_passed=0 (qur'a kuni): turlar ochiq, lekin deadline o'tmagan → 0.
    - days_passed=1: birinchi kun ochilganlar (MATCHDAYS_PER_UNLOCK ta) deadline o'tdi.
    - days_passed=N: N*MATCHDAYS_PER_UNLOCK tur deadline o'tdi.

    Avtomatik tasdiqlash (scheduler) shu raqamgacha bo'lgan turlarni hal qiladi.
    draw_date yo'q bo'lsa — 0.
    """
    league = get_league_by_id(league_id)
    if league is None:
        return 0
    draw_dt = _parse_draw_date(league["draw_date"] if "draw_date" in league.keys() else None)
    if draw_dt is None:
        return 0

    now = _tournament_now()

    def unlock_day(d: datetime):
        shifted = d - timedelta(hours=MATCHDAY_UNLOCK_HOUR, minutes=MATCHDAY_UNLOCK_MINUTE)
        return shifted.date()

    days_passed = (unlock_day(now) - unlock_day(draw_dt)).days
    if days_passed < 1:
        return 0
    deadline_passed = days_passed * MATCHDAYS_PER_UNLOCK
    if deadline_passed > TOTAL_MATCHDAYS:
        return TOTAL_MATCHDAYS
    return deadline_passed


def get_matchday_entry_locked(league_id: int, matchday: int) -> bool:
    """
    Berilgan matchday uchun hisob kiritish KECHIKISH tufayli bloklanganmi.

    Tur ochilgandan (01:00) so'ng RESULT_ENTRY_DELAY_MINUTES (105 daq = 1s45daq)
    o'tmaguncha natija kiritib bo'lmaydi. Maqsad: o'yinchilar o'ynashga ulgursin,
    o'ynalmagan o'yinga darrov yolg'on natija kiritilmasin.

    True  → hali erta, hisob kiritib bo'lmaydi (kechikish tugamagan).
    False → kechikish tugagan yoki tur eski, hisob kiritsa bo'ladi.

    Eslatma: bu tur OCHIQ (get_open_matchday) ekanini tekshirmaydi — uni chaqiruvchi
    alohida tekshiradi. Bu faqat "ochilgandan keyin yetarli vaqt o'tdimi"ni qaraydi.
    """
    league = get_league_by_id(league_id)
    if league is None:
        return True
    draw_dt = _parse_draw_date(league["draw_date"] if "draw_date" in league.keys() else None)
    if draw_dt is None:
        return True

    import math
    # matchday qaysi "unlock kunida" ochiladi (0 = boshlanish/qur'a kuni):
    # 1..PER_UNLOCK -> 0-kun, PER_UNLOCK+1..2*PER_UNLOCK -> 1-kun, ...
    unlock_day_index = math.ceil(matchday / MATCHDAYS_PER_UNLOCK) - 1

    # O'sha turning ochilish payti: draw_date kuni + unlock_day_index kun, soat = UNLOCK_HOUR:UNLOCK_MINUTE.
    # draw_dt timezone-aware — open_dt'ni ham o'sha tzinfo bilan yasaymiz (taqqoslash uchun).
    draw_day = (draw_dt - timedelta(hours=MATCHDAY_UNLOCK_HOUR, minutes=MATCHDAY_UNLOCK_MINUTE)).date()
    open_day = draw_day + timedelta(days=unlock_day_index)
    open_dt = datetime(open_day.year, open_day.month, open_day.day,
                       MATCHDAY_UNLOCK_HOUR, MATCHDAY_UNLOCK_MINUTE, 0, tzinfo=draw_dt.tzinfo)

    # Boshlanish kuni (0-kun) turlar darrov ochiladi (qur'a payti), keyingilari 23:30 da.
    # Qur'a kuni ochilgan turlar uchun ochilish payti = draw_date'ning o'zi.
    if unlock_day_index == 0:
        open_dt = draw_dt

    entry_allowed_at = open_dt + timedelta(minutes=RESULT_ENTRY_DELAY_MINUTES)
    now = _tournament_now()
    return now < entry_allowed_at


def is_near_deadline() -> bool:
    """
    Hozir keyingi DEADLINE (01:00, MATCHDAY_UNLOCK_HOUR) ga
    ENTRY_CUTOFF_BEFORE_DEADLINE_MINUTES (15 daq) dan kam qoldimi.

    True  → 00:45–01:00 oralig'idamiz: hisob KIRITISH va RAD ETISH yopiq.
            (oxirgi 15 daqiqada yangi o'yin boshlab/rad etib bo'lmaydi)
    False → vaqt yetarli, normal ishlaydi.

    Vaqtga asoslangan (matchday'dan mustaqil) — har kuni 00:45 da yopiladi,
    01:00 da (yangi tur ochilgach) yana ochiladi.

    ⚠️ CHEKLOV O'CHIRILDI (foydalanuvchi so'rovi): deadline'dan oldingi 15 daqiqalik
    cheklov olib tashlandi — endi 00:45–01:00 oralig'ida ham hisob kiritish va rad
    etish ochiq. Funksiya doim False qaytaradi.
    REVERT: pastdagi `return False`ni o'chirib, izohga olingan asl blokni qaytarish kifoya.
    """
    return False
    # --- ASL CHEKLOV MANTIG'I (revert uchun saqlandi) ---
    # now = _tournament_now()
    # # Bugungi (yoki ertangi) keyingi unlock payti (01:00)
    # today_unlock = now.replace(hour=MATCHDAY_UNLOCK_HOUR, minute=0, second=0, microsecond=0)
    # if now >= today_unlock:
    #     # 01:00 dan o'tdik — keyingi deadline ertaga 01:00
    #     next_deadline = today_unlock + timedelta(days=1)
    # else:
    #     next_deadline = today_unlock
    # minutes_left = (next_deadline - now).total_seconds() / 60.0
    # return minutes_left <= ENTRY_CUTOFF_BEFORE_DEADLINE_MINUTES


def get_open_matchday(league_id: int) -> int:
    """
    Shu liga uchun hozir ochiq bo'lgan eng yuqori matchday raqamini qaytaradi.

    Mantiq: qur'a kuni MATCHDAYS_PER_UNLOCK ta tur ochiq. Keyin har kuni
    MATCHDAY_UNLOCK_HOUR (01:00) da yana MATCHDAYS_PER_UNLOCK ta tur ochiladi.
    Ochiq turlar = (1 + kun farqi) * MATCHDAYS_PER_UNLOCK, kun farqi "unlock
    soatiga moslangan kalendar kun" bo'yicha (Toshkent vaqti).

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

    # "Unlock kuni" = soat:daqiqani MATCHDAY_UNLOCK_HOUR:MATCHDAY_UNLOCK_MINUTE ga siljitib, faqat sanani olamiz.
    # Masalan unlock payti 23:30 bo'lsa, 23:00 hali "kechagi kun"ga tegishli.
    def unlock_day(d: datetime):
        shifted = d - timedelta(hours=MATCHDAY_UNLOCK_HOUR, minutes=MATCHDAY_UNLOCK_MINUTE)
        return shifted.date()

    days_passed = (unlock_day(now) - unlock_day(draw_dt)).days
    # Har "unlock kuni" MATCHDAYS_PER_UNLOCK ta tur ochiladi (boshlanish kuni ham shuncha).
    open_count = (1 + days_passed) * MATCHDAYS_PER_UNLOCK

    if open_count < 1:
        return 0
    if open_count > TOTAL_MATCHDAYS:
        return TOTAL_MATCHDAYS
    return open_count


def get_leagues_needing_deadline_notice() -> list[dict]:
    """
    Deadline (23:30) ga 1 soat qolganda (22:30-23:30 oralig'ida) hali bugun
    eslatma yuborilmagan, davom etayotgan (ochiq turi bor) ligalarni qaytaradi.

    Idempotent: last_deadline_notice_date bugungi sanaga teng bo'lsa qayta
    yuborilmaydi. Faqat 22:30-23:30 oynasida ishlaydi.

    Qaytaradi: [{league_id, name}, ...]
    """
    now = _tournament_now()
    # Faqat deadline'dan 1 soat oldingi oynada (deadline 23:30 → 22:30-23:30).
    # Daqiqa aniqligida: now ning kun ichidagi daqiqasi [deadline-60, deadline) oralig'ida.
    deadline_minutes = MATCHDAY_UNLOCK_HOUR * 60 + MATCHDAY_UNLOCK_MINUTE
    now_minutes = now.hour * 60 + now.minute
    if not (deadline_minutes - 60 <= now_minutes < deadline_minutes):
        return []
    today_str = now.date().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name FROM leagues
        WHERE draw_date IS NOT NULL
          AND (last_deadline_notice_date IS NULL OR last_deadline_notice_date != ?)
        """,
        (today_str,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Faqat hali tugamagan (ochiq turi bor) ligalar
    result = []
    for r in rows:
        open_md = get_open_matchday(r["id"])
        if 1 <= open_md <= TOTAL_MATCHDAYS:
            result.append({"league_id": r["id"], "name": r["name"]})
    return result


def set_deadline_notice_sent(league_id: int) -> None:
    """Ligaga bugun deadline eslatmasi yuborilganini belgilaydi (idempotentlik)."""
    today_str = _tournament_now().date().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE leagues SET last_deadline_notice_date = ? WHERE id = ?",
        (today_str, league_id),
    )
    conn.commit()
    conn.close()


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


# ============================================================
#  WORLD CUP (Jahon Chempionati) — liga tizimidan ALOHIDA
#  wc_registrations jadvali. Foydalanuvchi WC'da 1 marta ro'yxatdan o'tadi.
# ============================================================

def wc_get_user_registration(user_id: int) -> dict | None:
    """Foydalanuvchining World Cup ro'yxatini qaytaradi (bor bo'lsa)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wc_registrations WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def wc_get_taken_teams(group_letter: str) -> list[str]:
    """Shu guruhda allaqachon band qilingan jamoa nomlari ro'yxati."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT team_name FROM wc_registrations WHERE group_letter = ?",
        (group_letter,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["team_name"] for row in rows]


def wc_count_group_players(group_letter: str) -> int:
    """Shu guruhda ro'yxatdan o'tgan ishtirokchilar soni."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM wc_registrations WHERE group_letter = ?",
        (group_letter,),
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"]


def wc_register_user(user_id: int, group_letter: str, team_name: str) -> tuple[bool, str]:
    """
    Foydalanuvchini World Cup'ga ro'yxatdan o'tkazadi.

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "wc_already_registered", "wc_group_full",
              "wc_invalid_group", "wc_invalid_team", "wc_team_taken"
    """
    # WC_TEAMS_PER_GROUP markazlashtirilgan (wc_data) — guruh to'lganini tekshirish uchun
    from wc_data import wc_is_valid_group, wc_team_in_group, WC_TEAMS_PER_GROUP

    # Foydalanuvchi WC'da allaqachon ro'yxatdan o'tganmi (1 marta qoidasi)
    existing = wc_get_user_registration(user_id)
    if existing is not None:
        return False, "wc_already_registered"

    if not wc_is_valid_group(group_letter):
        return False, "wc_invalid_group"

    if not wc_team_in_group(group_letter, team_name):
        return False, "wc_invalid_team"

    # Guruh to'lgan bo'lsa (4 jamoa band)
    if wc_count_group_players(group_letter) >= WC_TEAMS_PER_GROUP:
        return False, "wc_group_full"

    # Jamoa allaqachon band qilinganmi (race condition uchun ham backend himoyasi)
    if team_name in wc_get_taken_teams(group_letter):
        return False, "wc_team_taken"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO wc_registrations (user_id, group_letter, team_name) VALUES (?, ?, ?)",
        (user_id, group_letter, team_name),
    )
    conn.commit()
    conn.close()
    return True, "ok"
