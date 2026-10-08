"""
pt_delete.py — SHAXSIY turnirni o'chirish (2026-10-07).

Admin so'rovi: muddati o'tgan yoki xato ochilgan turnirlarni o'chirish tugmasi.
Ruxsat: FAQAT tashkilotchi (turnir egasi) yoki bosh admin (qoida #34) — turnir adminlari emas.
Istalgan holatda o'chiriladi (to'lov kutilayotgan, yig'ilayotgan, davom etayotgan, yakunlangan);
to'langan summa qaytarilmaydi — frontend ogohlantiradi. Barcha bog'liq yozuvlar BITTA
tranzaksiyada o'chadi (FK tartibi: xabarlar -> o'yinlar -> a'zolar/adminlar/chek -> turnir).
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


def pt_delete_tournament(tid: int, user_id: int, is_super: bool = False) -> tuple[bool, str | dict]:
    """Sabablar: not_found, not_owner. Qaytaradi (ok): {name, members: [{telegram_id, language}]} (xabar uchun)."""
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id, name, owner_user_id, status FROM pt_tournaments WHERE id = ?", (tid,))
        t = cursor.fetchone()
        why = "not_found" if not t else (None if is_super or t["owner_user_id"] == user_id else "not_owner")
        if why:
            cursor.execute("ROLLBACK")
            return False, why
        cursor.execute("SELECT m.telegram_id, u.language FROM pt_members m JOIN users u ON u.id = m.user_id "
                       "WHERE m.tournament_id = ? AND m.user_id != ?", (tid, t["owner_user_id"]))
        members = [dict(r) for r in cursor.fetchall()]
        cursor.execute("DELETE FROM pt_messages WHERE match_id IN (SELECT id FROM pt_matches WHERE tournament_id = ?)",
                       (tid,))
        # 2026-10-08: ishtirokchi <-> tashkilotchi chati
        cursor.execute("DELETE FROM pt_support_messages WHERE thread_id IN "
                       "(SELECT id FROM pt_support_threads WHERE tournament_id = ?)", (tid,))
        cursor.execute("DELETE FROM pt_support_threads WHERE tournament_id = ?", (tid,))
        for table in ("pt_matches", "pt_members", "pt_admins", "pt_receipts"):
            cursor.execute(f"DELETE FROM {table} WHERE tournament_id = ?", (tid,))
        cursor.execute("DELETE FROM pt_tournaments WHERE id = ?", (tid,))
        cursor.execute("COMMIT")
    except Exception:
        try:
            cursor.execute("ROLLBACK")
        except Exception:
            logger.exception("pt_delete_tournament: ROLLBACK xatosi")
        raise
    finally:
        conn.close()
    logger.info("PT #%s '%s' o'chirildi (holat %s, user %s, super=%s)", tid, t["name"], t["status"], user_id, is_super)
    return True, {"name": t["name"], "status": t["status"], "members": members}
