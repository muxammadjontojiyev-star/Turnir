"""
queries_wc.py — World Cup: ro'yxatdan o'tish, guruh ma'lumotlari, qur'a sanasi.

queries.py'dan ajratildi (2026-07-03, audit C1 — fayl hajmi qoidasi #21).
Barcha funksiyalar VERBATIM ko'chirilgan, mantiq o'zgartirilmagan.
"""

from datetime import datetime
from models import get_connection
from queries_leagues import _tournament_now


# ============================================================
#  WORLD CUP (Jahon Chempionati) — liga tizimidan ALOHIDA
#  wc_registrations jadvali. Foydalanuvchi WC'da 1 marta ro'yxatdan o'tadi.
# ============================================================

def wc_get_user_registration(user_id: int) -> dict | None:
    """Foydalanuvchining World Cup ro'yxatini qaytaradi (bor bo'lsa)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wc_registrations WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def wc_get_taken_teams(group_letter: str) -> list[str]:
    """Shu guruhda allaqachon band qilingan jamoa nomlari ro'yxati."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT team_name FROM wc_registrations WHERE group_letter = ?",
        (group_letter,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [row["team_name"] for row in rows]


def wc_count_group_players(group_letter: str) -> int:
    """Shu guruhda ro'yxatdan o'tgan ishtirokchilar soni."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM wc_registrations WHERE group_letter = ?",
        (group_letter,),
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"]


def wc_register_user(user_id: int, group_letter: str, team_name: str) -> tuple[bool, str]:
    """
    Foydalanuvchini World Cup'ga ro'yxatdan o'tkazadi.

    Qaytaradi: (muvaffaqiyat: bool, sabab: str)
    Sabablar: "ok", "wc_already_registered", "wc_group_full",
              "wc_invalid_group", "wc_invalid_team", "wc_team_taken"
    """
    # WC_TEAMS_PER_GROUP markazlashtirilgan (wc_data) — guruh to'lganini tekshirish uchun
    import sqlite3
    from wc_data import wc_is_valid_group, wc_team_in_group, WC_TEAMS_PER_GROUP

    # Statik (DB'siz) validatsiyalar — tranzaksiyadan tashqarida tez fail
    if not wc_is_valid_group(group_letter):
        return False, "wc_invalid_group"

    if not wc_team_in_group(group_letter, team_name):
        return False, "wc_invalid_team"

    # RACE HIMOYASI (audit A2): tekshiruv + INSERT bitta BEGIN IMMEDIATE
    # tranzaksiyasida (liga register_user_to_league bilan bir xil naqsh — qoida #10).
    # Qo'shimcha qatlam: UNIQUE(group_letter, team_name) indeksi (db_migrations.py).
    conn = get_connection()
    conn.isolation_level = None
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")

        # Foydalanuvchi WC'da allaqachon ro'yxatdan o'tganmi (1 marta qoidasi)
        cursor.execute("SELECT 1 FROM wc_registrations WHERE user_id = ?", (user_id,))
        if cursor.fetchone() is not None:
            cursor.execute("ROLLBACK")
            return False, "wc_already_registered"

        # Guruh to'lgan bo'lsa (4 jamoa band)
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM wc_registrations WHERE group_letter = ?",
            (group_letter,),
        )
        if cursor.fetchone()["cnt"] >= WC_TEAMS_PER_GROUP:
            cursor.execute("ROLLBACK")
            return False, "wc_group_full"

        # Jamoa allaqachon band qilinganmi
        cursor.execute(
            "SELECT 1 FROM wc_registrations WHERE group_letter = ? AND team_name = ?",
            (group_letter, team_name),
        )
        if cursor.fetchone() is not None:
            cursor.execute("ROLLBACK")
            return False, "wc_team_taken"

        cursor.execute(
            "INSERT INTO wc_registrations (user_id, group_letter, team_name) VALUES (?, ?, ?)",
            (user_id, group_letter, team_name),
        )
        cursor.execute("COMMIT")
    except sqlite3.IntegrityError as exc:
        cursor.execute("ROLLBACK")
        conn.close()
        if "user_id" in str(exc):
            return False, "wc_already_registered"
        return False, "wc_team_taken"
    except Exception:
        cursor.execute("ROLLBACK")
        conn.close()
        raise
    conn.close()

    # Guruh shu registratsiya bilan 4 jamoaga to'ldimi? To'lgan bo'lsa — avtomatik
    # round-robin o'yinlarini yaratamiz va guruh draw_date'ini yozamiz (matchday-lock).
    if wc_count_group_players(group_letter) >= WC_TEAMS_PER_GROUP:
        _wc_try_generate_group(group_letter)

    return True, "ok"


def _wc_try_generate_group(group_letter: str) -> None:
    """
    Guruh to'lganda o'yinlarni avtomatik yaratadi (agar hali yaratilmagan bo'lsa)
    va guruh draw_date'ini hozirgi vaqtga o'rnatadi (matchday hisoblanishi uchun).
    Kechiktirilgan import — circular import oldini olish uchun.
    """
    from wc_schedule import (
        wc_group_has_matches, generate_wc_group_schedule, wc_get_group_player_ids,
    )
    if wc_group_has_matches(group_letter):
        return  # allaqachon yaratilgan — ikkinchi marta qur'a qilmaymiz
    player_ids = wc_get_group_player_ids(group_letter)
    generate_wc_group_schedule(group_letter, player_ids)
    wc_set_group_draw_date(group_letter)


def wc_set_group_draw_date(group_letter: str, dt: datetime | None = None) -> None:
    """
    Guruh qur'a sanasini wc_groups'ga yozadi (turnir mintaqasi, ISO). Bu sana
    asosida WC matchday-lock hisoblanadi (liga set_league_draw_date kabi).
    """
    if dt is None:
        dt = _tournament_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO wc_groups (group_letter, draw_date) VALUES (?, ?)
        ON CONFLICT(group_letter) DO UPDATE SET draw_date = excluded.draw_date
        """,
        (group_letter, dt.isoformat()),
    )
    conn.commit()
    conn.close()


def wc_get_group(group_letter: str) -> dict | None:
    """wc_groups qatorini qaytaradi (draw_date va h.k.) yoki None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wc_groups WHERE group_letter = ?", (group_letter,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
