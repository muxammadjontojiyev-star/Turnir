"""
shop_core.py — DO'KON: eF Token paketlari va sotib olish (karta + chek) (2026-10-30).

Egasi qarorlari: valyuta dizayni — "eF Token" (olti burchakli neon token); to'lov — karta + chek
(shaxsiy turnirlardagi kabi), bosh admin tasdiqlagach balansga tushadi; paket va narxlar —
bosh admin paneldan.

Oqim:
  1) Ishtirokchi faol paketni tanlaydi, kartaga o'tkazadi, chek rasmini yuboradi ->
     shop_orders (status 'review', coins/price_uzs — paketdan nusxa). Bir kishida ko'pi bilan
     SHOP_PENDING_MAX ta tekshiruvdagi buyurtma (spam himoyasi).
  2) Bosh admin: tasdiqlash -> 'approved' + wallet_change(+coins); rad etish -> 'rejected' (sabab).
     Ikkalasi ham shartli UPDATE (status = 'review') — takror bosish ikki marta pul bermaydi (qoida #38).
Chek rasmi — pt_payment.decode_receipt (imzo tekshiruvi, 2.5 MB), faqat bosh admin ko'radi.
"""

import logging

from config import SHOP_COINS_MAX, SHOP_ORDERS_HISTORY, SHOP_PACKAGES_MAX, SHOP_PENDING_MAX, SHOP_PRICE_MAX_UZS
from models import get_connection
from wallet import TX_PURCHASE, get_balance, wallet_change

logger = logging.getLogger(__name__)

ST_REVIEW, ST_APPROVED, ST_REJECTED = "review", "approved", "rejected"
_PKG_COLS = "id, coins, price_uzs, active"
_ORDER_COLS = ("o.id, o.user_id, o.package_id, o.coins, o.price_uzs, o.status, o.reject_reason, o.created_at, o.reviewed_at, "
               "length(o.receipt) > 0 AS has_receipt")
# 2026-10-30: chekni ilovada yubora olmagan xaridor — buyurtma chek RASMISIZ ochiladi (receipt = b"", mime = ""),
# chekni bosh adminga Telegram'da yuboradi; admin to'lovni tekshirib tasdiqlaydi (tushunmovchilik bo'lmasin).
NO_RECEIPT = (b"", "")


def _tx(fn):
    """BEGIN IMMEDIATE ichida fn(cursor) -> (ok, natija); ok bo'lmasa ROLLBACK."""
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        ok, result = fn(cursor)
        cursor.execute("COMMIT" if ok else "ROLLBACK")
        return ok, result
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("shop _tx: ROLLBACK xatosi")
        raise
    finally:
        conn.close()


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


# ---------------- Ishtirokchi ----------------

