"""
Konferensiya ligasi (KL, UEFA Conference League) kvalifikatsiyasi (2026-11-01, egasi tasdiqladi).

Qoida: liga mavsumi yakunlanganda 13 ta Yevropa ligasidan ChL va YeL o'rinlaridan KEYINGI o'rinlar
(cl_qualification.EURO_QUOTAS + CO_QUOTAS): katta 5 liga — 9–12-o'rin, Liga Portugal va Eredivisie — 7–9,
Jupiler Pro League, Süper Lig, Chance Liga, RPL — 5–6, Eliteserien va Greek Super League — 3-o'rin.
Jami 36 (Swiss formatida juft son). qualified_via='top'. Osiyo ligalari kirmaydi.
ChL/YeL'ga o'tganlar (shu tranzaksiyadagi cl_qualifiers / el_qualifiers) chiqarib tashlanadi — ro'yxatlar
kesishmaydi (nazariy: bitta odam 2 ligada).

Kirish huquqi ODAMGA (telegram_id) tegishli: keyingi mavsumda boshqa klub tanlasa ham KL'da qatnashadi
(co_core.co_sync_participants).

MUHIM: save_co_qualifiers() finalize tranzaksiyasi ICHIDA, save_el_qualifiers() dan KEYIN chaqiriladi
(season_prizes._finalize_league_locked).
"""

import logging

from cl_qualification import EURO_QUOTAS, euro_leagues
from models import get_connection
from rating import calculate_league_rating

logger = logging.getLogger(__name__)

# liga -> KL o'rinlari soni (ChL + YeL kvotasidan keyin). Yangi Yevropa ligasi — shu yerga ham.
CO_QUOTAS: dict[str, int] = {
    "LaLiga": 4, "Premier Liga": 4, "Bundesliga": 4, "Serie A": 4, "Ligue 1": 4,
    "Liga Portugal": 3, "Eredivisie": 3,
    "Jupiler Pro League": 2, "Süper Lig": 2, "Chance Liga": 2, "RPL": 2,
    "Eliteserien": 1, "Greek Super League": 1,
}
CO_VIA_TOP = "top"
CO_TOTAL = sum(CO_QUOTAS.values())      # 36


def co_range(league_name: str) -> tuple[int, int]:
    """(birinchi, oxirgi) KL o'rni shu ligada; kvota yo'q bo'lsa (0, -1)."""
    cl_n, el_n = EURO_QUOTAS.get(league_name, (0, 0))
    n = CO_QUOTAS.get(league_name, 0)
    return cl_n + el_n + 1, cl_n + el_n + n


def compute_co_qualifiers(exclude_telegram_ids: set[int] | None = None) -> list[dict]:
    """Joriy reyting bo'yicha KL kvalifikantlarini HISOBLAYDI (saqlamaydi)."""
    exclude = exclude_telegram_ids or set()
    conn = get_connection()
    cursor = conn.cursor()
    leagues = euro_leagues(cursor)
    cursor.execute("SELECT id, telegram_id FROM users")
    tg_map = {r["id"]: r["telegram_id"] for r in cursor.fetchall()}
    conn.close()

    qualifiers: list[dict] = []
    seen: set[int] = set()
    for lg in leagues:
        first, last = co_range(lg["name"])
        if last < first:
            continue
        table = calculate_league_rating(lg["id"])
        for pos, p in enumerate(table, start=1):
            if pos < first:
                continue
            if pos > last:
                break
            tg = tg_map.get(p["user_id"])
            if tg is None:
                logger.warning("KL: user_id=%s uchun telegram_id topilmadi, tashlab ketildi", p["user_id"])
                continue
            if tg in seen or tg in exclude:
                continue
            seen.add(tg)
            qualifiers.append({
                "telegram_id": tg, "user_id": p["user_id"], "nickname": p["nickname"],
                "league_id": lg["id"], "league_name": lg["name"], "position": pos,
                "points": p["points"], "goal_difference": p["goal_difference"],
                "goals_for": p["goals_for"], "qualified_via": CO_VIA_TOP,
            })
    return qualifiers


def save_co_qualifiers(cursor, season: int) -> int:
    """
    Kvalifikantlarni co_qualifiers'ga yozadi (finalize tranzaksiyasi cursor'i bilan, ChL va YeL'dan KEYIN).
    INSERT OR IGNORE + UNIQUE(telegram_id, from_season) — idempotent (qoida #38).
    """
    cursor.execute("SELECT telegram_id FROM cl_qualifiers WHERE from_season = ? "
                   "UNION SELECT telegram_id FROM el_qualifiers WHERE from_season = ?", (season, season))
    taken = {r["telegram_id"] for r in cursor.fetchall()}
    count = 0
    for q in compute_co_qualifiers(taken):
        cursor.execute(
            "INSERT OR IGNORE INTO co_qualifiers "
            "(telegram_id, user_id, nickname, league_id, league_name, position, "
            " points, goal_difference, goals_for, qualified_via, from_season) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (q["telegram_id"], q["user_id"], q["nickname"], q["league_id"],
             q["league_name"], q["position"], q["points"], q["goal_difference"],
             q["goals_for"], q["qualified_via"], season),
        )
        count += cursor.rowcount if cursor.rowcount > 0 else 0
    logger.info("KL kvalifikatsiyasi: %s ta ishtirokchi saqlandi (mavsum %s)", count, season)
    return count


def _latest_season(cursor) -> int | None:
    cursor.execute("SELECT MAX(from_season) AS s FROM co_qualifiers")
    row = cursor.fetchone()
    return row["s"] if row and row["s"] else None


def get_co_qualifiers(from_season: int | None = None) -> dict:
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
            "FROM co_qualifiers WHERE from_season = ? "
            "ORDER BY league_id, position",
            (from_season,),
        )
        return {"from_season": from_season,
                "qualifiers": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()


def is_co_qualifier(telegram_id: int, from_season: int | None = None) -> bool:
    """Ishtirokchi KL kvalifikantimi?"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if from_season is None:
            from_season = _latest_season(cursor)
        if from_season is None:
            return False
        cursor.execute(
            "SELECT 1 FROM co_qualifiers WHERE telegram_id = ? AND from_season = ?",
            (telegram_id, from_season),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()
