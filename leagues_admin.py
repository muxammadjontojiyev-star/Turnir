"""
leagues_admin.py — BOSH ADMIN: LIGALARNI YOQISH / O'CHIRISH (2026-11-02).

Egasi so'rovi: yangi kelganlarga joy yetmay qolsa, ligalarni (masalan 2-ligalarni) o'zi yoqib, kerak
bo'lmaganda o'chirib qo'ya olsin. O'chirilgan liga botda ko'rinmaydi, ma'lumoti bazada qoladi
(leagues.is_active — leagues_region.py). Admin bir marta bosgach liga leagues.admin_set = 1 bo'ladi —
avtomatik «bo'sh 2-ligani nofaol qilish» unga endi tegmaydi.

Himoya: ishtirokchisi bor ligani o'chirib bo'lmaydi (has_players) — aks holda o'yinchilar ko'rinmay qoladi.
"""

import logging

from models import get_connection

logger = logging.getLogger(__name__)


def leagues_all() -> list[dict]:
    """Admin ro'yxati: barcha ligalar (nofaollar ham), mintaqa va tartib bo'yicha, o'yinchilar soni bilan."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT l.id, l.name, l.region, l.max_players, COALESCE(l.is_active, 1) AS is_active, "
            "(SELECT COUNT(*) FROM registrations r WHERE r.league_id = l.id) AS players "
            "FROM leagues l ORDER BY CASE l.region WHEN 'eu' THEN 1 WHEN 'asia' THEN 2 ELSE 3 END, "
            "l.sort_order, l.id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def league_set_active(league_id: int, on: bool) -> tuple[bool, str | dict]:
    """Sabablar: not_found, has_players (o'chirishda)."""
    conn = get_connection()
    try:
        r = conn.execute("SELECT name, (SELECT COUNT(*) FROM registrations WHERE league_id = ?) AS n "
                         "FROM leagues WHERE id = ?", (league_id, league_id)).fetchone()
        if not r:
            return False, "not_found"
        if not on and r["n"]:
            return False, "has_players"
        conn.execute("UPDATE leagues SET is_active = ?, admin_set = 1 WHERE id = ?", (1 if on else 0, league_id))
        conn.commit()
    finally:
        conn.close()
    logger.info("LIGA: bosh admin %s ni %s", r["name"], "YOQDI" if on else "O'CHIRDI")
    return True, {"id": league_id, "is_active": bool(on)}
