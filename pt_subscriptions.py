"""
pt_subscriptions.py — SHAXSIY turnir obunalari (2026-10-03).

Admin qarori: haftalik / oylik / yillik obuna; obuna davrida turnir TO'LOVSIZ yaratiladi
(darhol 'recruiting'), lekin bir vaqtda ko'pi bilan SUB_ACTIVE_LIMIT ta faol (yig'ilayotgan
yoki davom etayotgan) obuna-turnir. Obuna tugasa ham boshlangan turnirlar oxirigacha davom etadi.
Bir martalik to'lov ham qoladi (narx sig'im pog'onasiga qarab — pt_pricing).

To'lov oqimi turnirniki bilan bir xil: awaiting_payment -> (chek) payment_review ->
(bosh admin) active | rejected (chekni qayta yuborish mumkin).
Yangilash: yangi obuna joriy faol obuna TUGAYDIGAN paytdan boshlanadi (kunlar yo'qolmaydi).
Vaqtlar UTC 'YYYY-MM-DD HH:MM:SS' (datetime('now') bilan solishtiriladi).
"""

import logging
from datetime import datetime, timedelta, timezone

from config import TOURNAMENT_TIMEZONE_OFFSET
from models import get_connection
from pt_members import _tx
from pt_pricing import SUB_ACTIVE_LIMIT, plan_info, price_for_size

logger = logging.getLogger(__name__)

_FMT = "%Y-%m-%d %H:%M:%S"
_LOCAL = timezone(timedelta(hours=TOURNAMENT_TIMEZONE_OFFSET))
_PENDING = ("awaiting_payment", "payment_review", "rejected")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def local_date(utc_str: str | None) -> str | None:
    """UTC -> 'DD.MM.YYYY HH:MM' (Toshkent) — yillik obunada yil ham kerak."""
    if not utc_str:
        return None
    dt = datetime.strptime(utc_str, _FMT).replace(tzinfo=timezone.utc)
    return dt.astimezone(_LOCAL).strftime("%d.%m.%Y %H:%M")


def _active(cursor, user_id: int):
    """Hozir amal qilayotgan obuna (eng uzog'i) yoki None."""
    cursor.execute("SELECT id, plan, starts_at, expires_at FROM pt_subscriptions WHERE user_id = ? "
                   "AND status = 'active' AND expires_at > ? ORDER BY expires_at DESC LIMIT 1",
                   (user_id, _now().strftime(_FMT)))
    r = cursor.fetchone()
    return dict(r) if r else None


def _active_sub_tournaments(cursor, user_id: int) -> int:
    cursor.execute("SELECT COUNT(*) AS c FROM pt_tournaments WHERE owner_user_id = ? "
                   "AND paid_via = 'subscription' AND status IN ('recruiting', 'running')", (user_id,))
    return cursor.fetchone()["c"]


def pt_sub_status(user_id: int) -> dict:
    """{active: {plan, expires_local} | None, pending: buyurtma | None, active_tournaments, limit}"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        a = _active(cursor, user_id)
        cursor.execute("SELECT id, plan, price_uzs, status, reject_reason FROM pt_subscriptions "
                       f"WHERE user_id = ? AND status IN ({','.join('?' * len(_PENDING))}) "
                       "ORDER BY id DESC LIMIT 1", (user_id, *_PENDING))
        p = cursor.fetchone()
        used = _active_sub_tournaments(cursor, user_id)
    finally:
        conn.close()
    return {"active": {"plan": a["plan"], "expires_local": local_date(a["expires_at"])} if a else None,
            "pending": dict(p) if p else None, "active_tournaments": used, "limit": SUB_ACTIVE_LIMIT}


def pt_order_subscription(user: dict, plan: str) -> tuple[bool, str | dict]:
    """Obuna buyurtmasi. Sabablar: plan_unavailable, pending_exists."""
    info = plan_info(plan)
    if not info:
        return False, "plan_unavailable"

    def run(cursor):
        cursor.execute(f"SELECT 1 FROM pt_subscriptions WHERE user_id = ? AND status IN "
                       f"({','.join('?' * len(_PENDING))})", (user["id"], *_PENDING))
        if cursor.fetchone():
            return False, "pending_exists"            # bitta ochiq buyurtma (qoida #39)
        cursor.execute("INSERT INTO pt_subscriptions (user_id, telegram_id, plan, price_uzs) VALUES (?, ?, ?, ?)",
                       (user["id"], user["telegram_id"], plan, info[1]))
        return True, {"id": cursor.lastrowid, "plan": plan, "price_uzs": info[1], "days": info[0]}
    return _tx(run)


def pt_sub_cancel_order(sub_id: int, user_id: int) -> tuple[bool, str]:
    """To'lanmagan buyurtmani bekor qilish (boshqa tarif tanlash uchun). Sabab: not_found, wrong_status."""
    def run(cursor):
        cursor.execute("SELECT user_id, status FROM pt_subscriptions WHERE id = ?", (sub_id,))
        r = cursor.fetchone()
        if not r or r["user_id"] != user_id:
            return False, "not_found"
        if r["status"] not in ("awaiting_payment", "rejected"):
            return False, "wrong_status"
        cursor.execute("DELETE FROM pt_sub_receipts WHERE subscription_id = ?", (sub_id,))
        cursor.execute("DELETE FROM pt_subscriptions WHERE id = ?", (sub_id,))
        return True, "ok"
    return _tx(run)


