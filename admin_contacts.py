"""
admin_contacts.py — mas'ul adminlar bilan bog'lanish (2026-10-11).

Admin so'rovi: bosh admin rasmiy rejim/ligalarga mas'ul qilib tayinlagan
shaxslarning Telegram profiliga o'sha rejim ishtirokchilari oson o'tsin.

Kim ko'rsatiladi (bosh admin kelishuvi bilan):
  * liga  — FAQAT foydalanuvchi ro'yxatdan o'tgan ligaga biriktirilgan
            liga adminlari (admin_leagues + admins.scope='league');
  * cl / el / div / wc — shu rejim scope'idagi adminlar (list_admins).
Bosh adminlar (config.py) ro'yxatga kirmaydi — ular "tayinlangan" emas.

Faqat o'qiydi. Qaytaradi: [{"nickname", "username", "telegram_id"}, ...]
"""

from admin_roles import (SCOPE_AC, SCOPE_CL, SCOPE_DIVISION, SCOPE_EL, SCOPE_LEAGUE,
                         SCOPE_WC, list_admins)
from models import get_connection

# Frontend rejim nomi → admin scope (liga alohida — liga bo'yicha filtr)
CONTACT_MODE_SCOPES = {
    "cl": SCOPE_CL,
    "el": SCOPE_EL,
    "ac": SCOPE_AC,    # 2026-10-15
    "div": SCOPE_DIVISION,
    "wc": SCOPE_WC,
}
CONTACT_MODES = ("league",) + tuple(CONTACT_MODE_SCOPES)


def _league_admins(user_id: int) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT league_id FROM registrations WHERE user_id = ?", (user_id,))
        reg = cursor.fetchone()
        if reg is None:
            return []
        cursor.execute(
            """
            SELECT al.telegram_id, u.nickname, u.username
            FROM admin_leagues al
            JOIN admins a ON a.telegram_id = al.telegram_id AND a.scope = ?
            LEFT JOIN users u ON u.telegram_id = al.telegram_id
            WHERE al.league_id = ?
            ORDER BY al.added_at
            """,
            (SCOPE_LEAGUE, reg["league_id"]),
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_admin_contacts(mode: str, user_id: int) -> list[dict] | None:
    """mode noto'g'ri bo'lsa None; aks holda ro'yxat (bo'sh bo'lishi mumkin)."""
    if mode == "league":
        rows = _league_admins(user_id)
    elif mode in CONTACT_MODE_SCOPES:
        rows = list_admins(CONTACT_MODE_SCOPES[mode])
    else:
        return None
    return [{"nickname": r.get("nickname"), "username": r.get("username"),
             "telegram_id": r.get("telegram_id")} for r in rows]
