"""
Chempionlar ligasi (ChL) kvalifikatsiyasi.

Qoida (loyiha egasi, 2026-10-14): liga mavsumi yakunlanganda YEVROPA mintaqasining
7 ta 1-ligasi reytingidan (CL_LEAGUES — Osiyo ligalari va 2-ligalar KIRMAYDI):
  - har ligadan TOP-5 (7 × 5 = 35 ta), qualified_via='top5'
  - 6-o'rin egalaridan ENG YAXSHI 1 tasi (achko > gol farqi > urilgan gol),
    qualified_via='best6'
Jami 36 ishtirokchi. (Avval: 5 liga × TOP-7 + eng yaxshi 8-o'rin — 'top7'/'best8';
eski mavsum yozuvlarida shu kodlar qoladi.) Ular telegram_id orqali eslab qolinadi — keyingi mavsumda
boshqa klub tanlasalar ham ChL'da qatnashish huquqi SHU odamda qoladi.

MUHIM: hisoblash reset'dan OLDIN bo'lishi shart (registrations/matches o'chadi),
shuning uchun save_cl_qualifiers() finalize tranzaksiyasi ICHIDA (o'sha cursor
bilan) chaqiriladi. Reytingni o'qish alohida ulanishda (WAL — o'qish erkin).
"""

import logging

from models import get_connection
from rating import calculate_league_rating

logger = logging.getLogger(__name__)

CL_TOP_N = 5          # har ligadan to'g'ridan-to'g'ri o'tadiganlar (2026-10-14: 7 -> 5)
CL_BEST_EIGHTH = 1    # eng yaxshi (CL_TOP_N+1)-o'rinlar soni — hozir eng yaxshi 6-o'rin
CL_TOTAL = 36
# 2026-10-14: ChL/YeL faqat Yevropa mintaqasining 1-ligalaridan (DB liga nomlari).
# Osiyo ligalari (Superliga, Saudi, UAE, J1) va 2-ligalar (LaLiga 2, Championship,
# 2. Bundesliga, Serie B, Ligue 2) kirmaydi. Yangi Yevropa 1-ligasi qo'shilsa — shu yerga.
CL_LEAGUES = ("LaLiga", "Premier Liga", "Bundesliga", "Serie A", "Ligue 1",
              "Liga Portugal", "Süper Lig")
CL_VIA_TOP = "top5"
CL_VIA_BEST = "best6"


def euro_leagues(cursor) -> list[dict]:
    """Kvalifikatsiya beradigan ligalar (CL_LEAGUES), id tartibida. YeL ham shundan oladi."""
    q = ",".join("?" * len(CL_LEAGUES))
    cursor.execute(f"SELECT id, name FROM leagues WHERE name IN ({q}) ORDER BY id", CL_LEAGUES)
    return [dict(r) for r in cursor.fetchall()]


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
    leagues = euro_leagues(cursor)   # 2026-10-14: faqat Yevropa 1-ligalari

    # user_id -> telegram_id xaritasi (bitta so'rov, qoida #24/#49)
    cursor.execute("SELECT id, telegram_id FROM users")
    tg_map = {r["id"]: r["telegram_id"] for r in cursor.fetchall()}
    conn.close()

    qualifiers: list[dict] = []
    eighths: list[dict] = []

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
                entry["qualified_via"] = CL_VIA_TOP
                qualifiers.append(entry)
            else:  # pos == CL_TOP_N + 1 (6-o'rin)
                entry["qualified_via"] = CL_VIA_BEST
                eighths.append(entry)

    # Eng yaxshi 6-o'rin(lar): achko > gol farqi > urilgan gol
    eighths.sort(
        key=lambda e: (e["points"], e["goal_difference"], e["goals_for"]),
        reverse=True,
    )
    qualifiers.extend(eighths[:CL_BEST_EIGHTH])

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
    from_season berilmasa — faol ChL'niki (cl_season_state.cl_qualifier_season).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if from_season is None:
            # 2026-10-09: faol ChL kvalifikantlari (MAX emas — liga yakunlangach yangilari aralashmasin)
            from cl_season_state import cl_qualifier_season
            from_season = cl_qualifier_season(cursor)
        if from_season is None:
            return {"from_season": None, "qualifiers": []}
        cursor.execute(
            "SELECT telegram_id, nickname, league_id, league_name, position, "
            "points, goal_difference, goals_for, qualified_via "
            "FROM cl_qualifiers WHERE from_season = ? "
            "ORDER BY qualified_via IN ('best8', 'best6'), league_id, position",
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
            # 2026-10-09: faol ChL kvalifikantlari (MAX emas — liga yakunlangach yangilari aralashmasin)
            from cl_season_state import cl_qualifier_season
            from_season = cl_qualifier_season(cursor)
        if from_season is None:
            return False
        cursor.execute(
            "SELECT 1 FROM cl_qualifiers WHERE telegram_id = ? AND from_season = ?",
            (telegram_id, from_season),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()
