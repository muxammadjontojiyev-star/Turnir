"""
season_break.py — LIGA MAVSUMLARI ORASIDAGI TANAFFUS (2026-11-01).

Egasi so'rovi: «Mavsumni yakunlash» bosilganda yangi mavsum darhol boshlanmasin — ishtirokchilar
qo'lga kiritgan eF Token bilan auksionda qatnashsin; bosh admin «Yangi mavsumni boshlash»ni bosganda
mavsum ochilsin va auksion g'oliblarining klubi allaqachon band bo'lsin.

Oqim:
  finalize_league_season  -> sovrin, mukofot, ko'tarilish, reset + season_state.league_break = 1
                             (auksion g'oliblari HALI yozilmaydi);
  tanaffus                -> /register yopiq (season_break), auksion ishlaydi;
  start_new_season()      -> faol auksion bo'lsa — rad (auction_active: tugashini kuting yoki bekor qiling);
                             auksion g'oliblari klubiga yoziladi (auction_apply_reservations);
                             league_break = 0, last_finalized_at = hozir (klub tanlash navbati shu paytdan),
                             ko'tarilganlarning band joyi muddati shu paytdan boshlanadi (promotion.py).
Migratsiya (qoida #31): ALTER TABLE season_state ADD COLUMN league_break (bir marta).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


def migrate_season_break(cur) -> None:
    cols = {r["name"] for r in cur.execute("PRAGMA table_info(season_state)")}
    if "league_break" not in cols:
        cur.execute("ALTER TABLE season_state ADD COLUMN league_break INTEGER NOT NULL DEFAULT 0")


def set_break_cur(cur) -> None:
    """Finalize tranzaksiyasi ichida: tanaffus boshlanadi."""
    cur.execute("UPDATE season_state SET league_break = 1 WHERE id = 1")


def is_break() -> bool:
    conn = get_connection()
    try:
        r = conn.execute("SELECT league_break FROM season_state WHERE id = 1").fetchone()
        return bool(r and r["league_break"])
    finally:
        conn.close()


def start_new_season() -> tuple[bool, str | dict]:
    """Sabablar: not_in_break, auction_active ({"lots": N} natijada)."""
    from auction_admin import auction_apply_reservations
    from auction_core import ST_ACTIVE, auction_close_due
    from shop_core import _tx

    def check(cur):
        r = cur.execute("SELECT league_break FROM season_state WHERE id = 1").fetchone()
        if not (r and r["league_break"]):
            return False, "not_in_break"
        auction_close_due(cur)
        n = cur.execute("SELECT COUNT(*) AS n FROM auction_lots WHERE status = ?", (ST_ACTIVE,)).fetchone()["n"]
        return (False, {"code": "auction_active", "lots": n}) if n else (True, None)

    ok, r = _tx(check)
    if not ok:
        return False, r
    # registratsiya hali yopiq (league_break = 1) — g'oliblar klubini boshqalar ola olmaydi
    auction = auction_apply_reservations()

    def open_season(cur):
        from promotion import start_promotion_hold
        cur.execute("UPDATE season_state SET league_break = 0, last_finalized_at = datetime('now') "
                    "WHERE id = 1 AND league_break = 1")
        if not cur.rowcount:                 # parallel bosish — boshqasi allaqachon ochdi
            return False, "not_in_break"
        return True, {"auction": auction, "promotions": start_promotion_hold(cur)}

    ok, res = _tx(open_season)
    if ok:
        logger.info("YANGI LIGA MAVSUMI OCHILDI: auksion %s, ko'tarilganlar %s", auction, res["promotions"])
    return ok, res
