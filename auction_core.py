"""
auction_core.py — DO'KON → AUKSION: liga klubi uchun muddatli kim oshdi savdosi (2026-10-30).

Egasi qarorlari:
  - bosh admin klubni (liga + klub) sotuvga qo'yadi: boshlang'ich narx, eng kam qadam, muddat;
  - g'olib KEYINGI liga mavsumida shu klubga AVTOMATIK yoziladi (bir mavsumlik joy) —
    mavsum yangilanishida (season_reset dan keyin, auction_admin.auction_apply_reservations);
  - taklif summasi darhol MUZLATILADI (balansdan yechiladi); kimdir oshirsa — avvalgisiga darhol qaytadi;
  - muddat tugashiga AUCTION_SNIPE_MINUTES qolganda taklif tushsa — savdo shuncha daqiqaga uzayadi.
Qo'shimcha qoida (registrations.user_id UNIQUE — bir kishi bir mavsumda bitta klub):
  bir kishi bir vaqtda faqat BITTA savdoda yetakchi bo'la oladi va yutib, hali qo'llanmagan klubi
  bo'lsa yangi taklif qo'ya olmaydi (leading_other / already_won).

Holatlar: active -> ended (g'olib bilan yoki takliflarsiz) -> applied | failed; active -> cancelled.
Muddat o'tgan lotlar har o'qishda (lazy) va scheduler'da yopiladi (auction_close_due).
Har o'zgartirish BEGIN IMMEDIATE ichida (qoida #38); pul — faqat wallet.wallet_change orqali.
"""

import logging

from config import AUCTION_ENDED_SHOWN, AUCTION_PRICE_MAX, AUCTION_SNIPE_MINUTES
from models import get_connection
from shop_core import _int, _tx
from wallet import get_balance, wallet_change

logger = logging.getLogger(__name__)

ST_ACTIVE, ST_ENDED, ST_CANCELLED, ST_APPLIED, ST_FAILED = "active", "ended", "cancelled", "applied", "failed"
TX_BID, TX_REFUND = "auction_bid", "auction_refund"
_LOT_COLS = ("l.id, l.league_id, lg.name AS league_name, l.club_name, l.start_price, l.min_step, l.current_bid, "
             "l.leader_user_id, l.winner_user_id, l.bids_count, l.status, l.ends_at, l.ended_at, "
             "u.nickname AS leader_nickname, u.username AS leader_username")
_LOT_FROM = "FROM auction_lots l JOIN leagues lg ON lg.id = l.league_id LEFT JOIN users u ON u.id = l.leader_user_id "


def init_auction_tables(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auction_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            club_name TEXT NOT NULL,
            start_price INTEGER NOT NULL,
            min_step INTEGER NOT NULL,
            current_bid INTEGER,
            leader_user_id INTEGER,
            leader_bid_id INTEGER,
            winner_user_id INTEGER,
            bids_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            ends_at TIMESTAMP NOT NULL,
            ended_at TIMESTAMP,
            applied_at TIMESTAMP,
            end_notified INTEGER NOT NULL DEFAULT 0,
            apply_notified INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_auction_lots_status ON auction_lots(status, ends_at)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS auction_bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lot_id) REFERENCES auction_lots(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_auction_bids_lot ON auction_bids(lot_id, id)")


def auction_close_due(cur) -> int:
    """Muddati o'tgan faol lotlarni yopadi (ochiq tranzaksiya ichida). G'olib — yetakchi (pul allaqachon muzlatilgan)."""
    cur.execute("UPDATE auction_lots SET status = ?, winner_user_id = leader_user_id, ended_at = CURRENT_TIMESTAMP, "
                "end_notified = 0 WHERE status = ? AND ends_at <= CURRENT_TIMESTAMP", (ST_ENDED, ST_ACTIVE))
    return cur.rowcount


def min_next_bid(lot) -> int:
    return lot["start_price"] if lot["current_bid"] is None else lot["current_bid"] + lot["min_step"]


def _blocking_reason(cur, user_id: int, lot_id: int) -> str | None:
    """Bir kishi — bitta klub: boshqa savdoda yetakchi yoki yutgan (hali qo'llanmagan) klubi bormi."""
    cur.execute("SELECT 1 FROM auction_lots WHERE status = ? AND leader_user_id = ? AND id != ?",
                (ST_ACTIVE, user_id, lot_id))
    if cur.fetchone():
        return "leading_other"
    cur.execute("SELECT 1 FROM auction_lots WHERE status = ? AND winner_user_id = ?", (ST_ENDED, user_id))
    return "already_won" if cur.fetchone() else None


def auction_state(user_id: int) -> dict:
    """Auksion tabi: faol lotlar (min keyingi taklif bilan), oxirgi yakunlanganlar, balans."""
    _tx(lambda cur: (True, auction_close_due(cur)))
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {_LOT_COLS}, CAST((julianday(l.ends_at) - julianday('now')) * 86400 AS INTEGER) AS left_s "
                    f"{_LOT_FROM}WHERE l.status = ? ORDER BY l.ends_at, l.id", (ST_ACTIVE,))
        active = []
        for r in cur.fetchall():
            d = dict(r)
            d["min_bid"] = min_next_bid(d)
            d["is_leader"] = d["leader_user_id"] == user_id
            active.append(d)
        cur.execute(f"SELECT {_LOT_COLS} {_LOT_FROM}WHERE l.status IN (?, ?, ?) AND l.ended_at IS NOT NULL "
                    "ORDER BY l.ended_at DESC, l.id DESC LIMIT ?", (ST_ENDED, ST_APPLIED, ST_FAILED, AUCTION_ENDED_SHOWN))
        ended = [{**dict(r), "is_winner": r["winner_user_id"] == user_id and r["winner_user_id"] is not None}
                 for r in cur.fetchall()]
        return {"balance": get_balance(cur, user_id), "lots": active, "ended": ended,
                "block": _blocking_reason(cur, user_id, 0), "snipe_minutes": AUCTION_SNIPE_MINUTES}
    finally:
        conn.close()


