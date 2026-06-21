"""
queries.py — User, League, Registration uchun CRUD funksiyalari.

Match generatsiyasi va jadval (schedule) bilan bog'liq funksiyalar
uchun schedule.py ga qarang.
"""

from models import get_connection
from config import LEAGUE_STATUS_OPEN, DEFAULT_LANGUAGE


# ============ USERS ============

def get_or_create_user(telegram_id: int, nickname: str) -> dict:
    """Foydalanuvchini topadi, topilmasa yangi yaratadi."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            "INSERT INTO users (telegram_id, nickname, language) VALUES (?, ?, ?)",
            (telegram_id, nickname, DEFAULT_LANGUAGE),
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()

    conn.close()
    return dict(row)


def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    """Telegram ID bo'yicha foydalanuvchini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_language(user_id: int, language: str) -> None:
    """Foydalanuvchi tilini yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
    conn.commit()
    conn.close()


def update_user_nickname(user_id: int, nickname: str) -> None:
    """Foydalanuvchi nickname'ini yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET nickname = ? WHERE id = ?", (nickname, user_id))
    conn.commit()
    conn.close()


# ============ LEAGUES ============

def get_all_leagues() -> list[dict]:
    """Barcha ligalarni qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leagues")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_league_by_id(league_id: int) -> dict | None:
    """ID bo'yicha ligani qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leagues WHERE id = ?", (league_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def count_league_players(league_id: int) -> int:
    """Ligadagi ro'yxatdan o'tgan ishtirokchilar sonini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM registrations WHERE league_id = ?", (league_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"]


def update_league_status(league_id: int, status: str) -> None:
    """Liga statusini yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leagues SET status = ? WHERE id = ?", (status, league_id))
    conn.commit()
    conn.close()


# ============ REGISTRATIONS ============

def get_user_registration(user_id: int) -> dict | None:
    """Foydalanuvchining ro'yxatdan o'tgan ligasini qaytaradi (agar bor bo'lsa)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registrations WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def register_user_to_league(user_id: int, league_id: int) -> tuple[bool, str]:
    """
    Foydalanuvchini ligaga ro'yxatdan o'tkazadi.

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "already_registered", "league_full"
    """
    existing = get_user_registration(user_id)
    if existing is not None:
        return False, "already_registered"

    league = get_league_by_id(league_id)
    if league is None:
        return False, "league_not_found"

    current_count = count_league_players(league_id)
    if current_count >= league["max_players"]:
        return False, "league_full"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO registrations (user_id, league_id) VALUES (?, ?)",
        (user_id, league_id),
    )
    conn.commit()
    conn.close()
    return True, "ok"
