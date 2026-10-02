"""
el_rounds.py — Yevropa ligasi turlarini (matchday) boshqarish.
cl_rounds.py naqshi, ALOHIDA nusxa (ChL'ga tegilmaydi).

Qoida (ChL bilan bir xil):
  • Kuniga BITTA tur. Deadline — 23:30 (Toshkent).
  • Boshida hamma turlar YOPIQ (started=0); admin "O'yinlarni boshlash" -> 1-tur.
  • Har kuni 23:30 da joriy va undan oldingi turlar yopiladi:
        awaiting_confirmation -> CONFIRMED (kiritilgan hisob bilan)
        pending               -> 0:0 durang, CONFIRMED
    va keyingi tur ochiladi.
Idempotent (qoida #38): kuniga bir marta siljiydi (last_advance_date).
"""

import logging
from datetime import datetime, timedelta, timezone

from config import (
    MATCH_STATUS_AWAITING_CONFIRMATION,
    MATCH_STATUS_CONFIRMED,
    MATCH_STATUS_PENDING,
    MATCHDAY_UNLOCK_HOUR,
    TOURNAMENT_TIMEZONE_OFFSET,
)
from models import get_connection

logger = logging.getLogger(__name__)

EL_DEADLINE_MINUTE = 30      # 23:30 (Toshkent)


def _now_local() -> datetime:
    return datetime.now(timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET)))


def _current_season(cursor) -> int:
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def _total_matchdays(cursor, season: int) -> int:
    cursor.execute(
        "SELECT COALESCE(MAX(matchday), 0) AS m FROM el_matches WHERE season = ?",
        (season,),
    )
    return cursor.fetchone()["m"]


def _is_stale_state(cursor, season: int, current: int) -> bool:
    """
    el_state eskirganmi? current > 1, lekin shu mavsumda BIRORTA o'yin
    'pending'dan boshqa holatga o'tmagan (haqiqiy mavsumda har deadline oldingi
    turni confirmed qiladi). Eskirgan holatda tick hech narsa qilmaydi — aks holda
    yangi mavsumning barcha turlari 0:0 bilan yopilib ketardi (ChL saboq'i).
    """
    if not current or current <= 1:
        return False
    cursor.execute(
        "SELECT 1 FROM el_matches WHERE season = ? AND status != 'pending' LIMIT 1",
        (season,),
    )
    return cursor.fetchone() is None


def _rollback(cursor, where: str) -> None:
    try:
        cursor.execute("ROLLBACK")
    except Exception:
        logger.exception("%s: ROLLBACK xatosi", where)


