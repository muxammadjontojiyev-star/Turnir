"""
auction_admin.py — AUKSION: bosh admin amallari, yakun xabarlari va yangi mavsumda klubga yozish (2026-10-30).

  - auction_create      — lot: liga + klub (pt_formats.LEAGUE_CLUBS dagi nom), boshlang'ich narx, qadam, muddat (soat).
                          Bir klub bir vaqtda faqat bitta faol / qo'llanmagan lotda (club_on_auction).
  - auction_cancel      — faqat faol lot; yetakchiga muzlatilgan summa qaytadi.
  - auction_admin_list  — faol va oxirgi lotlar (admin paneli).
  - auction_take_end_notices / auction_take_apply_notices — scheduler: yuborilmagan xabarlar (bir martalik belgilanadi).
  - auction_apply_reservations — liga mavsumi yangilangach (season_prizes, reset'dan KEYIN): g'oliblar
    klubiga avtomatik yoziladi (registrations). Yozib bo'lmasa (liga to'la / akkaunt o'chgan / allaqachon
    ro'yxatda) — 'failed' va muzlatilgan summa qaytariladi.
"""

import logging

from config import AUCTION_ENDED_SHOWN, AUCTION_MAX_HOURS, AUCTION_MIN_HOURS, AUCTION_PRICE_MAX
from auction_core import (ST_ACTIVE, ST_APPLIED, ST_CANCELLED, ST_ENDED, ST_FAILED, TX_REFUND,
                          _LOT_COLS, _LOT_FROM, auction_close_due)
from models import get_connection
from shop_core import _int, _tx
from wallet import wallet_change

logger = logging.getLogger(__name__)


def auction_create(admin_tg: int, league_id, club_name: str, start_price, min_step, hours) -> tuple[bool, str | dict]:
    """Sabablar: league_not_found, bad_club, bad_price, bad_step, bad_hours, club_on_auction."""
    from pt_formats import LEAGUE_CLUBS
    lid, price, step, hrs = _int(league_id), _int(start_price), _int(min_step), _int(hours)
    club = (club_name or "").strip()
    if price is None or not 0 < price <= AUCTION_PRICE_MAX:
        return False, "bad_price"
    if step is None or not 0 < step <= AUCTION_PRICE_MAX:
        return False, "bad_step"
    if hrs is None or not AUCTION_MIN_HOURS <= hrs <= AUCTION_MAX_HOURS:
        return False, "bad_hours"

    def run(cur):
        cur.execute("SELECT name FROM leagues WHERE id = ?", (lid,))
        lg = cur.fetchone()
        if not lg:
            return False, "league_not_found"
        if club not in LEAGUE_CLUBS.get(lg["name"], ()):
            return False, "bad_club"
        cur.execute("SELECT 1 FROM auction_lots WHERE league_id = ? AND club_name = ? AND "
                    "(status = ? OR (status = ? AND winner_user_id IS NOT NULL))", (lid, club, ST_ACTIVE, ST_ENDED))
        if cur.fetchone():
            return False, "club_on_auction"
        cur.execute("INSERT INTO auction_lots (league_id, club_name, start_price, min_step, ends_at, created_by) "
                    "VALUES (?, ?, ?, ?, datetime('now', ?), ?)", (lid, club, price, step, f"+{hrs} hours", admin_tg))
        return True, {"id": cur.lastrowid, "league_name": lg["name"], "club_name": club}

    ok, r = _tx(run)
    if ok:
        logger.info("AUKSION #%s: %s (%s) sotuvga qo'yildi, %s eF dan, %s soat", r["id"], club, r["league_name"], price, hrs)
    return ok, r


def auction_cancel(lot_id) -> tuple[bool, str | dict]:
    """Sabablar: not_found, wrong_status. Natijada yetakchi (xabar uchun) — bo'lsa."""
    lid = _int(lot_id)

    def run(cur):
        auction_close_due(cur)
        cur.execute("SELECT l.*, u.telegram_id, u.language FROM auction_lots l LEFT JOIN users u ON u.id = l.leader_user_id "
                    "WHERE l.id = ?", (lid,))
        lot = cur.fetchone()
        if not lot:
            return False, "not_found"
        cur.execute("UPDATE auction_lots SET status = ?, ended_at = CURRENT_TIMESTAMP, end_notified = 1 "
                    "WHERE id = ? AND status = ?", (ST_CANCELLED, lid, ST_ACTIVE))
        if cur.rowcount == 0:
            return False, "wrong_status"
        info = {"club_name": lot["club_name"], "leader": None}
        if lot["leader_user_id"]:
            wallet_change(cur, lot["leader_user_id"], lot["current_bid"], TX_REFUND, lot["leader_bid_id"])
            info["leader"] = {"telegram_id": lot["telegram_id"], "language": lot["language"], "amount": lot["current_bid"]}
        return True, info

    return _tx(run)