def pt_sub_submit_receipt(sub_id: int, user_id: int, data: bytes, mime: str) -> tuple[bool, str | dict]:
    """Chek: awaiting_payment|rejected -> payment_review. Sabablar: not_found, wrong_status."""
    def run(cursor):
        cursor.execute("SELECT s.id, s.user_id, s.plan, s.price_uzs, s.status, u.nickname, u.username "
                       "FROM pt_subscriptions s JOIN users u ON u.id = s.user_id WHERE s.id = ?", (sub_id,))
        s = cursor.fetchone()
        if not s or s["user_id"] != user_id:
            return False, "not_found"
        if s["status"] not in ("awaiting_payment", "rejected"):
            return False, "wrong_status"
        cursor.execute("INSERT INTO pt_sub_receipts (subscription_id, mime, data) VALUES (?, ?, ?) "
                       "ON CONFLICT(subscription_id) DO UPDATE SET mime = excluded.mime, data = excluded.data, "
                       "created_at = CURRENT_TIMESTAMP", (sub_id, mime, data))
        cursor.execute("UPDATE pt_subscriptions SET status = 'payment_review', receipt_at = CURRENT_TIMESTAMP, "
                       "reject_reason = NULL WHERE id = ?", (sub_id,))
        return True, {"id": sub_id, "plan": s["plan"], "price_uzs": s["price_uzs"],
                      "owner_nickname": s["nickname"], "owner_username": s["username"]}
    return _tx(run)


def pt_sub_list_payments() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT s.id, s.plan, s.price_uzs, s.receipt_at, u.nickname AS owner_nickname, "
            "u.username AS owner_username FROM pt_subscriptions s JOIN users u ON u.id = s.user_id "
            "WHERE s.status = 'payment_review' ORDER BY s.receipt_at, s.id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def pt_sub_get_receipt(sub_id: int) -> tuple[bytes, str] | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT mime, data FROM pt_sub_receipts WHERE subscription_id = ?", (sub_id,)).fetchone()
        return (bytes(r["data"]), r["mime"]) if r else None
    finally:
        conn.close()


def _owner_info(cursor, sub_id: int) -> dict:
    cursor.execute("SELECT s.telegram_id, s.plan, s.expires_at, u.language FROM pt_subscriptions s "
                   "JOIN users u ON u.id = s.user_id WHERE s.id = ?", (sub_id,))
    return dict(cursor.fetchone())


def pt_sub_approve(sub_id: int, admin_tg: int) -> tuple[bool, str | dict]:
    """payment_review -> active; muddat joriy faol obuna oxiridan (yoki hozirdan) boshlanadi."""
    def run(cursor):
        cursor.execute("SELECT user_id, plan, status FROM pt_subscriptions WHERE id = ?", (sub_id,))
        s = cursor.fetchone()
        if not s:
            return False, "not_found"
        if s["status"] != "payment_review":
            return False, "wrong_status"
        days = {"week": 7, "month": 30, "year": 365}[s["plan"]]
        cur = _active(cursor, s["user_id"])
        start = max(_now(), datetime.strptime(cur["expires_at"], _FMT).replace(tzinfo=timezone.utc)) if cur else _now()
        end = start + timedelta(days=days)
        cursor.execute("UPDATE pt_subscriptions SET status = 'active', reviewed_by = ?, starts_at = ?, expires_at = ? "
                       "WHERE id = ? AND status = 'payment_review'",
                       (admin_tg, start.strftime(_FMT), end.strftime(_FMT), sub_id))
        info = _owner_info(cursor, sub_id)
        info["expires_local"] = local_date(info["expires_at"])
        return True, info
    return _tx(run)


def pt_sub_reject(sub_id: int, admin_tg: int, reason: str | None) -> tuple[bool, str | dict]:
    from pt_payment import clean_reject_reason
    reason = clean_reject_reason(reason)

    def run(cursor):
        cursor.execute("UPDATE pt_subscriptions SET status = 'rejected', reviewed_by = ?, reject_reason = ? "
                       "WHERE id = ? AND status = 'payment_review'", (admin_tg, reason, sub_id))
        if cursor.rowcount != 1:
            cursor.execute("SELECT 1 FROM pt_subscriptions WHERE id = ?", (sub_id,))
            return False, "wrong_status" if cursor.fetchone() else "not_found"
        info = _owner_info(cursor, sub_id)
        info["reason"] = reason
        return True, info
    return _tx(run)


def pt_create_with_mode(user: dict, name: str, max_players: int, pay_mode: str, fmt: str = "classic",
                        league: str | None = None, legs: int = 1) -> tuple[bool, str | dict]:
    """
    Turnir yaratish to'lov turi bilan (biznes-mantiq shu yerda — endpoint faqat chaqiradi, qoida #27):
      pay_mode='subscription' — faol obuna kerak (no_subscription), limit (sub_limit);
      pay_mode='one_time'     — narx sig'im pog'onasidan (price_not_set — bu pog'ona yopiq).
    2026-10-07: fmt/league/legs (pt_core.check_format: bad_format, bad_league, bad_legs, bad_size).
    """
    from pt_core import check_format, pt_create_tournament
    why = check_format(fmt, league, legs, max_players)
    if why:
        return False, why
    extra = {"fmt": fmt, "league": league, "legs": legs}
    if pay_mode == "subscription":
        conn = get_connection()
        cursor = conn.cursor()
        try:
            if not _active(cursor, user["id"]):
                return False, "no_subscription"
            if _active_sub_tournaments(cursor, user["id"]) >= SUB_ACTIVE_LIMIT:
                return False, "sub_limit"
        finally:
            conn.close()
        return pt_create_tournament(user, name, 0, max_players, via_subscription=True, **extra)
    from pt_pricing import price_for_tournament        # liga: +3000 har qo'shimcha liga uchun
    return pt_create_tournament(user, name, price_for_tournament(fmt, max_players, league), max_players, **extra)
