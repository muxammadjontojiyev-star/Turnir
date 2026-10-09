"""
cl_rounds.py — ChL turlarini (matchday) boshqarish.

Qoida (loyiha egasi):
  • Kuniga BITTA tur o'ynaladi. Deadline — 23:30 (Toshkent).
  • Boshida hamma turlar YOPIQ (started=0).
  • Admin "O'yinlarni boshlash" bosadi -> 1-tur ochiladi.
  • Har kuni 23:30 da joriy tur YOPILADI (variant A):
        - awaiting_confirmation  -> avtomatik CONFIRMED (kiritilgan hisob bilan)
        - pending (hech kim kiritmagan) -> 0:0 durang, CONFIRMED
    va keyingi tur ochiladi. Oxirgi tur yopilgach current_matchday > umumiy tur
    soni bo'ladi (guruh bosqichi tugadi).

Vaqt: config.TOURNAMENT_TIMEZONE_OFFSET (UTC+5) va MATCHDAY_UNLOCK_HOUR (23) +
DEADLINE_MINUTE (30) — hardcode qilinmadi (qoida #17/#46).
Idempotent (qoida #38): kuniga faqat bir marta oldinga siljiydi (last_advance_date).
"""

import logging
from datetime import datetime, timedelta, timezone

from models import get_connection
from config import (
    MATCH_STATUS_PENDING,
    MATCH_STATUS_AWAITING_CONFIRMATION,
    MATCH_STATUS_CONFIRMED,
    TOURNAMENT_TIMEZONE_OFFSET,
    MATCHDAY_UNLOCK_HOUR,
)

logger = logging.getLogger(__name__)

CL_DEADLINE_MINUTE = 30      # 23:30 (Toshkent)


def _now_local() -> datetime:
    tz = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
    return datetime.now(tz)


def _current_season(cursor) -> int:
    # 2026-10-09: ChL faol mavsumi — liga mavsumidan mustaqil (cl_season_state)
    from cl_season_state import cl_data_season
    return cl_data_season(cursor)


def _total_matchdays(cursor, season: int) -> int:
    cursor.execute(
        "SELECT COALESCE(MAX(matchday), 0) AS m FROM cl_matches WHERE season = ?",
        (season,),
    )
    return cursor.fetchone()["m"]


def _is_stale_state(cursor, season: int, current: int) -> bool:
    """
    2026-09-22: cl_state ESKIRGANmi? (o'tgan ChL mavsumidan qolib ketgan holat)

    Belgisi: current_matchday > 1, lekin shu mavsumda BIRORTA ham o'yin
    'pending' dan boshqa holatga o'tmagan.

    Nega bu ishonchli: haqiqiy mavsumda har deadline (cl_tick) oldingi turni
    confirmed qiladi. Ya'ni current >= 2 bo'lsa, kamida 1-tur o'yinlari allaqachon
    confirmed bo'ladi. "current > 1 va hammasi pending" — faqat YANGI qur'a
    ESKI holat ustiga tushganda yuz beradi (cl_draw cl_state'ni tozalamasdi).

    XAVF: eskirgan holatda cl_tick yangi mavsumning barcha turlarini 0:0 bilan
    yopib yuborardi (_resolve_matchdays_upto). Shuning uchun tick buni tekshiradi.
    """
    if not current or current <= 1:
        return False
    cursor.execute(
        "SELECT 1 FROM cl_matches WHERE season = ? AND status != 'pending' LIMIT 1",
        (season,),
    )
    return cursor.fetchone() is None


