"""
tb_models.py — "TEAMLAR JANGI" bo'limi jadvallari (2026-10-15, 1-bosqich).

Rasmiy va shaxsiy turnirlardan TO'LIQ ajratilgan 3-bo'lim. 1-bosqichda faqat
teamlar va a'zolar (mavsum/divizion/o'yinlar — 2-bosqichda alohida jadvallar).
models.init_db() oxirida init_tb_tables() chaqiriladi (CREATE IF NOT EXISTS — idempotent).

  tb_teams    — team: nom (takrorlanmas, katta-kichik harf farqsiz), belgi (emoji),
                sardor, taklif kodi, holat (pending -> approved | rejected).
  tb_members  — a'zolik: bir kishi FAQAT bitta teamda (UNIQUE user_id);
                role: captain | member; in_lineup/lineup_pos — sardor tuzgan asosiy tarkib.
"""

from models import get_connection


def init_tb_tables() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                emoji TEXT,
                captain_user_id INTEGER NOT NULL,
                invite_code TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending',
                reject_reason TEXT,
                reviewed_by INTEGER,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (captain_user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_teams_status ON tb_teams(status)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tb_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL UNIQUE,
                role TEXT NOT NULL DEFAULT 'member',
                in_lineup INTEGER NOT NULL DEFAULT 0,
                lineup_pos INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES tb_teams(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tb_members_team ON tb_members(team_id)")
        conn.commit()
    finally:
        conn.close()