def shop_state(user_id: int) -> dict:
    """Do'kon sahifasi: balans, faol paketlar, oxirgi buyurtmalarim (chek rasmisiz)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {_PKG_COLS} FROM shop_packages WHERE active = 1 ORDER BY coins, id")
        packages = [dict(r) for r in cur.fetchall()]
        cur.execute(f"SELECT {_ORDER_COLS} FROM shop_orders o WHERE o.user_id = ? ORDER BY o.id DESC LIMIT ?",
                    (user_id, SHOP_ORDERS_HISTORY))
        orders = [dict(r) for r in cur.fetchall()]
        from pt_rounds import utc_to_local_text           # Toshkent vaqti (DB — UTC)
        for o in orders:
            o["created_local"] = utc_to_local_text(o["created_at"])
        return {"balance": get_balance(cur, user_id), "packages": packages, "orders": orders,
                "pending_max": SHOP_PENDING_MAX}
    finally:
        conn.close()


def shop_create_order(user_id: int, package_id, data: bytes, mime: str) -> tuple[bool, str | dict]:
    """Chek bilan buyurtma. Sabablar: package_not_found, too_many_pending."""
    pid = _int(package_id)

    def run(cur):
        cur.execute(f"SELECT {_PKG_COLS} FROM shop_packages WHERE id = ? AND active = 1", (pid,))
        pkg = cur.fetchone()
        if not pkg:
            return False, "package_not_found"
        cur.execute("SELECT COUNT(*) AS n FROM shop_orders WHERE user_id = ? AND status = ?", (user_id, ST_REVIEW))
        if cur.fetchone()["n"] >= SHOP_PENDING_MAX:
            return False, "too_many_pending"
        cur.execute("INSERT INTO shop_orders (user_id, package_id, coins, price_uzs, receipt, receipt_mime) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (user_id, pkg["id"], pkg["coins"], pkg["price_uzs"], data, mime))
        oid = cur.lastrowid
        cur.execute("SELECT nickname, username FROM users WHERE id = ?", (user_id,))
        u = cur.fetchone()
        return True, {"id": oid, "coins": pkg["coins"], "price_uzs": pkg["price_uzs"],
                      "nickname": u["nickname"] if u else "", "username": u["username"] if u else None}

    ok, r = _tx(run)
    if ok:
        logger.info("SHOP: buyurtma #%s (user %s, %s eF)", r["id"], user_id, r["coins"])
    return ok, r


# ---------------- Bosh admin: buyurtmalar ----------------

def shop_list_review() -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {_ORDER_COLS}, u.nickname, u.username, u.telegram_id FROM shop_orders o "
                    "JOIN users u ON u.id = o.user_id WHERE o.status = ? ORDER BY o.id", (ST_REVIEW,))
        rows = [dict(r) for r in cur.fetchall()]
        from pt_rounds import utc_to_local_text
        for o in rows:
            o["created_local"] = utc_to_local_text(o["created_at"])
        return rows
    finally:
        conn.close()


def shop_get_receipt(order_id) -> tuple[bytes, str] | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT receipt, receipt_mime FROM shop_orders WHERE id = ?", (_int(order_id),)).fetchone()
        return (bytes(r["receipt"]), r["receipt_mime"]) if r and r["receipt"] else None
    finally:
        conn.close()


def shop_review_order(order_id, admin_tg: int, approve: bool, reason: str | None = None) -> tuple[bool, str | dict]:
    """review -> approved (+balans) | rejected. Sabablar: not_found, wrong_status."""
    oid = _int(order_id)

    def run(cur):
        cur.execute("SELECT o.id, o.user_id, o.coins, o.price_uzs, o.status, u.telegram_id, u.language "
                    "FROM shop_orders o JOIN users u ON u.id = o.user_id WHERE o.id = ?", (oid,))
        o = cur.fetchone()
        if not o:
            return False, "not_found"
        cur.execute("UPDATE shop_orders SET status = ?, reject_reason = ?, reviewed_by = ?, "
                    "reviewed_at = CURRENT_TIMESTAMP WHERE id = ? AND status = ?",
                    (ST_APPROVED if approve else ST_REJECTED, None if approve else reason, admin_tg, oid, ST_REVIEW))
        if cur.rowcount == 0:
            return False, "wrong_status"
        info = dict(o)
        if approve:
            info["balance"] = wallet_change(cur, o["user_id"], o["coins"], TX_PURCHASE, oid)
        return True, info

    ok, r = _tx(run)
    if ok:
        logger.info("SHOP: buyurtma #%s %s (admin %s)", oid, "tasdiqlandi" if approve else "rad etildi", admin_tg)
    return ok, r


# ---------------- Bosh admin: paketlar ----------------

def shop_list_packages() -> list[dict]:
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(f"SELECT {_PKG_COLS} FROM shop_packages ORDER BY coins, id")]
    finally:
        conn.close()


def shop_save_package(package_id, coins, price_uzs, active=True) -> tuple[bool, str | dict]:
    """Yangi (package_id bo'sh) yoki tahrir. Sabablar: bad_coins, bad_price, not_found, too_many_packages."""
    coins, price, pid = _int(coins), _int(price_uzs), _int(package_id)
    if coins is None or not 0 < coins <= SHOP_COINS_MAX:
        return False, "bad_coins"
    if price is None or not 0 < price <= SHOP_PRICE_MAX_UZS:
        return False, "bad_price"
    act = 1 if active else 0

    def run(cur):
        if pid:
            cur.execute("UPDATE shop_packages SET coins = ?, price_uzs = ?, active = ?, "
                        "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (coins, price, act, pid))
            if cur.rowcount == 0:
                return False, "not_found"
            return True, {"id": pid}
        cur.execute("SELECT COUNT(*) AS n FROM shop_packages")
        if cur.fetchone()["n"] >= SHOP_PACKAGES_MAX:
            return False, "too_many_packages"
        cur.execute("INSERT INTO shop_packages (coins, price_uzs, active) VALUES (?, ?, ?)", (coins, price, act))
        return True, {"id": cur.lastrowid}

    return _tx(run)