def el_get_state(season: int | None = None) -> dict:
    """{season, started, current_matchday, total_matchdays, finished, stale}"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if season is None:
            season = _current_season(cursor)
        cursor.execute(
            "SELECT started, current_matchday FROM el_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        started = bool(row["started"]) if row else False
        current = row["current_matchday"] if row else 0
        total = _total_matchdays(cursor, season)
        stale = bool(started and _is_stale_state(cursor, season, current))
        return {"season": season, "started": started, "current_matchday": current,
                "total_matchdays": total,
                "finished": bool(started and total and current > total and not stale),
                "stale": stale}
    finally:
        conn.close()


def el_start_rounds(season: int | None = None) -> tuple[bool, str | dict]:
    """Admin turlarni boshlaydi: 1-tur ochiladi. Sabablar: not_drawn, already_started."""
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
            "SELECT started, current_matchday FROM el_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        if row and row["started"]:
            if _is_stale_state(cursor, season, row["current_matchday"]):
                logger.warning("YeL: eskirgan el_state tuzatildi (mavsum %s, %s-tur -> 1-tur)",
                               season, row["current_matchday"])
            else:
                cursor.execute("ROLLBACK")
                return False, "already_started"

        cursor.execute(
            "INSERT INTO el_state (season, started, current_matchday, last_advance_date) "
            "VALUES (?, 1, 1, NULL) "
            "ON CONFLICT(season) DO UPDATE SET started = 1, current_matchday = 1, "
            "last_advance_date = NULL, updated_at = CURRENT_TIMESTAMP",
            (season,),
        )
        cursor.execute("COMMIT")
        logger.info("YeL: turlar boshlandi (mavsum %s), 1-tur ochildi", season)
        return True, {"season": season, "current_matchday": 1}
    except Exception:
        _rollback(cursor, "el_start_rounds")
        raise
    finally:
        conn.close()


def _resolve_matchdays_upto(cursor, season: int, up_to_matchday: int) -> dict:
    """
    awaiting -> confirmed; pending -> 0:0 confirmed ("matchday <= ?" — o'zini
    o'zi tuzatadi, chetda qolgan o'yin play-off'ni bloklamaydi).
    confirmed/rejected'ga tegilmaydi (idempotent).
    """
    cursor.execute(
        "UPDATE el_matches SET status = ? "
        "WHERE season = ? AND matchday <= ? AND status = ?",
        (MATCH_STATUS_CONFIRMED, season, up_to_matchday, MATCH_STATUS_AWAITING_CONFIRMATION),
    )
    awaiting = cursor.rowcount or 0
    cursor.execute(
        "UPDATE el_matches SET score1 = 0, score2 = 0, status = ? "
        "WHERE season = ? AND matchday <= ? AND status = ?",
        (MATCH_STATUS_CONFIRMED, season, up_to_matchday, MATCH_STATUS_PENDING),
    )
    pending = cursor.rowcount or 0
    return {"awaiting_resolved": awaiting, "pending_resolved": pending}


def el_tick(season: int | None = None) -> dict | None:
    """
    Scheduler chaqiradi (daqiqada bir marta). 23:30 o'tgan va bugun hali
    siljitilmagan bo'lsa: joriy turni yopadi va keyingisini ochadi.
    Qaytaradi: siljish/tozalash bo'lsa dict, aks holda None.
    """
    now = _now_local()
    deadline = now.replace(hour=MATCHDAY_UNLOCK_HOUR, minute=EL_DEADLINE_MINUTE,
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
            "FROM el_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        if not row or not row["started"] or row["last_advance_date"] == today:
            cursor.execute("ROLLBACK")
            return None

        total = _total_matchdays(cursor, season)
        current = row["current_matchday"]

        if _is_stale_state(cursor, season, current):
            cursor.execute("ROLLBACK")
            logger.warning("YeL tick O'TKAZIB YUBORILDI: el_state eskirgan (mavsum %s, %s-tur)",
                           season, current)
            return None

        if current > total:   # liga bosqichi tugagan — faqat qolib ketganlarni yopamiz
            healed = _resolve_matchdays_upto(cursor, season, total)
            if healed["awaiting_resolved"] or healed["pending_resolved"]:
                cursor.execute("COMMIT")
                logger.warning("YeL: liga bosqichi tugagan, chetda qolgan o'yinlar yopildi "
                               "(awaiting: %s, 0:0: %s)",
                               healed["awaiting_resolved"], healed["pending_resolved"])
                return {"season": season, "closed_matchday": total,
                        "opened_matchday": current, **healed}
            cursor.execute("ROLLBACK")
            return None

        resolved = _resolve_matchdays_upto(cursor, season, current)
        cursor.execute(
            "UPDATE el_state SET current_matchday = ?, last_advance_date = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE season = ?",
            (current + 1, today, season),
        )
        cursor.execute("COMMIT")
        logger.info("YeL: %s-tur yopildi (awaiting: %s, 0:0: %s) -> %s-tur ochildi",
                    current, resolved["awaiting_resolved"],
                    resolved["pending_resolved"], current + 1)
        return {"season": season, "closed_matchday": current,
                "opened_matchday": current + 1, **resolved}
    except Exception:
        _rollback(cursor, "el_tick")
        raise
    finally:
        conn.close()


def el_matchday_open(matchday: int, season: int | None = None) -> bool:
    """Shu tur natija kiritish uchun ochiqmi? (server tekshiruvi — qoida #41)"""
    st = el_get_state(season)
    return bool(st["started"]) and matchday == st["current_matchday"]


def el_force_close_group(season: int | None = None) -> tuple[bool, str, dict]:
    """
    ADMIN: liga bosqichidagi hal qilinmagan o'yinlarni DARHOL yopadi (23:30 kutmasdan).
    Faqat liga bosqichi TUGAGAN bo'lsa (current_matchday > total) — aks holda
    o'ynalmagan kelajak turlar 0:0 bo'lib ketardi (qoida #07).
    reason: ok | not_started | not_drawn | group_not_over | force_close_failed
    """
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        if season is None:
            season = _current_season(cursor)
        cursor.execute(
            "SELECT started, current_matchday FROM el_state WHERE season = ?", (season,))
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
            return False, "group_not_over", {"current_matchday": row["current_matchday"],
                                             "total_matchdays": total}

        resolved = _resolve_matchdays_upto(cursor, season, total)
        cursor.execute("COMMIT")
        logger.warning("YeL: ADMIN liga bosqichini majburiy yopdi (awaiting: %s, 0:0: %s)",
                       resolved["awaiting_resolved"], resolved["pending_resolved"])
        return True, "ok", {"season": season, "total_matchdays": total, **resolved}
    except Exception:
        _rollback(cursor, "el_force_close_group")
        logger.exception("el_force_close_group xatosi (mavsum %s)", season)
        return False, "force_close_failed", {}
    finally:
        conn.close()
