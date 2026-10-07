"""
pt_admin_all.py — bosh admin uchun BARCHA shaxsiy turnirlar ro'yxati (2026-10-07).

Admin so'rovi: bosh admin ochilgan shaxsiy turnirlarni ko'rsin va tushunmayotgan tashkilotchilarga
yordam berish uchun sozlamalarini o'zgartira olsin. Ro'yxat — shu modul; turnirni ochish va sozlash
oddiy endpointlar orqali (pt_core.is_manager / can_own bosh adminni tashkilotchi deb hisoblaydi).
Faqat o'qish; qidiruv — turnir nomi, tashkilotchi nickname/@username yoki #id bo'yicha.
"""

from models import get_connection

PT_ADMIN_LIST_LIMIT = 300
_STATUSES = ("awaiting_payment", "payment_review", "recruiting", "running", "finished", "rejected", "cancelled")


def pt_list_all(query: str = "", status: str = "", limit: int = PT_ADMIN_LIST_LIMIT) -> dict:
    """{"tournaments": [...], "counts": {holat: soni}, "total": N} — yangisi birinchi."""
    q = (query or "").strip().lstrip("@#").lower()
    where, args = [], []
    if status in _STATUSES:
        where.append("t.status = ?")
        args.append(status)
    if q:
        where.append("(LOWER(t.name) LIKE ? OR LOWER(COALESCE(u.username, '')) LIKE ? "
                     "OR LOWER(COALESCE(u.nickname, '')) LIKE ? OR CAST(t.id AS TEXT) = ?)")
        args += [f"%{q}%", f"%{q}%", f"%{q}%", q]
    sql_where = ("WHERE " + " AND ".join(where)) if where else ""
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""SELECT t.id, t.name, t.status, t.format, t.league_name, t.legs, t.max_players, t.paid_via,
                       t.price_uzs, t.created_at, t.owner_user_id, u.nickname AS owner_nickname,
                       u.username AS owner_username, u.telegram_id AS owner_telegram_id,
                       (SELECT COUNT(*) FROM pt_members m WHERE m.tournament_id = t.id
                          AND m.status = 'approved') AS members_count
                FROM pt_tournaments t JOIN users u ON u.id = t.owner_user_id
                {sql_where} ORDER BY t.id DESC LIMIT ?""", (*args, int(limit))).fetchall()
        counts = {r["status"]: r["c"] for r in conn.execute(
            "SELECT status, COUNT(*) AS c FROM pt_tournaments GROUP BY status").fetchall()}
    finally:
        conn.close()
    return {"tournaments": [dict(r) for r in rows], "counts": counts, "total": sum(counts.values())}