def auction_admin_list() -> dict:
    _tx(lambda cur: (True, auction_close_due(cur)))
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {_LOT_COLS} {_LOT_FROM}WHERE l.status = ? ORDER BY l.ends_at", (ST_ACTIVE,))
        from pt_rounds import utc_to_local_text                 # Toshkent vaqti (DB — UTC)
        active = [{**dict(r), "ends_local": utc_to_local_text(r["ends_at"])} for r in cur.fetchall()]
        cur.execute(f"SELECT {_LOT_COLS} {_LOT_FROM}WHERE l.status != ? ORDER BY l.id DESC LIMIT ?",
                    (ST_ACTIVE, AUCTION_ENDED_SHOWN))
        return {"active": active, "recent": [dict(r) for r in cur.fetchall()]}
    finally:
        conn.close()


def _take(flag: str, where: str) -> list[dict]:
    def run(cur):
        auction_close_due(cur)
        cur.execute(f"SELECT l.id, l.club_name, lg.name AS league_name, l.current_bid, l.status, "
                    f"u.telegram_id, u.language, u.nickname, u.username FROM auction_lots l "
                    f"JOIN leagues lg ON lg.id = l.league_id LEFT JOIN users u ON u.id = l.winner_user_id "
                    f"WHERE {flag} = 0 AND {where}")
        rows = [dict(r) for r in cur.fetchall()]
        if rows:
            cur.execute(f"UPDATE auction_lots SET {flag} = 1 WHERE id IN ({','.join('?' * len(rows))})",
                        [r["id"] for r in rows])
        return True, rows
    return _tx(run)[1]


def auction_take_end_notices() -> list[dict]:
    """Yakunlangan, xabari hali yuborilmagan lotlar (g'olibli yoki takliflarsiz)."""
    return _take("end_notified", f"l.status IN ('{ST_ENDED}', '{ST_APPLIED}', '{ST_FAILED}')")


def auction_take_apply_notices() -> list[dict]:
    """Yangi mavsumda klubga yozilgan / yozib bo'lmagan g'oliblar (xabari yuborilmagan)."""
    return _take("apply_notified", f"l.status IN ('{ST_APPLIED}', '{ST_FAILED}')")


def auction_apply_reservations() -> dict:
    """Mavsum yangilangach: g'oliblarni klubiga yozadi. Idempotent (faqat 'ended' + g'olibli lotlar)."""
    def run(cur):
        auction_close_due(cur)
        cur.execute("SELECT id, league_id, club_name, winner_user_id, current_bid, leader_bid_id FROM auction_lots "
                    "WHERE status = ? AND winner_user_id IS NOT NULL ORDER BY id", (ST_ENDED,))
        done = {"applied": 0, "failed": 0}
        for lot in cur.fetchall():
            cur.execute("SELECT (SELECT 1 FROM users WHERE id = ?) AS u, "
                        "(SELECT 1 FROM registrations WHERE user_id = ?) AS reg, "
                        "(SELECT 1 FROM registrations WHERE league_id = ? AND club_name = ?) AS taken, "
                        "(SELECT COUNT(*) FROM registrations WHERE league_id = ?) AS cnt, "
                        "(SELECT max_players FROM leagues WHERE id = ?) AS mx",
                        (lot["winner_user_id"], lot["winner_user_id"], lot["league_id"], lot["club_name"],
                         lot["league_id"], lot["league_id"]))
            c = cur.fetchone()
            if c["u"] and not c["reg"] and not c["taken"] and c["mx"] and c["cnt"] < c["mx"]:
                cur.execute("INSERT INTO registrations (user_id, league_id, club_name) VALUES (?, ?, ?)",
                            (lot["winner_user_id"], lot["league_id"], lot["club_name"]))
                status = ST_APPLIED
            else:
                if c["u"]:
                    wallet_change(cur, lot["winner_user_id"], lot["current_bid"], TX_REFUND, lot["leader_bid_id"])
                status = ST_FAILED
            cur.execute("UPDATE auction_lots SET status = ?, applied_at = CURRENT_TIMESTAMP, apply_notified = 0 "
                        "WHERE id = ?", (status, lot["id"]))
            done[status] += 1
        return True, done

    r = _tx(run)[1]
    if r["applied"] or r["failed"]:
        logger.info("AUKSION: yangi mavsum — %s g'olib klubiga yozildi, %s yozilmadi (pul qaytdi)", r["applied"], r["failed"])
    return r
