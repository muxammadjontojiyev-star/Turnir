"""
pt_capacity.py — SHAXSIY turnir sig'imini o'zgartirish (2026-10-03; 2026-10-07 pt_core'dan ajratildi
va formatga moslandi: liga — sig'im qat'iy (ligadagi klublar soni), ChL/YeL 8..36 juft, JCh 8..48).
"""

import logging

from models import get_connection
from pt_core import STATUS_AWAITING_PAYMENT, STATUS_RECRUITING, STATUS_REJECTED, _UNPAID, can_own

logger = logging.getLogger(__name__)


def pt_set_capacity(tid: int, owner_id: int, max_players: int) -> tuple[bool, str]:
    """
    Tashkilotchi sig'imni o'zgartiradi (qur'agacha). Qabul qilinganlardan kam bo'lolmaydi.
    Bir martalik to'lov (2026-10-03):
      - to'lovdan OLDIN (awaiting_payment/rejected) — narx yangi pog'onaga qayta hisoblanadi;
      - to'langan/tekshiruvda — faqat O'SHA narx pog'onasi ichida (tier_locked), aks holda
        8 kishilik narxni to'lab 128 kishilik turnir qilish mumkin bo'lardi.
    Obuna orqali yaratilgan turnirda — istalgan sig'im.
    Sabablar: bad_size, not_found, not_owner, already_started, below_members, tier_locked, price_not_set.
    """
    from pt_formats import valid_size_for
    from pt_pricing import price_for_tournament, tier_for_size
    if isinstance(max_players, bool) or not isinstance(max_players, int):
        return False, "bad_size"
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT owner_user_id, status, max_players, paid_via, format, league_name "
                       "FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        why = None
        new_price = None
        if not t:
            why = "not_found"
        elif not can_own(cursor, t["owner_user_id"], owner_id):   # 2026-10-07: bosh admin ham
            why = "not_owner"
        elif not valid_size_for(t["format"] or "classic", max_players, t["league_name"]):
            why = "bad_size"                    # liga: sig'im qat'iy; boshqalar — format qoidasi
        elif t["status"] not in (*_UNPAID, STATUS_RECRUITING, STATUS_REJECTED):
            why = "already_started"
        else:
            cursor.execute("SELECT COUNT(*) AS c FROM pt_members WHERE tournament_id = ? "
                           "AND status = 'approved'", (tid,))
            if cursor.fetchone()["c"] > max_players:
                why = "below_members"
            elif t["paid_via"] == "one_time":
                if t["status"] in (STATUS_AWAITING_PAYMENT, STATUS_REJECTED):
                    new_price = price_for_tournament(t["format"] or "classic", max_players, t["league_name"])
                    if new_price <= 0:
                        why = "price_not_set"
                elif tier_for_size(max_players) != tier_for_size(t["max_players"]):
                    why = "tier_locked"
        if why:
            cursor.execute("ROLLBACK")
            return False, why
        cursor.execute("UPDATE pt_tournaments SET max_players = ?, price_uzs = COALESCE(?, price_uzs), "
                       "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (max_players, new_price, tid))
        cursor.execute("COMMIT")
        return True, "ok"
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_set_capacity: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
