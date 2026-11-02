"""
club_priority_admin.py — KLUB NAVBATI: bosh admin tekshiruvi va tuzatishi (2026-11-02).

Egasi: «navbatingiz oxirida (tashlab ketgan)» yozuvi yangilarga ham chiqyapti. Kod tekshirildi — o'tgan
mavsum bo'yicha YOZUVI YO'Q odam «yangi» bo'ladi (club_priority.club_priority_for). Demak bu yozuv
chiqqanlarda club_reliability'da 'abandoned' belgisi bor (masalan, kanalni tark etgani uchun klubi
boshqaga o'tgan, admin akkauntni ko'chirgan yoki o'yinlari bor holda chiqarilgan) va ular qaytib kirgan.
Bosh admin: @username yoki ID bo'yicha tekshiradi — qachon chiqib ketgani, qaysi ligadagi qaysi klubni
tashlab ketgani, sababi (2026-11-02: to'liq ro'yxat ko'rsatilmaydi — egasi so'rovi) va belgini olib tashlaydi.
"""

import logging

from club_priority import ST_ABANDONED, club_priority_for
from models import get_connection

logger = logging.getLogger(__name__)
REASONS = ("club_taken", "admin", "removed")


def _prev_season(cur) -> int:
    r = cur.execute("SELECT current_season FROM season_state WHERE id = 1").fetchone()
    return (r["current_season"] if r else 1) - 1


def abandoned_count() -> dict:
    """O'tgan mavsumda «tashlab ketgan» deb belgilanganlar SONI (ro'yxat emas)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        prev = _prev_season(cur)
        n = cur.execute("SELECT COUNT(*) AS c FROM club_reliability WHERE season_number = ? AND status = ?",
                        (prev, ST_ABANDONED)).fetchone()["c"]
        return {"season": prev, "count": n}
    finally:
        conn.close()


def _record(cur, tg: int) -> dict | None:
    cols = {r["name"] for r in cur.execute("PRAGMA table_info(club_reliability)")}
    extra = ", ".join(c if c in cols else f"NULL AS {c}" for c in ("reason", "league_name", "club_name"))
    rec = cur.execute(f"SELECT status, created_at, {extra} FROM club_reliability "
                      "WHERE telegram_id = ? AND season_number = ?", (tg, _prev_season(cur))).fetchone()
    if not rec:
        return None
    from pt_rounds import utc_to_local_text
    d = dict(rec)
    d["left_at"] = utc_to_local_text(str(d["created_at"])[:19]) if d["created_at"] else None   # Toshkent
    return d


def find_user(query: str) -> dict | None:
    """@username yoki Telegram ID: {telegram_id, nickname, username, record{status, left_at, reason, league_name,
    club_name}, priority}."""
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
        rec = _record(cur, tg)
    finally:
        conn.close()
    return {"telegram_id": tg, "nickname": u["nickname"] if u else None, "username": u["username"] if u else None,
            "record": rec, "priority": club_priority_for(tg)}


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
