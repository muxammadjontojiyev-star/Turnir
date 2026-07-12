"""
queries_matchdays.py — Matchday deadline/lock mantiqi, ochiq tur, bildirishnoma navbatlari.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from datetime import datetime, timedelta
from models import get_connection
from config import (
    MATCHDAY_UNLOCK_HOUR,
    MATCHDAY_UNLOCK_MINUTE,
    TOTAL_MATCHDAYS,
    MATCHDAYS_PER_UNLOCK,
    RESULT_ENTRY_DELAY_MINUTES,
)
from queries_leagues import _parse_draw_date, _tournament_now, get_league_by_id


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


def get_all_drawn_leagues() -> list[dict]:
    """
    Qur'a o'tkazilgan (draw_date bor) BARCHA ligalar.

    get_leagues_needing_matchday_notice()'dan farqi: u faqat YANGI TUR OCHILGAN
    ligalarni qaytaradi. Oxirgi tur (38) ochilib bo'lgach yangi tur ochilmaydi,
    shuning uchun u liga ro'yxatdan chiqib ketadi va deadline o'tgan o'yinlar
    hech qachon avtomatik tasdiqlanmay qoladi (aynan shu xato bo'lgan edi).

    Avtomatik tasdiqlash (auto_resolve_matches) shu ro'yxat bo'yicha, xabar
    yuborishdan MUSTAQIL ravishda bajariladi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id AS league_id, name FROM leagues "
        "WHERE draw_date IS NOT NULL ORDER BY id"
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
