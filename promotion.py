"""
promotion.py — 2-LIGADAN 1-LIGAGA KO'TARILISH: joy band qilish (2026-11-01).

Egasi so'rovi: 2-liganing 1-, 2-, 3-o'rin egalari o'z 1-ligasida joy olishi kerak — joy band turadi,
aks holda ular ulgurmasa liga to'lib qolishi mumkin.

Qoida:
  * liga mavsumi yakunlanganda (season_prizes.finalize, reset'dan OLDIN, o'sha tranzaksiyada)
    har 2-liganing top-PROMOTION_TOP_N'i (kamida 1 o'yin o'ynagan) league_promotions'ga yoziladi;
  * band joy PROMOTION_HOLD_HOURS davomida (yangi mavsum ochilgandan) boshqalar uchun liga sig'imidan
    ayiriladi: 20 o'rin, 3 tasi band -> boshqalar 17 tagacha yoziladi;
  * band egasi shu 1-ligaga navbat (club_priority) va ketma-ket ochilish (league_locked)ni kutmasdan yoziladi;
  * u ro'yxatdan o'tishi bilan (istalgan ligaga) yoki muddat tugashi bilan band hisoblanmaydi —
    holat saqlanmaydi, har so'rovda hisoblanadi (qo'shimcha UPDATE va yugurish xatosi yo'q).
Odam telegram_id bo'yicha eslanadi (akkount qayta yaratilsa ham band joy saqlanadi).
"""

import logging

from config import PROMOTION_HOLD_HOURS, PROMOTION_TOP_N, SECOND_TIER_PARENTS
from models import get_connection

logger = logging.getLogger(__name__)

# faol band: muddati o'tmagan va egasi hali hech qaysi ligada ro'yxatda emas
_ACTIVE = ("p.expires_at > CURRENT_TIMESTAMP AND NOT EXISTS (SELECT 1 FROM registrations r "
           "JOIN users u ON u.id = r.user_id WHERE u.telegram_id = p.telegram_id)")


def init_promotion_table(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS league_promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_number INTEGER NOT NULL,
            telegram_id INTEGER NOT NULL,
            from_league TEXT NOT NULL,
            to_league_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            notified INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (season_number, telegram_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_promotions_to ON league_promotions(to_league_id, expires_at)")


def save_promotions(cur, season: int) -> int:
    """Finalize tranzaksiyasi ichida (reset'dan OLDIN). Idempotent — UNIQUE(season, telegram_id)."""
    from rating import calculate_league_rating
    cur.execute("SELECT id, name FROM leagues")
    ids = {r["name"]: r["id"] for r in cur.fetchall()}
    saved = 0
    for lower, upper in SECOND_TIER_PARENTS.items():
        if lower not in ids or upper not in ids:
            continue
        top = [p for p in calculate_league_rating(ids[lower]) if p.get("played")][:PROMOTION_TOP_N]
        for pos, p in enumerate(top, start=1):
            row = cur.execute("SELECT telegram_id FROM users WHERE id = ?", (p["user_id"],)).fetchone()
            if not row:
                continue
            cur.execute("INSERT OR IGNORE INTO league_promotions (season_number, telegram_id, from_league, "
                        "to_league_id, position, expires_at) VALUES (?, ?, ?, ?, ?, datetime('now', ?))",
                        (season, row["telegram_id"], lower, ids[upper], pos, f"+{PROMOTION_HOLD_HOURS} hours"))
            saved += cur.rowcount
    if saved:
        logger.info("KO'TARILISH: %s-mavsum — %s ishtirokchiga 1-ligada joy band qilindi", season, saved)
    return saved


def reserved_counts(cur) -> dict[int, int]:
    """{1-liga id: faol band joylar soni} — /leagues va ketma-ket ochilish uchun."""
    cur.execute(f"SELECT p.to_league_id, COUNT(*) AS n FROM league_promotions p WHERE {_ACTIVE} "
                "GROUP BY p.to_league_id")
    return {r["to_league_id"]: r["n"] for r in cur.fetchall()}


def reserved_for_others(cur, league_id: int, telegram_id: int | None) -> int:
    """Shu ligada BOSHQALAR uchun band joylar (o'zining band joyi hisoblanmaydi)."""
    return cur.execute(f"SELECT COUNT(*) AS n FROM league_promotions p WHERE p.to_league_id = ? AND {_ACTIVE} "
                       "AND p.telegram_id != ?", (league_id, telegram_id or 0)).fetchone()["n"]


def promotion_for(telegram_id: int) -> dict | None:
    """Faol band joyim: {league_id, league_name, from_league, position, expires_at (ISO UTC)} yoki None."""
    conn = get_connection()
    try:
        r = conn.execute(f"SELECT p.to_league_id, lg.name, p.from_league, p.position, p.expires_at "
                         f"FROM league_promotions p JOIN leagues lg ON lg.id = p.to_league_id "
                         f"WHERE p.telegram_id = ? AND {_ACTIVE} ORDER BY p.id DESC LIMIT 1",
                         (telegram_id,)).fetchone()
        if not r:
            return None
        return {"league_id": r["to_league_id"], "league_name": r["name"], "from_league": r["from_league"],
                "position": r["position"], "expires_at": str(r["expires_at"]).replace(" ", "T") + "Z"}
    finally:
        conn.close()


async def promotion_send_notices() -> int:
    """Scheduler: yangi band joylar egalariga bot xabari (bir marta — avval belgi, keyin xabar, qoida #37/#38)."""
    conn = get_connection()
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT p.id, p.telegram_id, p.from_league, p.position, lg.name AS league, "
            "(SELECT language FROM users WHERE telegram_id = p.telegram_id ORDER BY id DESC LIMIT 1) AS lang "
            "FROM league_promotions p JOIN leagues lg ON lg.id = p.to_league_id "
            "WHERE p.notified = 0 AND p.expires_at > CURRENT_TIMESTAMP").fetchall()]
        if rows:
            conn.execute(f"UPDATE league_promotions SET notified = 1 WHERE id IN ({','.join('?' * len(rows))})",
                         [r["id"] for r in rows])
            conn.commit()
    finally:
        conn.close()
    from notify import notify_user
    for r in rows:
        try:
            await notify_user(r["telegram_id"], "promotion_notify", r["lang"], open_button_key="btn_open_app",
                              league=r["league"], from_league=r["from_league"], pos=r["position"],
                              hours=PROMOTION_HOLD_HOURS)
        except Exception as exc:
            logger.warning("Ko'tarilish xabari (%s) yuborilmadi: %s", r["telegram_id"], exc)
    return len(rows)
