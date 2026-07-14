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
    cursor.execute("SELECT current_season FROM season_state WHERE id = 1")
    row = cursor.fetchone()
    return row["current_season"] if row else 1


def _total_matchdays(cursor, season: int) -> int:
    cursor.execute(
        "SELECT COALESCE(MAX(matchday), 0) AS m FROM cl_matches WHERE season = ?",
        (season,),
    )
    return cursor.fetchone()["m"]


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
        return {"season": season, "started": started, "current_matchday": current,
                "total_matchdays": total,
                "finished": bool(started and total and current > total)}
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

        cursor.execute("SELECT started FROM cl_state WHERE season = ?", (season,))
        row = cursor.fetchone()
        if row and row["started"]:
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


def _resolve_matchday(cursor, season: int, matchday: int) -> dict:
    """Deadline yopilishi (variant A): awaiting -> confirmed; pending -> 0:0 confirmed."""
    cursor.execute(
        "UPDATE cl_matches SET status = ? "
        "WHERE season = ? AND matchday = ? AND status = ?",
        (MATCH_STATUS_CONFIRMED, season, matchday, MATCH_STATUS_AWAITING_CONFIRMATION),
    )
    awaiting = cursor.rowcount or 0
    cursor.execute(
        "UPDATE cl_matches SET score1 = 0, score2 = 0, status = ? "
        "WHERE season = ? AND matchday = ? AND status = ?",
        (MATCH_STATUS_CONFIRMED, season, matchday, MATCH_STATUS_PENDING),
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
        if current > total:                            # guruh bosqichi tugagan
            cursor.execute("ROLLBACK")
            return None

        resolved = _resolve_matchday(cursor, season, current)
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