def auction_bid(user_id: int, lot_id, amount) -> tuple[bool, str | dict]:
    """
    Taklif. Sabablar: lot_not_found, ended, already_leader, leading_other, already_won,
    bid_too_low (min — natijada), bad_amount, insufficient.
    """
    lid, amt = _int(lot_id), _int(amount)

    def run(cur):
        auction_close_due(cur)
        cur.execute(f"SELECT {_LOT_COLS}, l.leader_bid_id, "
                    "CAST((julianday(l.ends_at) - julianday('now')) * 86400 AS INTEGER) AS left_s "
                    f"{_LOT_FROM}WHERE l.id = ?", (lid,))
        lot = cur.fetchone()
        if not lot:
            return False, "lot_not_found"
        if lot["status"] != ST_ACTIVE:
            return False, "ended"
        if lot["leader_user_id"] == user_id:
            return False, "already_leader"
        block = _blocking_reason(cur, user_id, lid)
        if block:
            return False, block
        if amt is None or amt <= 0 or amt > AUCTION_PRICE_MAX:
            return False, "bad_amount"
        if amt < min_next_bid(lot):
            return False, "bid_too_low"
        cur.execute("INSERT INTO auction_bids (lot_id, user_id, amount) VALUES (?, ?, ?)", (lid, user_id, amt))
        bid_id = cur.lastrowid
        try:
            balance = wallet_change(cur, user_id, -amt, TX_BID, bid_id)        # muzlatish
        except ValueError:
            return False, "insufficient"
        prev = None
        if lot["leader_user_id"]:
            wallet_change(cur, lot["leader_user_id"], lot["current_bid"], TX_REFUND, lot["leader_bid_id"])
            cur.execute("SELECT telegram_id, language FROM users WHERE id = ?", (lot["leader_user_id"],))
            row = cur.fetchone()
            prev = {**dict(row), "amount": lot["current_bid"]} if row else None
        extended = lot["left_s"] is not None and lot["left_s"] < AUCTION_SNIPE_MINUTES * 60
        cur.execute("UPDATE auction_lots SET current_bid = ?, leader_user_id = ?, leader_bid_id = ?, "
                    "bids_count = bids_count + 1" + (", ends_at = datetime('now', ?)" if extended else "") + " WHERE id = ?",
                    (amt, user_id, bid_id, f"+{AUCTION_SNIPE_MINUTES} minutes", lid) if extended
                    else (amt, user_id, bid_id, lid))
        return True, {"lot_id": lid, "amount": amt, "balance": balance, "extended": extended,
                      "club_name": lot["club_name"], "league_name": lot["league_name"], "prev": prev,
                      # 2026-10-31: oshirilgan ishtirokchi xabari uchun — keyingi eng kam taklif va qolgan vaqt
                      "next_min": amt + lot["min_step"],
                      "left_s": AUCTION_SNIPE_MINUTES * 60 if extended else max(0, lot["left_s"] or 0)}

    ok, r = _tx(run)
    if ok:
        logger.info("AUKSION #%s: taklif %s eF (user %s)%s", lid, amt, user_id, " — uzaytirildi" if r["extended"] else "")
    return ok, r
