"""
admin_roles.py — Admin rollari mantig'i (markazlashtirilgan).

Ikki daraja:
  1. BOSH ADMIN — config.py ADMIN_TELEGRAM_IDS'da. Hamma narsani qila oladi:
     ikkala tizimда (liga + wc) barcha admin funksiyalari + admin tayinlash.
  2. ODDIY ADMIN — bosh admin tayinlagan (admins jadvali). Faqat o'z scope'ida
     (liga YOKI wc) natija tuzata oladi. Admin tayinlay OLMAYDI.

scope qiymatlari: 'league', 'wc'.
"""

from models import get_connection
from config import ADMIN_TELEGRAM_IDS

SCOPE_LEAGUE = "league"
SCOPE_WC = "wc"
SCOPE_CL = "cl"              # 2026-07-22: Chempionlar ligasi admin scope'i
SCOPE_DIVISION = "division"  # 2026-07-22: Divizion admin scope'i
VALID_SCOPES = (SCOPE_LEAGUE, SCOPE_WC, SCOPE_CL, SCOPE_DIVISION)


def is_super_admin(telegram_id: int) -> bool:
    """Bosh admin (config.py)? Faqat ular admin tayinlay oladi va hamma narsani qiladi."""
    return telegram_id in ADMIN_TELEGRAM_IDS


def is_scope_admin(telegram_id: int, scope: str) -> bool:
    """
    Foydalanuvchi berilgan scope ('league'/'wc') uchun admin huquqiga egami?
    Bosh admin har doim ha. Oddiy admin faqat o'z scope'ida.
    """
    if is_super_admin(telegram_id):
        return True
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM admins WHERE telegram_id = ? AND scope = ? LIMIT 1",
        (telegram_id, scope),
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def add_admin(telegram_id: int, scope: str, added_by: int) -> tuple[bool, str]:
    """
    Yangi oddiy admin tayinlaydi (faqat bosh admin chaqirishi kerak — bu yerda
    tekshirilmaydi, endpoint darajasida tekshiriladi).

    Qaytaradi: (success, reason). reason: ok / invalid_scope / already_admin /
               cannot_add_super (bosh adminni qo'shib bo'lmaydi — u allaqachon hammasi).
    """
    if scope not in VALID_SCOPES:
        return False, "invalid_scope"
    if is_super_admin(telegram_id):
        return False, "cannot_add_super"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM admins WHERE telegram_id = ? AND scope = ? LIMIT 1",
        (telegram_id, scope),
    )
    if cursor.fetchone() is not None:
        conn.close()
        return False, "already_admin"

    cursor.execute(
        "INSERT INTO admins (telegram_id, scope, added_by) VALUES (?, ?, ?)",
        (telegram_id, scope, added_by),
    )
    conn.commit()
    conn.close()
    return True, "ok"


def remove_admin(telegram_id: int, scope: str) -> bool:
    """
    Oddiy adminni o'z scope'idan o'chiradi. Agar 'league' scope bo'lsa, uning
    barcha liga biriktirishlarini ham tozalaydi. Qaytaradi: o'chirildimi (bool).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM admins WHERE telegram_id = ? AND scope = ?",
        (telegram_id, scope),
    )
    deleted = cursor.rowcount > 0
    # Liga admini o'chirilsa — uning liga biriktirishlari ham keraksiz
    if scope == SCOPE_LEAGUE:
        cursor.execute(
            "DELETE FROM admin_leagues WHERE telegram_id = ?",
            (telegram_id,),
        )
    conn.commit()
    conn.close()
    return deleted


def list_admins(scope: str) -> list[dict]:
    """
    Berilgan scope'dagi oddiy adminlar ro'yxati (bosh admin kiritilmaydi).
    Har biriga users jadvalidan nickname/username qo'shiladi (agar topilsa).
    Format: [{telegram_id, nickname, username, added_at}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT a.telegram_id, a.added_at, u.nickname, u.username
        FROM admins a
        LEFT JOIN users u ON u.telegram_id = a.telegram_id
        WHERE a.scope = ?
        ORDER BY a.added_at
        """,
        (scope,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "telegram_id": row["telegram_id"],
            "added_at": row["added_at"],
            "nickname": row["nickname"],
            "username": row["username"],
        }
        for row in rows
    ]


# ============================================================
#  LIGA BIRIKTIRISH (liga adminini aynan qaysi ligalarga bog'lash)
# ============================================================

def assign_league(telegram_id: int, league_id: int, added_by: int) -> tuple[bool, str]:
    """
    Liga adminini AYNAN bitta ligaga biriktiradi. Admin avval 'league' scope'da
    bo'lishi kerak (admins jadvalida). Bir admin bir nechta ligaga biriktirilishi
    mumkin (har biri alohida chaqiriladi).

    Qaytaradi: (success, reason). Sabablar: ok / not_league_admin / already_assigned
    """
    # Avval 'league' scope admin bo'lishi shart (bosh admin bundan mustasno —
    # u allaqachon hamma ligaga ega, biriktirish kerak emas).
    if is_super_admin(telegram_id):
        return False, "is_super"
    if not is_scope_admin(telegram_id, SCOPE_LEAGUE):
        return False, "not_league_admin"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM admin_leagues WHERE telegram_id = ? AND league_id = ? LIMIT 1",
        (telegram_id, league_id),
    )
    if cursor.fetchone() is not None:
        conn.close()
        return False, "already_assigned"

    cursor.execute(
        "INSERT INTO admin_leagues (telegram_id, league_id, added_by) VALUES (?, ?, ?)",
        (telegram_id, league_id, added_by),
    )
    conn.commit()
    conn.close()
    return True, "ok"


def unassign_league(telegram_id: int, league_id: int) -> bool:
    """Liga adminini bitta ligadan ajratadi. Qaytaradi: o'chirildimi (bool)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM admin_leagues WHERE telegram_id = ? AND league_id = ?",
        (telegram_id, league_id),
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_admin_league_ids(telegram_id: int) -> list[int]:
    """
    Adminga biriktirilgan liga ID'lari ro'yxati. Bosh admin uchun bo'sh ro'yxat
    qaytariladi (chunki u barcha ligaga ega — alohida tekshiriladi).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT league_id FROM admin_leagues WHERE telegram_id = ?",
        (telegram_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["league_id"] for row in rows]


def can_manage_league(telegram_id: int, league_id: int) -> bool:
    """
    Foydalanuvchi berilgan ligani boshqara oladimi (natija tuzatish)?
    Bosh admin — har doim ha. Liga admini — faqat o'ziga biriktirilgan liga.
    """
    if is_super_admin(telegram_id):
        return True
    if not is_scope_admin(telegram_id, SCOPE_LEAGUE):
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM admin_leagues WHERE telegram_id = ? AND league_id = ? LIMIT 1",
        (telegram_id, league_id),
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None
