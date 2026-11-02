"""
leagues_region.py — LIGALAR: MINTAQA (Yevropa / Osiyo), FAOLLIK va TARTIB (2026-11-01).

Egasi so'rovi:
  * 6 ta yangi Yevropa ligasi — Rossiya, Niderlandiya, Belgiya, Chexiya, Norvegiya, Gretsiya
    (ChL va YeL'ga yo'llanma beradi — cl_qualification.EURO_QUOTAS);
  * 2-ligalar O'CHIRILMAYDI — nofaol (is_active = 0): botda ko'rinmaydi, ma'lumot bazada qoladi;
  * ligalar mintaqa tablarida — Yevropa, Osiyo, Janubiy Amerika, Shimoliy Amerika (2026-11-02); navbat bilan ochilish har
    mintaqada alohida;
  * 2026-11-02: bosh admin har ligani yoqib/o'chira oladi (leagues_admin.py) — migratsiya is_active ga
    tegmaydi (faqat bo'sh 2-ligalar bir marta nofaol qilinadi, admin qayta yoqsa — yoqilgan qoladi).

Migratsiya (qoida #31, idempotent — har ishga tushishda xavfsiz):
  leagues ga region ('eu' | 'asia'), is_active (1/0), sort_order ustunlari; yangi ligalar INSERT OR IGNORE;
  2-ligalar nofaol — FAQAT ro'yxati bo'sh bo'lsa (joriy mavsum yakunlanmagan bo'lsa, sovrin va
  ko'tarilish hisoblanishi uchun qoladi; season_break.start_new_season ham chaqiradi).
Klublar: static/league_clubs_eu2.js va league_clubs_eu2.py (nomlar bir xil).
"""

import logging

logger = logging.getLogger(__name__)

REGION_EU, REGION_ASIA, REGION_SA = "eu", "asia", "sa"   # 2026-11-02: Janubiy Amerika
REGION_NA = "na"   # 2026-11-02: Shimoliy Amerika (MLS)
MLS_SEATS = 20     # MLS o'rinlari (klublar 30 ta) — boshqa ligalar bilan bir xil 38 tur
# (nom, max_players = klublar soni, mintaqa, tartib) — tartib: mintaqa ichida navbat bilan ochilish
LEAGUE_ORDER = (
    ("LaLiga", None, REGION_EU, 1), ("Premier Liga", None, REGION_EU, 2), ("Bundesliga", None, REGION_EU, 3),
    ("Serie A", None, REGION_EU, 4), ("Ligue 1", None, REGION_EU, 5), ("Liga Portugal", None, REGION_EU, 6),
    ("Süper Lig", None, REGION_EU, 7),
    # 2026-11-01: yangi Yevropa ligalari (2026/27 mavsumi tarkibi bo'yicha klublar soni)
    ("RPL", 16, REGION_EU, 8), ("Eredivisie", 18, REGION_EU, 9), ("Jupiler Pro League", 18, REGION_EU, 10),
    ("Chance Liga", 16, REGION_EU, 11), ("Eliteserien", 16, REGION_EU, 12), ("Greek Super League", 14, REGION_EU, 13),
    ("Superliga", None, REGION_ASIA, 21), ("Saudi Pro Liga", None, REGION_ASIA, 22),
    ("UAE Pro Liga", None, REGION_ASIA, 23), ("J1 Liga", None, REGION_ASIA, 24),
    # 2026-11-02: Janubiy Amerika — Braziliya Seriya A (2026 mavsumi, 20 klub)
    ("Brasileirão", 20, REGION_SA, 31),
    # 2026-11-02: Janubiy Amerika — Kolumbiya Primera A (2026 mavsumi, 20 klub)
    ("Primera A", 20, REGION_SA, 32),
    # 2026-11-02: Shimoliy Amerika — MLS (2026 mavsumi). 30 klubdan tanlanadi, lekin O'RIN 20 ta
    # (MLS_SEATS): 30 kishida 58 tur bo'lib, mavsum boshqa ligalardan ~10 kun uzoq cho'zilardi.
    ("MLS", MLS_SEATS, REGION_NA, 41),
)
SECOND_TIER_SORT = 90          # nofaol 2-ligalar ro'yxat oxirida (qayta yoqilsa)


def migrate_leagues_region(cur) -> None:
    cols = {r["name"] for r in cur.execute("PRAGMA table_info(leagues)")}
    if "region" not in cols:
        cur.execute(f"ALTER TABLE leagues ADD COLUMN region TEXT NOT NULL DEFAULT '{REGION_EU}'")
    if "is_active" not in cols:
        cur.execute("ALTER TABLE leagues ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "sort_order" not in cols:
        cur.execute("ALTER TABLE leagues ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
    if "admin_set" not in cols:      # 2026-11-02: admin yoqib/o'chirgan — avtomatik nofaol qilish tegmaydi
        cur.execute("ALTER TABLE leagues ADD COLUMN admin_set INTEGER")
    for name, max_players, region, order in LEAGUE_ORDER:
        if max_players:
            cur.execute("INSERT OR IGNORE INTO leagues (name, max_players, status) VALUES (?, ?, 'open')",
                        (name, max_players))
        cur.execute("UPDATE leagues SET region = ?, sort_order = ? WHERE name = ?", (region, order, name))
    from config import SECOND_TIER_LEAGUES
    q = ",".join("?" * len(SECOND_TIER_LEAGUES))
    cur.execute(f"UPDATE leagues SET sort_order = ? WHERE name IN ({q})", (SECOND_TIER_SORT, *SECOND_TIER_LEAGUES))
    deactivate_empty_second_tiers(cur)


def deactivate_empty_second_tiers(cur) -> int:
    """2-ligalarni nofaol qiladi — faqat ro'yxati bo'sh bo'lsa (mavsum yakunlanib tozalangan)."""
    from config import SECOND_TIER_LEAGUES
    q = ",".join("?" * len(SECOND_TIER_LEAGUES))
    cur.execute(f"UPDATE leagues SET is_active = 0 WHERE is_active = 1 AND admin_set IS NULL AND name IN ({q}) "
                "AND NOT EXISTS (SELECT 1 FROM registrations r WHERE r.league_id = leagues.id)",
                SECOND_TIER_LEAGUES)
    if cur.rowcount:
        logger.info("LIGALAR: %s ta 2-liga nofaol qilindi (ma'lumot saqlanadi)", cur.rowcount)
    return cur.rowcount
