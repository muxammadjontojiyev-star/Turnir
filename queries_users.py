"""
queries_users.py — Foydalanuvchilar CRUD + liga ro'yxatdan o'tish (registrations).

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from models import get_connection
from config import (
    DEFAULT_LANGUAGE,
)


# ============ USERS ============

def get_or_create_user(telegram_id: int, nickname: str, username: str | None = None) -> dict:
    """
    Foydalanuvchini topadi, topilmasa yangi yaratadi.

    username (Telegram @username) berilsa: yangi user yaratilganda yoziladi,
    mavjud user'da esa yangilanadi (foydalanuvchi keyinroq username
    qo'shishi yoki o'zgartirishi mumkin).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            "INSERT INTO users (telegram_id, nickname, username, language) VALUES (?, ?, ?, ?)",
            (telegram_id, nickname, username, DEFAULT_LANGUAGE),
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
    elif username is not None and row["username"] != username:
        # Mavjud user — username o'zgargan bo'lsa yangilaymiz
        cursor.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
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


def get_user_by_id(user_id: int) -> dict | None:
    """Internal user.id bo'yicha foydalanuvchini qaytaradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
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


def get_all_users_with_registration() -> list[dict]:
    """
    Barcha foydalanuvchilarni, ro'yxatdan o'tgan ligasi va klubi bilan birga
    qaytaradi (admin panel uchun). Ro'yxatdan o'tmagan foydalanuvchilarda
    league_id va club_name = None.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT users.id, users.telegram_id, users.nickname, users.username,
               registrations.league_id, registrations.club_name
        FROM users
        LEFT JOIN registrations ON registrations.user_id = users.id
        ORDER BY users.id ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def remove_user_completely(user_id: int) -> tuple[bool, str]:
    """
    Foydalanuvchini butunlay o'chiradi: uning matchlari, ro'yxatdan
    o'tgan yozuvi va user qatorining o'zi (admin uchun).

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "user_not_found"
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if cursor.fetchone() is None:
        conn.close()
        return False, "user_not_found"

    cursor.execute(
        "DELETE FROM matches WHERE player1_id = ? OR player2_id = ?",
        (user_id, user_id),
    )
    cursor.execute("DELETE FROM registrations WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

    conn.commit()
    conn.close()
    return True, "ok"


# ============ REGISTRATIONS ============

def get_user_registration(user_id: int) -> dict | None:
    """Foydalanuvchining ro'yxatdan o'tgan ligasini qaytaradi (agar bor bo'lsa)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registrations WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_league_members_for_notify(league_id: int) -> list[dict]:
    """
    Ligadagi barcha ishtirokchilarning telegram_id va language'ini qaytaradi
    (inline bildirishnoma yuborish uchun). Format: [{telegram_id, language}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT users.telegram_id, users.language
        FROM registrations
        JOIN users ON users.id = registrations.user_id
        WHERE registrations.league_id = ?
        """,
        (league_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def register_user_to_league(user_id: int, league_id: int, club_name: str | None = None) -> tuple[bool, str]:
    """
    Foydalanuvchini ligaga ro'yxatdan o'tkazadi.

    RACE HIMOYASI (audit A2): barcha tekshiruvlar va INSERT bitta BEGIN IMMEDIATE
    tranzaksiyasida — ikki kishi bir vaqtda bossa ham bitta klub ikki kishiga
    yozilmaydi va liga max_players'dan oshmaydi. Qo'shimcha qatlam:
    UNIQUE(league_id, club_name) indeksi (db_migrations.py) IntegrityError beradi.

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "already_registered", "league_full", "league_not_found", "club_taken"
    """
    import sqlite3

    conn = get_connection()
    conn.isolation_level = None  # tranzaksiyani qo'lda boshqaramiz
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")  # yozish qulfi — parallel so'rovlar navbatda

        cursor.execute("SELECT 1 FROM registrations WHERE user_id = ?", (user_id,))
        if cursor.fetchone() is not None:
            cursor.execute("ROLLBACK")
            return False, "already_registered"

        cursor.execute("SELECT max_players FROM leagues WHERE id = ?", (league_id,))
        league_row = cursor.fetchone()
        if league_row is None:
            cursor.execute("ROLLBACK")
            return False, "league_not_found"

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM registrations WHERE league_id = ?",
            (league_id,),
        )
        if cursor.fetchone()["cnt"] >= league_row["max_players"]:
            cursor.execute("ROLLBACK")
            return False, "league_full"

        if club_name is not None:
            cursor.execute(
                "SELECT 1 FROM registrations WHERE league_id = ? AND club_name = ?",
                (league_id, club_name),
            )
            if cursor.fetchone() is not None:
                cursor.execute("ROLLBACK")
                return False, "club_taken"

        cursor.execute(
            "INSERT INTO registrations (user_id, league_id, club_name) VALUES (?, ?, ?)",
            (user_id, league_id, club_name),
        )
        cursor.execute("COMMIT")
        return True, "ok"
    except sqlite3.IntegrityError as exc:
        # UNIQUE indeks ishga tushdi (qo'shimcha himoya qatlami)
        cursor.execute("ROLLBACK")
        if "user_id" in str(exc):
            return False, "already_registered"
        return False, "club_taken"
    except Exception:
        cursor.execute("ROLLBACK")
        raise
    finally:
        conn.close()