def cl_get_state(season: int | None = None) -> dict:
    """{season, started, current_matchday, total_matchdays, finished}"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_season(cursor)
        cursor.execute(
            "SELECT started, current_matchday FROM cl_state WHERE season = ?",
            (season,),
        )
        row = cursor.fetchone()
        started = bool(row["started"]) if row else False
        current = row["current_matchday"] if row else 0
        total = _total_matchdays(cursor, season)
        stale = bool(started and _is_stale_state(cursor, season, current))
        return {"season": season, "started": started, "current_matchday": current,
                "total_matchdays": total,
                # Eskirgan holatda "tugagan" deb ko'rsatilmaydi
                "finished": bool(started and total and current > total and not stale),
                # 2026-09-22: admin "O'yinlarni boshlash" ni qayta bosa olishi uchun
                "stale": stale}
    finally:
        conn.close()


def cl_start_rounds(season: int | None = None) -> tuple[bool, str | dict]:
    """
    Admin turlarni boshlaydi: 1-tur ochiladi. Sabablar: not_drawn, already_started.
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_season(cursor)
        if _total_matchdays(cursor, season) == 0:
            cursor.execute("ROLLBACK")
            return False, "not_drawn"

        cursor.execute(
            "SELECT started, current_matchday FROM cl_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        if row and row["started"]:
            # 2026-09-22: eskirgan holat bo'lsa (o'tgan mavsumdan qolgan) —
            # to'xtatmaymiz, 1-turdan qaytadan boshlaymiz. Hech qanday natija
            # yo'qolmaydi: eskirgan holatda barcha o'yinlar 'pending'.
            if _is_stale_state(cursor, season, row["current_matchday"]):
                logger.warning(
                    "ChL: eskirgan cl_state tuzatildi (mavsum %s, %s-tur -> 1-tur)",
                    season, row["current_matchday"])
            else:
                cursor.execute("ROLLBACK")
                return False, "already_started"

        cursor.execute(
            "INSERT INTO cl_state (season, started, current_matchday, last_advance_date) "
            "VALUES (?, 1, 1, NULL) "
            "ON CONFLICT(season) DO UPDATE SET started = 1, current_matchday = 1, "
            "last_advance_date = NULL, updated_at = CURRENT_TIMESTAMP",
            (season,),
        )
        cursor.execute("COMMIT")
        logger.info("ChL: turlar boshlandi (mavsum %s), 1-tur ochildi", season)
        return True, {"season": season, "current_matchday": 1}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _resolve_matchdays_upto(cursor, season: int, up_to_matchday: int) -> dict:
    """
    Deadline yopilishi (variant A): awaiting -> confirmed; pending -> 0:0 confirmed.

    2026-08-28: ilgari FAQAT joriy tur (matchday = ?) yopilardi. Endi
    "matchday <= ?" — Liga (auto_resolve_matches) va WC (wc_auto_resolve_group)
    bilan bir xil naqsh (qoida #26).

    NIMA UCHUN (qoida #19): faqat joriy tur yopilganda, biror sabab bilan
    chetda qolgan o'yin (masalan scheduler 23:30-23:59 oynasini o'tkazib
    yuborsa yoki tur diapazondan tashqarida bo'lsa) ABADIY 'pending' qolardi.
    Bitta shunday o'yin cl_po_qualified() ni bloklab, "Guruh o'yinlari hali
    tugamagan" xatosini keltirib chiqarardi. "<=" bilan har deadline o'zini
    o'zi tuzatadi (self-healing).

    Idempotent (qoida #38): 'confirmed' va 'rejected' o'yinlarga TEGILMAYDI —
    qayta chaqirilsa 0 qator o'zgaradi.
    """
    cursor.execute(
        "UPDATE cl_matches SET status = ? "
        "WHERE season = ? AND matchday <= ? AND status = ?",
        (MATCH_STATUS_CONFIRMED, season, up_to_matchday,
         MATCH_STATUS_AWAITING_CONFIRMATION),
    )
    awaiting = cursor.rowcount or 0
    cursor.execute(
        "UPDATE cl_matches SET score1 = 0, score2 = 0, status = ? "
        "WHERE season = ? AND matchday <= ? AND status = ?",
        (MATCH_STATUS_CONFIRMED, season, up_to_matchday, MATCH_STATUS_PENDING),
    )
    pending = cursor.rowcount or 0
    return {"awaiting_resolved": awaiting, "pending_resolved": pending}


def cl_tick(season: int | None = None) -> dict | None:
    """
    Scheduler chaqiradi (daqiqada bir marta). 23:30 (Toshkent) o'tgan va bugun
    hali siljitilmagan bo'lsa: joriy turni yopadi va keyingisini ochadi.
    Qaytaradi: siljish bo'lsa natija dict, aks holda None.
    """
    now = _now_local()
    deadline = now.replace(hour=MATCHDAY_UNLOCK_HOUR, minute=CL_DEADLINE_MINUTE,
                           second=0, microsecond=0)
    if now < deadline:
        return None
    today = now.date().isoformat()

    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_season(cursor)
        cursor.execute(
            "SELECT started, current_matchday, last_advance_date "
            "FROM cl_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        if not row or not row["started"]:
            cursor.execute("ROLLBACK")
            return None
        if row["last_advance_date"] == today:          # bugun allaqachon siljidi
            cursor.execute("ROLLBACK")
            return None

        total = _total_matchdays(cursor, season)
        current = row["current_matchday"]

        # 2026-09-22: ESKIRGAN holat — yangi qur'a eski holat ustiga tushgan.
        # Bu yerda davom etsak, _resolve_matchdays_upto yangi mavsumning
        # BARCHA turlarini 0:0 bilan yopib yuborardi. Admin "O'yinlarni
        # boshlash" ni bosguncha hech narsa qilmaymiz.
        if _is_stale_state(cursor, season, current):
            cursor.execute("ROLLBACK")
            logger.warning(
                "ChL tick O'TKAZIB YUBORILDI: cl_state eskirgan (mavsum %s, %s-tur, "
                "barcha o'yinlar pending). Admin 'O'yinlarni boshlash'ni bosishi kerak.",
                season, current)
            return None

        if current > total:                            # guruh bosqichi tugagan
            # 2026-08-28: tugagan bo'lsa ham qolib ketgan o'yinlarni yopamiz.
            # Ilgari bu yerda shunchaki ROLLBACK/None bo'lardi — natijada
            # chetda qolgan bitta 'pending' o'yin play-off'ni ABADIY bloklardi
            # ("Guruh o'yinlari hali tugamagan"). current_matchday oshirilmaydi,
            # last_advance_date ham o'zgarmaydi — faqat tozalash.
            healed = _resolve_matchdays_upto(cursor, season, total)
            if healed["awaiting_resolved"] or healed["pending_resolved"]:
                cursor.execute("COMMIT")
                logger.warning(
                    "ChL: guruh bosqichi tugagan, chetda qolgan o'yinlar yopildi "
                    "(awaiting: %s, 0:0: %s)",
                    healed["awaiting_resolved"], healed["pending_resolved"],
                )
                return {"season": season, "closed_matchday": total,
                        "opened_matchday": current, **healed}
            cursor.execute("ROLLBACK")
            return None

        resolved = _resolve_matchdays_upto(cursor, season, current)
        cursor.execute(
            "UPDATE cl_state SET current_matchday = ?, last_advance_date = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE season = ?",
            (current + 1, today, season),
        )
        cursor.execute("COMMIT")
        logger.info("ChL: %s-tur yopildi (awaiting: %s, 0:0: %s) → %s-tur ochildi",
                    current, resolved["awaiting_resolved"],
                    resolved["pending_resolved"], current + 1)
        return {"season": season, "closed_matchday": current,
                "opened_matchday": current + 1, **resolved}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def cl_matchday_open(matchday: int, season: int | None = None) -> bool:
    """Shu tur natija kiritish uchun ochiqmi? (server tomonida tekshiruv — qoida #41)"""
    st = cl_get_state(season)
    return bool(st["started"]) and matchday == st["current_matchday"]


def cl_force_close_group(season: int | None = None) -> tuple[bool, str, dict]:
    """
    ADMIN: guruh bosqichidagi hal qilinmagan o'yinlarni DARHOL yopadi —
    23:30 deadline'ni kutmasdan (2026-08-28).

    Kerak bo'lgan sabab (qoida #52): chetda qolgan bitta o'yin play-off'ni
    bloklab qo'yadi, admin esa qayta tasnifni HOZIR boshlashi kerak.

    Xuddi deadline kabi: awaiting -> confirmed (kiritilgan hisob SAQLANADI),
    pending -> 0:0 confirmed. cl_state (current_matchday, last_advance_date)
    TEGILMAYDI — turlar tartibi buzilmaydi.

    XAVFSIZLIK GUARD (qoida #07): faqat guruh bosqichi TUGAGAN bo'lsa
    (current_matchday > total_matchdays) ishlaydi. Aks holda o'ynalmagan
    kelajak turlar ham 0:0 bo'lib, turnir buzilardi.

    Qaytaradi: (ok, reason, info)
      reason: ok | not_started | not_drawn | group_not_over
      info: {season, total_matchdays, awaiting_resolved, pending_resolved}
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_season(cursor)

        cursor.execute(
            "SELECT started, current_matchday FROM cl_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        if not row or not row["started"]:
            cursor.execute("ROLLBACK")
            return False, "not_started", {}

        total = _total_matchdays(cursor, season)
        if total == 0:
            cursor.execute("ROLLBACK")
            return False, "not_drawn", {}
        if row["current_matchday"] <= total:
            cursor.execute("ROLLBACK")
            return False, "group_not_over", {
                "current_matchday": row["current_matchday"],
                "total_matchdays": total,
            }

        resolved = _resolve_matchdays_upto(cursor, season, total)
        cursor.execute("COMMIT")
        logger.warning(
            "ChL: ADMIN guruh o'yinlarini majburiy yopdi (awaiting: %s, 0:0: %s)",
            resolved["awaiting_resolved"], resolved["pending_resolved"],
        )
        return True, "ok", {"season": season, "total_matchdays": total, **resolved}
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("cl_force_close_group: ROLLBACK xatosi")
        logger.exception("cl_force_close_group xatosi (mavsum %s)", season)
        return False, "force_close_failed", {}
    finally:
        conn.close()
