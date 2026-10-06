"""
pt_admins.py — SHAXSIY turnir adminlari (2026-10-03).

Admin qarori: tashkilotchi cheksiz admin tayinlaydi (Telegram ID yoki @username — odam botda
/start bosgan bo'lishi kerak). Admin huquqlari pt_core.is_manager orqali (a'zolar, boshlash,
muddat, natija tuzatish, pley-off). Admin qo'shish/olib tashlash, sig'im va to'lov — FAQAT tashkilotchi.
"""

import logging

from pt_members import _find_user, _tx

logger = logging.getLogger(__name__)


def _owned(cursor, tid: int, owner_id: int):
    cursor.execute("SELECT id, name, owner_user_id, status FROM pt_tournaments WHERE id = ?", (tid,))
    t = cursor.fetchone()
    if not t:
        return None, "not_found"
    if t["owner_user_id"] != owner_id:
        return None, "not_owner"                     # admin boshqa admin tayinlay olmaydi
    if t["status"] in ("finished", "cancelled"):
        return None, "finished"
    return dict(t), "ok"


def pt_add_admin(tid: int, owner_id: int, query: str) -> tuple[bool, str | dict]:
    """Sabablar: not_found, not_owner, finished, user_not_found, is_owner, already_admin."""
    def run(cursor):
        t, why = _owned(cursor, tid, owner_id)
        if t is None:
            return False, why
        u = _find_user(cursor, query)
        if not u:
            return False, "user_not_found"
        if u["id"] == t["owner_user_id"]:
            return False, "is_owner"
        cursor.execute("INSERT OR IGNORE INTO pt_admins (tournament_id, user_id, telegram_id) VALUES (?, ?, ?)",
                       (tid, u["id"], u["telegram_id"]))
        if cursor.rowcount != 1:
            return False, "already_admin"
        logger.info("PT #%s: admin qo'shildi user %s", tid, u["id"])
        return True, {"name": t["name"], "user_id": u["id"], "telegram_id": u["telegram_id"],
                      "language": u["language"]}
    return _tx(run)


def pt_remove_admin(tid: int, owner_id: int, admin_user_id: int) -> tuple[bool, str | dict]:
    """Sabablar: not_found, not_owner, finished, admin_not_found."""
    def run(cursor):
        t, why = _owned(cursor, tid, owner_id)
        if t is None:
            return False, why
        cursor.execute("SELECT telegram_id FROM pt_admins WHERE tournament_id = ? AND user_id = ?",
                       (tid, admin_user_id))
        a = cursor.fetchone()
        if not a:
            return False, "admin_not_found"
        cursor.execute("DELETE FROM pt_admins WHERE tournament_id = ? AND user_id = ?", (tid, admin_user_id))
        logger.info("PT #%s: admin olib tashlandi user %s", tid, admin_user_id)
        return True, {"name": t["name"]}
    return _tx(run)
