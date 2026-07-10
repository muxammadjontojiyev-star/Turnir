"""
Chempionlar ligasi (ChL) kvalifikatsiyasi.

Qoida (loyiha egasi): liga mavsumi yakunlanganda 5 ta liga reytingidan:
  - har ligadan TOP-6 (5 × 6 = 30 ta), qualified_via='top6'
  - qolgan 7-o'rin egalaridan ENG YAXSHI 2 tasi (achko > gol farqi > urilgan gol),
    qualified_via='best7'
Jami 32 ishtirokchi. Ular telegram_id orqali eslab qolinadi — keyingi mavsumda
boshqa klub tanlasalar ham ChL'da qatnashish huquqi SHU odamda qoladi.

MUHIM: hisoblash reset'dan OLDIN bo'lishi shart (registrations/matches o'chadi),
shuning uchun save_cl_qualifiers() finalize tranzaksiyasi ICHIDA (o'sha cursor
bilan) chaqiriladi. Reytingni o'qish alohida ulanishda (WAL — o'qish erkin).
"""

import logging

from models import get_connection
from rating import calculate_league_rating

logger = logging.getLogger(__name__)

CL_TOP_N = 6          # har ligadan to'g'ridan-to'g'ri o'tadiganlar
CL_BEST_SEVENTH = 2   # eng yaxshi 7-o'rinlar soni
CL_TOTAL = 32


def compute_cl_qualifiers() -> list[dict]:
    """
    Joriy reyting bo'yicha ChL kvalifikantlarini HISOBLAYDI (saqlamaydi).

    Qaytaradi: [{telegram_id, user_id, nickname, league_id, league_name,
                 position, points, goal_difference, goals_for, qualified_via}, ...]
    Bitta odam ikki ligada bo'lsa (nazariy holat) — telegram_id bo'yicha
    birinchi (yuqoriroq) natijasi olinadi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM leagues ORDER BY id")
    leagues = [dict(r) for r in cursor.fetchall()]

    # user_id -> telegram_id xaritasi (bitta so'rov, qoida #24/#49)
    cursor.execute("SELECT id, telegram_id FROM users")
    tg_map = {r["id"]: r["telegram_id"] for r in cursor.fetchall()}
    conn.close()

    qualifiers: list[dict] = []
    sevenths: list[dict] = []

    for lg in leagues:
        table = calculate_league_rating(lg["id"])
        for pos, p in enumerate(table, start=1):
            if pos > CL_TOP_N + 1:
                break
            entry = {
                "telegram_id": tg_map.get(p["user_id"]),
                "user_id": p["user_id"],
                "nickname": p["nickname"],
                "league_id": lg["id"],
                "league_name": lg["name"],
                "position": pos,
                "points": p["points"],
                "goal_difference": p["goal_difference"],
                "goals_for": p["goals_for"],
            }
            if entry["telegram_id"] is None:
                logger.warning("ChL: user_id=%s uchun telegram_id topilmadi, tashlab ketildi", p["user_id"])
                continue
            if pos <= CL_TOP_N:
                entry["qualified_via"] = "top6"
                qualifiers.append(entry)
            else:  # pos == 7
                entry["qualified_via"] = "best7"
                sevenths.append(entry)

    # Eng yaxshi 7-o'rinlar: achko > gol farqi > urilgan gol
    sevenths.sort(
        key=lambda e: (e["points"], e["goal_difference"], e["goals_for"]),
        reverse=True,
    )
    qualifiers.extend(sevenths[:CL_BEST_SEVENTH])

    # telegram_id bo'yicha dedupe (nazariy: bitta odam 2 ligada) — birinchisi qoladi
    seen: set[int] = set()
    unique = []
    for q in qualifiers:
        if q["telegram_id"] in seen:
            continue
        seen.add(q["telegram_id"])
        unique.append(q)
    return unique


def save_cl_qualifiers(cursor, season: int) -> int:
    """
    Kvalifikantlarni cl_qualifiers'ga yozadi (finalize tranzaksiyasi cursor'i bilan).
    INSERT OR IGNORE + UNIQUE(telegram_id, from_season) — idempotent (qoida #38).
    Qaytaradi: yozilgan qatorlar soni.
    """
    rows = compute_cl_qualifiers()
    count = 0
    for q in rows:
        cursor.execute(
            "INSERT OR IGNORE INTO cl_qualifiers "
            "(telegram_id, user_id, nickname, league_id, league_name, position, "
            " points, goal_difference, goals_for, qualified_via, from_season) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (q["telegram_id"], q["user_id"], q["nickname"], q["league_id"],
             q["league_name"], q["position"], q["points"], q["goal_difference"],
             q["goals_for"], q["qualified_via"], season),
        )
        count += cursor.rowcount if cursor.rowcount > 0 else 0
    logger.info("ChL kvalifikatsiyasi: %s ta ishtirokchi saqlandi (mavsum %s)", count, season)
    return count


def get_cl_qualifiers(from_season: int | None = None) -> dict:
    """
    Saqlangan kvalifikantlar ro'yxati (WebApp uchun).
    from_season berilmasa — eng oxirgi mavjud mavsumniki.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if from_season is None:
            cursor.execute("SELECT MAX(from_season) AS s FROM cl_qualifiers")
            row = cursor.fetchone()
            from_season = row["s"] if row and row["s"] else None
        if from_season is None:
            return {"from_season": None, "qualifiers": []}
        cursor.execute(
            "SELECT telegram_id, nickname, league_id, league_name, position, "
            "points, goal_difference, goals_for, qualified_via "
            "FROM cl_qualifiers WHERE from_season = ? "
            "ORDER BY qualified_via = 'best7', league_id, position",
            (from_season,),
        )
        return {"from_season": from_season,
                "qualifiers": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()


def is_cl_qualifier(telegram_id: int, from_season: int | None = None) -> bool:
    """Ishtirokchi ChL kvalifikantimi? (keyingi bosqichlar — ChL guruh qurish uchun)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if from_season is None:
            cursor.execute("SELECT MAX(from_season) AS s FROM cl_qualifiers")
            row = cursor.fetchone()
            from_season = row["s"] if row and row["s"] else None
        if from_season is None:
            return False
        cursor.execute(
            "SELECT 1 FROM cl_qualifiers WHERE telegram_id = ? AND from_season = ?",
            (telegram_id, from_season),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()
