"""
ac_models.py — Osiyo Chempionlar ligasi (OChL) jadvallari (2026-10-15).

models.py shishmasligi uchun alohida (qoida #21). Tuzilma YeL jadvallari bilan
bir xil (el_* -> ac_*), ac_*.py modullari shu jadvallardan foydalanadi.
models.init_db() oxirida init_ac_tables() chaqiriladi (CREATE IF NOT EXISTS — idempotent).
"""

import logging
import sqlite3

from models import get_connection

logger = logging.getLogger(__name__)

_SEASON_STATE_ALTERS = (
    # OChL o'zining mavsum raqami (el_season kabi) — "OChL mavsumini yakunlash"da oshadi
    "ALTER TABLE season_state ADD COLUMN ac_season INTEGER NOT NULL DEFAULT 1",
    # OChL mavsumini yakunlashda takror bosishdan cooldown (el_last_finalized_at kabi)
    "ALTER TABLE season_state ADD COLUMN ac_last_finalized_at TIMESTAMP",
)


def init_ac_tables() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # === ac_qualifiers (Osiyo Chempionlar ligasi kvalifikatsiyasi — cl_qualifiers bilan bir xil tuzilma) ===
        # Liga mavsumi yakunlanganda: 8..14-o'rinlar (ChL'ga ketgan eng yaxshi 8-o'rinsiz)
        # + eng yaxshi 1 ta 15-o'rin = 35 (ac_qualification.py).
        # qualified_via: 'top14' yoki 'best15'. from_season: qaysi mavsum natijasidan.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac_qualifiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                user_id INTEGER,
                nickname TEXT,
                league_id INTEGER,
                league_name TEXT,
                position INTEGER NOT NULL,
                points INTEGER NOT NULL DEFAULT 0,
                goal_difference INTEGER NOT NULL DEFAULT 0,
                goals_for INTEGER NOT NULL DEFAULT 0,
                qualified_via TEXT NOT NULL,
                from_season INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (telegram_id, from_season)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ac_qualifiers_season ON ac_qualifiers(from_season)"
        )

        # === ac_participants (Osiyo Chempionlar ligasi ishtirokchilari — cl_participants bilan bir xil) ===
        # Kvalifikant (ac_qualifiers) telegram_id orqali eslab qolinadi; yangi mavsumda
        # istalgan klub bilan liga ro'yxatidan o'tsa shu jadvalga sinxronlanadi
        # (ac_core.ac_sync_participants). group_number: qur'adan keyin; ungacha NULL.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                nickname TEXT,
                club_name TEXT,
                group_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (telegram_id, season)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ac_participants_season_group "
            "ON ac_participants(season, group_number)"
        )

        # === ac_matches (Osiyo Chempionlar ligasi liga bosqichi o'yinlari — cl_matches bilan bir xil) ===
        # Swiss: barcha ishtirokchi group_number=AC_LEAGUE_GROUP, 8 tur, mehmon o'yinisiz.
        # status oqimi: pending -> awaiting_confirmation -> confirmed / admin_pending.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER NOT NULL,
                group_number INTEGER NOT NULL,
                matchday INTEGER NOT NULL,
                player1_id INTEGER NOT NULL,
                player2_id INTEGER NOT NULL,
                score1 INTEGER,
                score2 INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                submitted_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player1_id) REFERENCES users(id),
                FOREIGN KEY (player2_id) REFERENCES users(id)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ac_matches_season_group "
            "ON ac_matches(season, group_number, matchday)"
        )

        # === ac_messages (OChL o'yin ichidagi chat — cl_messages bilan bir xil) ===
        # read_at boshidan bor (nizo hisoboti — chat_report.MODES['ac']).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES ac_matches(id)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ac_messages_match ON ac_messages(match_id)"
        )

        # === ac_playoff_matches (OChL play-off — cl_playoff_matches bilan bir xil) ===
        # round: playin|r16|r8|r4|final. position: juftlik o'rni. leg: 1|2 (final faqat 1).
        # player1_id = shu O'YINDA uy egasi. sideA = leg1.player2, sideB = leg1.player1.
        # Uy+mehmon bir vaqtda yaratiladi; agregat teng bo'lishi taqiqlanadi.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac_playoff_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season INTEGER NOT NULL,
                round TEXT NOT NULL,
                position INTEGER NOT NULL,
                leg INTEGER NOT NULL DEFAULT 1,
                player1_id INTEGER,
                player2_id INTEGER,
                score1 INTEGER,
                score2 INTEGER,
                submitted_by INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (season, round, position, leg),
                FOREIGN KEY (player1_id) REFERENCES users(id),
                FOREIGN KEY (player2_id) REFERENCES users(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ac_po_season_round ON ac_playoff_matches(season, round)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ac_po_p1 ON ac_playoff_matches(player1_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ac_po_p2 ON ac_playoff_matches(player2_id)")

        # === ac_po_messages (OChL PLAY-OFF chati — cl_po_messages bilan bir xil, read_at boshidan) ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac_po_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES ac_playoff_matches(id)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ac_po_messages_match ON ac_po_messages(match_id)"
        )

        # === ac_playoff_state (mavsum bo'yicha: OChL play-off boshlanganmi) ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac_playoff_state (
                season INTEGER PRIMARY KEY,
                started INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMP
            )
        """)

        # === ac_state (OChL tur boshqaruvi — cl_state bilan bir xil) ===
        # started=0 -> hamma turlar yopiq; admin boshlaganda 1-tur ochiladi;
        # har kuni 23:30 (Toshkent) da joriy tur yopiladi (ac_rounds.ac_tick).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac_state (
                season INTEGER PRIMARY KEY,
                started INTEGER NOT NULL DEFAULT 0,
                current_matchday INTEGER NOT NULL DEFAULT 0,
                last_advance_date TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        for stmt in _SEASON_STATE_ALTERS:
            try:
                cursor.execute(stmt)
            except sqlite3.OperationalError as exc:
                if "duplicate column" not in str(exc).lower():
                    raise
        conn.commit()
    finally:
        conn.close()
