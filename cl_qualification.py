"""
Chempionlar ligasi (ChL) kvalifikatsiyasi.

Qoida (loyiha egasi, 2026-11-01): liga mavsumi yakunlanganda 13 ta YEVROPA ligasi reytingidan
LIGA KUCHIGA qarab (EURO_QUOTAS): katta 5 liga — 1–4-o'rin, Portugaliya va Niderlandiya — 1–3,
Belgiya, Turkiya, Chexiya, Rossiya — 1–2, Norvegiya va Gretsiya — 1-o'rin; qualified_via='top5'.
(2026-10-14 — 2026-11-01: 7 liga × top-5 + eng yaxshi 6-o'rin.) Osiyo ligalari va 2-ligalar KIRMAYDI.
Jami 36 ishtirokchi. (Undan avval: 5 liga × TOP-7 + eng yaxshi 8-o'rin — 'top7'/'best8';
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

# 2026-11-01: egasi qarori — 13 ta Yevropa ligasi, yo'llanmalar LIGA KUCHIGA qarab (UEFA reytingiga o'xshash).
# liga -> (ChL o'rinlari: 1..cl, YeL o'rinlari: cl+1..cl+el). Jami ChL 36, YeL 36. Yangi liga — shu yerga.
EURO_QUOTAS: dict[str, tuple[int, int]] = {
    "LaLiga": (4, 4), "Premier Liga": (4, 4), "Bundesliga": (4, 4), "Serie A": (4, 4), "Ligue 1": (4, 4),
    "Liga Portugal": (3, 3), "Eredivisie": (3, 3),
    "Jupiler Pro League": (2, 2), "Süper Lig": (2, 2), "Chance Liga": (2, 2), "RPL": (2, 2),
    "Eliteserien": (1, 1), "Greek Super League": (1, 1),
}
CL_TOTAL = sum(cl for cl, _ in EURO_QUOTAS.values())       # 36
# Osiyo ligalari va 2-ligalar kirmaydi. (Avval: 7 liga × top-5 + eng yaxshi 6-o'rin — 'top5'/'best6';
# eski mavsum yozuvlarida shu kodlar qoladi.)
CL_LEAGUES = tuple(EURO_QUOTAS)
CL_VIA_TOP = "top5"            # kod o'zgarmadi (frontend/tarix bilan moslik) — ma'nosi: liga kvotasi ichida
CL_VIA_BEST = "best6"          # endi ishlatilmaydi (eski yozuvlar uchun)


def euro_leagues(cursor) -> list[dict]:
    """Kvalifikatsiya beradigan ligalar (CL_LEAGUES), id tartibida. YeL ham shundan oladi."""
    q = ",".join("?" * len(CL_LEAGUES))
    cursor.execute(f"SELECT id, name FROM leagues WHERE name IN ({q}) AND COALESCE(is_active, 1) = 1 "
                   "ORDER BY sort_order, id", CL_LEAGUES)
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

    for lg in leagues:
        quota = EURO_QUOTAS.get(lg["name"], (0, 0))[0]
        table = calculate_league_rating(lg["id"])
        for pos, p in enumerate(table, start=1):
            if pos > quota:
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
                "qualified_via": CL_VIA_TOP,
            }
            if entry["telegram_id"] is None:
                logger.warning("ChL: user_id=%s uchun telegram_id topilmadi, tashlab ketildi", p["user_id"])
                continue
            qualifiers.append(entry)

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
