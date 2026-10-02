"""
Yevropa ligasi (YeL) kvalifikatsiyasi.

Qoida (loyiha egasi): liga mavsumi yakunlanganda 5 ta liga reytingidan:
  - har ligadan 8..14-o'rinlar, qualified_via='top14'
    (ChL'ga ketgan ENG YAXSHI 8-o'rin bundan CHIQARILADI — u ChL'da)
  - 15-o'rin egalaridan ENG YAXSHI 2 tasi (achko > gol farqi > urilgan gol),
    qualified_via='best15'
Jami: 4 (qolgan 8-o'rinlar) + 30 (9..14) + 2 = 36 ishtirokchi (ChL bilan teng —
Swiss formatida juft son, hech kim o'yinsiz qolmaydi).

Kirish huquqi ODAMGA (telegram_id) tegishli: keyingi mavsumda boshqa klub
tanlasa ham YeL'da qatnashadi (el_core.el_sync_participants).

ChL bilan bog'liqlik: 8-o'rin chegarasi cl_qualification konstantalaridan
hisoblanadi (qoida #17) — ChL qoidasi o'zgarsa, YeL avtomatik moslashadi.
ChL'ga o'tganlar to'plami save_el_qualifiers'da AYNAN saqlangan cl_qualifiers
yozuvlaridan olinadi (shu tranzaksiya cursor'i) — ikki ro'yxat kesishmaydi.

MUHIM: save_el_qualifiers() finalize tranzaksiyasi ICHIDA, save_cl_qualifiers()
dan KEYIN chaqiriladi (season_prizes._finalize_league_locked).
"""

import logging

from cl_qualification import CL_TOP_N, compute_cl_qualifiers
from models import get_connection
from rating import calculate_league_rating

logger = logging.getLogger(__name__)

EL_FIRST_POS = CL_TOP_N + 1   # 8 — ChL'ning to'g'ridan-to'g'ri chegarasidan keyin
EL_LAST_POS = 14              # har ligadan oxirgi to'g'ridan-to'g'ri o'rin
EL_BEST_POS = EL_LAST_POS + 1 # 15 — eng yaxshilari saralanadigan o'rin
EL_BEST_COUNT = 2             # eng yaxshi 15-o'rinlar soni
EL_TOTAL = 36


def compute_el_qualifiers(exclude_telegram_ids: set[int] | None = None) -> list[dict]:
    """
    Joriy reyting bo'yicha YeL kvalifikantlarini HISOBLAYDI (saqlamaydi).

    exclude_telegram_ids — ChL'ga o'tganlar (eng yaxshi 8-o'rin shu yerda).
    None bo'lsa compute_cl_qualifiers() dan olinadi (mustaqil chaqiruv uchun).

    Qaytaradi: [{telegram_id, user_id, nickname, league_id, league_name,
                 position, points, goal_difference, goals_for, qualified_via}, ...]
    """
    if exclude_telegram_ids is None:
        exclude_telegram_ids = {q["telegram_id"] for q in compute_cl_qualifiers()}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM leagues ORDER BY id")
    leagues = [dict(r) for r in cursor.fetchall()]

    # user_id -> telegram_id xaritasi (bitta so'rov, qoida #24/#49)
    cursor.execute("SELECT id, telegram_id FROM users")
    tg_map = {r["id"]: r["telegram_id"] for r in cursor.fetchall()}
    conn.close()

    qualifiers: list[dict] = []
    best_pool: list[dict] = []

    for lg in leagues:
        table = calculate_league_rating(lg["id"])
        for pos, p in enumerate(table, start=1):
            if pos < EL_FIRST_POS:
                continue
            if pos > EL_BEST_POS:
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
                logger.warning("YeL: user_id=%s uchun telegram_id topilmadi, tashlab ketildi", p["user_id"])
                continue
            if entry["telegram_id"] in exclude_telegram_ids:
                continue  # ChL'ga o'tgan (eng yaxshi 8-o'rin)
            if pos <= EL_LAST_POS:
                entry["qualified_via"] = "top14"
                qualifiers.append(entry)
            else:  # pos == 15
                entry["qualified_via"] = "best15"
                best_pool.append(entry)

    # Eng yaxshi 15-o'rinlar: achko > gol farqi > urilgan gol
    best_pool.sort(
        key=lambda e: (e["points"], e["goal_difference"], e["goals_for"]),
        reverse=True,
    )
    qualifiers.extend(best_pool[:EL_BEST_COUNT])

    # telegram_id bo'yicha dedupe (nazariy: bitta odam 2 ligada) — birinchisi qoladi
    seen: set[int] = set()
    unique = []
    for q in qualifiers:
        if q["telegram_id"] in seen:
            continue
        seen.add(q["telegram_id"])
        unique.append(q)
    return unique


def save_el_qualifiers(cursor, season: int) -> int:
    """
    Kvalifikantlarni el_qualifiers'ga yozadi (finalize tranzaksiyasi cursor'i bilan).
    save_cl_qualifiers() dan KEYIN chaqirilishi shart: ChL to'plami shu
    tranzaksiyadagi cl_qualifiers'dan o'qiladi.
    INSERT OR IGNORE + UNIQUE(telegram_id, from_season) — idempotent (qoida #38).
    Qaytaradi: yozilgan qatorlar soni.
    """
    cursor.execute("SELECT telegram_id FROM cl_qualifiers WHERE from_season = ?", (season,))
    cl_ids = {r["telegram_id"] for r in cursor.fetchall()}

    rows = compute_el_qualifiers(exclude_telegram_ids=cl_ids)
    count = 0
    for q in rows:
        cursor.execute(
            "INSERT OR IGNORE INTO el_qualifiers "
            "(telegram_id, user_id, nickname, league_id, league_name, position, "
            " points, goal_difference, goals_for, qualified_via, from_season) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (q["telegram_id"], q["user_id"], q["nickname"], q["league_id"],
             q["league_name"], q["position"], q["points"], q["goal_difference"],
             q["goals_for"], q["qualified_via"], season),
        )
        count += cursor.rowcount if cursor.rowcount > 0 else 0
    logger.info("YeL kvalifikatsiyasi: %s ta ishtirokchi saqlandi (mavsum %s)", count, season)
    return count


def _latest_season(cursor) -> int | None:
    cursor.execute("SELECT MAX(from_season) AS s FROM el_qualifiers")
    row = cursor.fetchone()
    return row["s"] if row and row["s"] else None


def get_el_qualifiers(from_season: int | None = None) -> dict:
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
            "FROM el_qualifiers WHERE from_season = ? "
            "ORDER BY qualified_via = 'best15', league_id, position",
            (from_season,),
        )
        return {"from_season": from_season,
                "qualifiers": [dict(r) for r in cursor.fetchall()]}
    finally:
        conn.close()


def is_el_qualifier(telegram_id: int, from_season: int | None = None) -> bool:
    """Ishtirokchi YeL kvalifikantimi?"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if from_season is None:
            from_season = _latest_season(cursor)
        if from_season is None:
            return False
        cursor.execute(
            "SELECT 1 FROM el_qualifiers WHERE telegram_id = ? AND from_season = ?",
            (telegram_id, from_season),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()
