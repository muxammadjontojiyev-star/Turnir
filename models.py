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
            status TEXT NOT NULL DEFAULT 'open'
        )
    """)

    # === registrations ===
    # UNIQUE(user_id) -> bitta foydalanuvchi faqat bitta ligaga yoza oladi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            league_id INTEGER NOT NULL,
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

    conn.commit()
    conn.close()
