"""
models.py — SQLite jadval sxemalari.

Bu fayl faqat jadval strukturasini belgilaydi (CREATE TABLE).
CRUD amallari uchun queries.py ga qarang.
"""

import sqlite3
from config import DB_PATH


def get_connection():
    """Yangi DB ulanish qaytaradi."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Barcha jadvallarni yaratadi (agar mavjud bo'lmasa)."""
    conn = get_connection()
    cursor = conn.cursor()

    # === users ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            nickname TEXT NOT NULL,
            username TEXT,
            language TEXT NOT NULL DEFAULT 'uz',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # === leagues ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            max_players INTEGER NOT NULL DEFAULT 20,
            status TEXT NOT NULL DEFAULT 'open',
            draw_date TIMESTAMP,
            last_notified_matchday INTEGER NOT NULL DEFAULT 0
        )
    """)

    # === registrations ===
    # UNIQUE(user_id) -> bitta foydalanuvchi faqat bitta ligaga yoza oladi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            league_id INTEGER NOT NULL,
            club_name TEXT,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (league_id) REFERENCES leagues(id)
        )
    """)

    # === matches ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            matchday INTEGER NOT NULL,
            player1_id INTEGER NOT NULL,
            player2_id INTEGER NOT NULL,
            score1 INTEGER,
            score2 INTEGER,
            submitted_by INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (player1_id) REFERENCES users(id),
            FOREIGN KEY (player2_id) REFERENCES users(id),
            FOREIGN KEY (submitted_by) REFERENCES users(id)
        )
    """)

    # === prizes ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prizes (
            league_id INTEGER PRIMARY KEY,
            top_scorer_user_id INTEGER,
            winner_user_id INTEGER,
            FOREIGN KEY (league_id) REFERENCES leagues(id),
            FOREIGN KEY (top_scorer_user_id) REFERENCES users(id),
            FOREIGN KEY (winner_user_id) REFERENCES users(id)
        )
    """)

    # === wc_registrations (World Cup ro'yxati — liga tizimidan ALOHIDA) ===
    # Foydalanuvchi World Cup'da bir marta ro'yxatdan o'tadi (UNIQUE user_id),
    # liga registratsiyasidan mustaqil — ya'ni ligada VA WC'da bir vaqtda qatnasha oladi.
    # group_letter: "A".."L", team_name: tanlangan terma jamoa (guruh ichida noyob).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wc_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            group_letter TEXT NOT NULL,
            team_name TEXT NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # === wc_groups (World Cup guruh holati) ===
    # Har guruh (A–L) uchun bitta qator. draw_date: guruh 4 jamoaga to'lib o'yinlar
    # yaratilgan vaqt (matchday-lock hisoblanishi uchun, liga draw_date kabi).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wc_groups (
            group_letter TEXT PRIMARY KEY,
            draw_date TIMESTAMP,
            last_notified_matchday INTEGER NOT NULL DEFAULT 0
        )
    """)

    # === wc_matches (World Cup guruh o'yinlari) ===
    # Liga matches'ga o'xshash, lekin group_letter bo'yicha. player1/2_id = users.id.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wc_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_letter TEXT NOT NULL,
            matchday INTEGER NOT NULL,
            player1_id INTEGER NOT NULL,
            player2_id INTEGER NOT NULL,
            score1 INTEGER,
            score2 INTEGER,
            submitted_by INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (player1_id) REFERENCES users(id),
            FOREIGN KEY (player2_id) REFERENCES users(id),
            FOREIGN KEY (submitted_by) REFERENCES users(id)
        )
    """)

    # === messages (WebApp chat — aktiv match raqibi bilan) ===
    # sender_id = users.id (kim yuborgan). is_read = raqib o'qidimi (ikkita ✓ uchun).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (sender_id) REFERENCES users(id)
        )
    """)

    # === chat_notify (bot bildirishnomasi anti-spam holati) ===
    # Har (match_id, recipient_id) juftligi uchun bot oxirgi marta qachon xabar
    # berganini saqlaydi — 1 daqiqada bir martadan ko'p yubormaslik uchun.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_notify (
            match_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            last_notified_at TIMESTAMP,
            PRIMARY KEY (match_id, recipient_id)
        )
    """)

    # === chat_typing (kim qachon "yozmoqda") ===
    # Har (match_id, user_id) uchun oxirgi "yozyapman" signali vaqti. Raqib buni
    # o'qib, yaqinda (bir necha soniya) signal bo'lsa "yozmoqda..." ko'rsatadi.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_typing (
            match_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            typing_at TIMESTAMP,
            PRIMARY KEY (match_id, user_id)
        )
    """)

    conn.commit()

    # === MIGRATSIYALAR ===
    # Mavjud DB ga yangi ustunlar qo'shish (agar yo'q bo'lsa)
    migrations = [
        "ALTER TABLE registrations ADD COLUMN club_name TEXT",
        "ALTER TABLE users ADD COLUMN username TEXT",
        "ALTER TABLE leagues ADD COLUMN draw_date TIMESTAMP",
        "ALTER TABLE leagues ADD COLUMN last_notified_matchday INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE leagues ADD COLUMN last_deadline_notice_date TEXT",
        "ALTER TABLE users ADD COLUMN last_seen TIMESTAMP",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
            conn.commit()
        except Exception:
            pass  # Ustun allaqachon mavjud — xato e'tiborsiz qoldiriladi

    conn.close()


def seed_leagues():
    """Boshlang'ich ligalarni qo'shadi (agar mavjud bo'lmasa)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO leagues (name, max_players, status) VALUES (?, ?, ?)",
        ("LaLiga", 20, "open"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO leagues (name, max_players, status) VALUES (?, ?, ?)",
        ("Premier Liga", 20, "open"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO leagues (name, max_players, status) VALUES (?, ?, ?)",
        ("Bundesliga", 18, "open"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO leagues (name, max_players, status) VALUES (?, ?, ?)",
        ("Serie A", 20, "open"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO leagues (name, max_players, status) VALUES (?, ?, ?)",
        ("Ligue 1", 18, "open"),
    )
    conn.commit()
    conn.close()
