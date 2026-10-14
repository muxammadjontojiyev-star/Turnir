"""
Osiyo Chempionlar ligasi (OChL) kvalifikatsiyasi (2026-10-15).

Qoida (loyiha egasi): liga mavsumi yakunlanganda OSIYO mintaqasining 4 ta ligasi
reytingidan (AC_LEAGUES) har ligadan TOP-8 (4 x 8 = 32 ishtirokchi),
qualified_via='top8'. Yevropa ligalari (ChL/YeL) va 2-ligalar kirmaydi —
shuning uchun ChL/YeL ro'yxatlari bilan kesishmaydi.

Kirish huquqi ODAMGA (telegram_id) tegishli: keyingi mavsumda boshqa klub
tanlasa ham OChL'da qatnashadi (ac_core.ac_sync_participants).

MUHIM: save_ac_qualifiers() finalize tranzaksiyasi ICHIDA (registrations hali
o'chmagan) chaqiriladi (season_prizes._finalize_league_locked).
"""

import logging

from models import get_connection
from rating import calculate_league_rating

logger = logging.getLogger(__name__)

# Osiyo ligalari (DB nomlari). Yangi Osiyo 1-ligasi qo'shilsa — shu yerga.
AC_LEAGUES = ("Superliga", "Saudi Pro Liga", "UAE Pro Liga", "J1 Liga")
AC_TOP_N = 8                 # har ligadan o'tadiganlar
AC_VIA_TOP = "top8"
AC_TOTAL = 32                # 4 x 8 (Swiss formatida juft son)


def asia_leagues(cursor) -> list[dict]:
    """Kvalifikatsiya beradigan Osiyo ligalari (AC_LEAGUES), id tartibida."""
    q = ",".join("?" * len(AC_LEAGUES))
    cursor.execute(f"SELECT id, name FROM leagues WHERE name IN ({q}) ORDER BY id", AC_LEAGUES)
    return [dict(r) for r in cursor.fetchall()]


def compute_ac_qualifiers() -> list[dict]:
    """
    Joriy reyting bo'yicha OChL kvalifikantlarini HISOBLAYDI (saqlamaydi).
    Qaytaradi: [{telegram_id, user_id, nickname, league_id, league_name,
                 position, points, goal_difference, goals_for, qualified_via}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    leagues = asia_leagues(cursor)
    cursor.execute("SELECT id, telegram_id FROM users")
    tg_map = {r["id"]: r["telegram_id"] for r in cursor.fetchall()}
    conn.close()

    qualifiers: list[dict] = []
    seen: set[int] = set()
    for lg in leagues:
        table = calculate_league_rating(lg["id"])
        for pos, p in enumerate(table[:AC_TOP_N], start=1):
            tg = tg_map.get(p["user_id"])
            if tg is None:
                logger.warning("OChL: user_id=%s uchun telegram_id topilmadi, tashlab ketildi", p["user_id"])
                continue
            if tg in seen:      # nazariy: bitta odam 2 ligada — birinchisi qoladi
                continue
            seen.add(tg)
            qualifiers.append({
                "telegram_id": tg, "user_id": p["user_id"], "nickname": p["nickname"],
                "league_id": lg["id"], "league_name": lg["name"], "position": pos,
                "points": p["points"], "goal_difference": p["goal_difference"],
                "goals_for": p["goals_for"], "qualified_via": AC_VIA_TOP,
            })
    return qualifiers


def save_ac_qualifiers(cursor, season: int) -> int:
    """
    Kvalifikantlarni ac_qualifiers'ga yozadi (finalize tranzaksiyasi cursor'i bilan).
    INSERT OR IGNORE + UNIQUE(telegram_id, from_season) — idempotent (qoida #38).
    Qaytaradi: yozilgan qatorlar soni.
    """
    rows = compute_ac_qualifiers()
    count = 0
    for q in rows:
        cursor.execute(
            "INSERT OR IGNORE INTO ac_qualifiers "
            "(telegram_id, user_id, nickname, league_id, league_name, position, "
            " points, goal_difference, goals_for, qualified_via, from_season) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (q["telegram_id"], q["user_id"], q["nickname"], q["league_id"],
             q["league_name"], q["position"], q["points"], q["goal_difference"],
             q["goals_for"], q["qualified_via"], season),
        )
        count += cursor.rowcount if cursor.rowcount > 0 else 0
    logger.info("OChL kvalifikatsiyasi: %s ta ishtirokchi saqlandi (mavsum %s)", count, season)
    return count


def _latest_season(cursor) -> int | None:
    cursor.execute("SELECT MAX(from_season) AS s FROM ac_qualifiers")
    row = cursor.fetchone()
    return row["s"] if row and row["s"] else None


def get_ac_qualifiers(from_season: int | None = None) -> dict:
    """
    Saqlangan kvalifikantlar ro'yxati (WebApp uchun).
    from_season berilmasa — eng oxirgi mavjud mavsumniki.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if from_season is None:
            from_season = _latest_season(cursor)
        if from_season is None:
            return {"from_season": None, "qualifiers": []}
        cursor.execute(
            "SELECT telegram_id, nickname, league_id, league_name, position, "
            "points, goal_difference, goals_for, qualified_via "
            "FROM ac_qualifiers WHERE from_season = ? "
            "ORDER BY league_id, position",
            (from_season,),
        )
        return {"from_season": from_season,
                "qualifiers": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()


def is_ac_qualifier(telegram_id: int, from_season: int | None = None) -> bool:
    """Ishtirokchi OChL kvalifikantimi?"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if from_season is None:
            from_season = _latest_season(cursor)
        if from_season is None:
            return False
        cursor.execute(
            "SELECT 1 FROM ac_qualifiers WHERE telegram_id = ? AND from_season = ?",
            (telegram_id, from_season),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()
