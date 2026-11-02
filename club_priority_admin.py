"""
club_priority_admin.py — KLUB NAVBATI: bosh admin tekshiruvi va tuzatishi (2026-11-02).

Egasi: «navbatingiz oxirida (tashlab ketgan)» yozuvi yangilarga ham chiqyapti. Kod tekshirildi — o'tgan
mavsum bo'yicha YOZUVI YO'Q odam «yangi» bo'ladi (club_priority.club_priority_for). Demak bu yozuv
chiqqanlarda club_reliability'da 'abandoned' belgisi bor (masalan, kanalni tark etgani uchun klubi
boshqaga o'tgan, admin akkauntni ko'chirgan yoki o'yinlari bor holda chiqarilgan) va ular qaytib kirgan.
Bosh admin endi: ro'yxatni ko'radi (sababi bilan), istalgan odamni tekshiradi va belgini olib tashlaydi.
"""

import logging

from club_priority import ST_ABANDONED, club_priority_for
from models import get_connection

logger = logging.getLogger(__name__)
REASONS = ("club_taken", "admin", "removed")


def _prev_season(cur) -> int:
    r = cur.execute("SELECT current_season FROM season_state WHERE id = 1").fetchone()
    return (r["current_season"] if r else 1) - 1


def abandoned_list() -> dict:
    """O'tgan mavsumda «tashlab ketgan» deb belgilanganlar (sabab, sana, hozirgi nik)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        prev = _prev_season(cur)
        cols = {r["name"] for r in cur.execute("PRAGMA table_info(club_reliability)")}
        reason = "c.reason" if "reason" in cols else "NULL"
        rows = cur.execute(
            f"SELECT c.telegram_id, {reason} AS reason, c.created_at, "
            "(SELECT nickname FROM users u WHERE u.telegram_id = c.telegram_id ORDER BY u.id DESC LIMIT 1) AS nickname, "
            "(SELECT username FROM users u WHERE u.telegram_id = c.telegram_id ORDER BY u.id DESC LIMIT 1) AS username "
            "FROM club_reliability c WHERE c.season_number = ? AND c.status = ? ORDER BY c.created_at DESC",
            (prev, ST_ABANDONED)).fetchall()
        return {"season": prev, "list": [dict(r) for r in rows]}
    finally:
        conn.close()


def find_user(query: str) -> dict | None:
    """@username yoki Telegram ID bo'yicha: {telegram_id, nickname, username, record, priority}."""
    q = (query or "").strip().lstrip("@")
    if not q:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        if q.isdigit():
            u = cur.execute("SELECT telegram_id, nickname, username FROM users WHERE telegram_id = ? "
                            "ORDER BY id DESC LIMIT 1", (int(q),)).fetchone()
            tg = int(q)
        else:
            u = cur.execute("SELECT telegram_id, nickname, username FROM users WHERE LOWER(username) = LOWER(?) "
                            "ORDER BY id DESC LIMIT 1", (q,)).fetchone()
            tg = u["telegram_id"] if u else None
        if tg is None:
            return None
        rec = cur.execute("SELECT status, created_at FROM club_reliability WHERE telegram_id = ? AND season_number = ?",
                          (tg, _prev_season(cur))).fetchone()
    finally:
        conn.close()
    return {"telegram_id": tg, "nickname": u["nickname"] if u else None, "username": u["username"] if u else None,
            "record": dict(rec) if rec else None, "priority": club_priority_for(tg)}


def clear_abandoned(telegram_id: int) -> bool:
    """O'tgan mavsum «tashlab ketgan» belgisini olib tashlaydi — odam «yangi» navbatiga o'tadi."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM club_reliability WHERE telegram_id = ? AND season_number = ? AND status = ?",
                    (telegram_id, _prev_season(cur), ST_ABANDONED))
        n = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    if n:
        logger.info("Klub navbati: bosh admin tg %s ning «tashlab ketgan» belgisini olib tashladi", telegram_id)
    return bool(n)
