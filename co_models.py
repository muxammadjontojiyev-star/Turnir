"""
co_models.py — Konferensiya ligasi (KL) jadvallari (2026-10-15).

models.py shishmasligi uchun alohida (qoida #21). Tuzilma YeL jadvallari bilan
bir xil (el_* -> co_*), co_*.py modullari shu jadvallardan foydalanadi.
models.init_db() oxirida init_co_tables() chaqiriladi (CREATE IF NOT EXISTS — idempotent).
"""

import logging
import sqlite3

from models import get_connection

logger = logging.getLogger(__name__)

_SEASON_STATE_ALTERS = (
    # KL o'zining mavsum raqami (el_season kabi) — "KL mavsumini yakunlash"da oshadi
    "ALTER TABLE season_state ADD COLUMN co_season INTEGER NOT NULL DEFAULT 1",
    # KL mavsumini yakunlashda takror bosishdan cooldown (el_last_finalized_at kabi)
    "ALTER TABLE season_state ADD COLUMN co_last_finalized_at TIMESTAMP",
)


def init_co_tables() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # === co_qualifiers (Konferensiya ligasi kvalifikatsiyasi — cl_qualifiers bilan bir xil tuzilma) ===
        # Liga mavsumi yakunlanganda: 8..14-o'rinlar (ChL'ga ketgan eng yaxshi 8-o'rinsiz)
        # + eng yaxshi 1 ta 15-o'rin = 35 (co_qualification.py).
        # qualified_via: 'top14' yoki 'best15'. from_season: qaysi mavsum natijasidan.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_qualifiers (
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
            "CREATE INDEX IF NOT EXISTS idx_co_qualifiers_season ON co_qualifiers(from_season)"
        )

        # === co_participants (Konferensiya ligasi ishtirokchilari — cl_participants bilan bir xil) ===
        # Kvalifikant (co_qualifiers) telegram_id orqali eslab qolinadi; yangi mavsumda
        # istalgan klub bilan liga ro'yxatidan o'tsa shu jadvalga sinxronlanadi
        # (co_core.co_sync_participants). group_number: qur'adan keyin; ungacha NULL.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_participants (
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
            "CREATE INDEX IF NOT EXISTS idx_co_participants_season_group "
            "ON co_participants(season, group_number)"
        )

        # === co_matches (Konferensiya ligasi liga bosqichi o'yinlari — cl_matches bilan bir xil) ===
        # Swiss: barcha ishtirokchi group_number=CO_LEAGUE_GROUP, 6 tur, mehmon o'yinisiz.
        # status oqimi: pending -> awaiting_confirmation -> confirmed / admin_pending.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_matches (
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
            "CREATE INDEX IF NOT EXISTS idx_co_matches_season_group "
            "ON co_matches(season, group_number, matchday)"
        )

        # === co_messages (KL o'yin ichidagi chat — cl_messages bilan bir xil) ===
        # read_at boshidan bor (nizo hisoboti — chat_report.MODES['co']).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES co_matches(id)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_co_messages_match ON co_messages(match_id)"
        )

        # === co_playoff_matches (KL play-off — cl_playoff_matches bilan bir xil) ===
        # round: playin|r16|r8|r4|final. position: juftlik o'rni. leg: 1|2 (final faqat 1).
        # player1_id = shu O'YINDA uy egasi. sideA = leg1.player2, sideB = leg1.player1.
        # Uy+mehmon bir vaqtda yaratiladi; agregat teng bo'lishi taqiqlanadi.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_playoff_matches (
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_co_po_season_round ON co_playoff_matches(season, round)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_co_po_p1 ON co_playoff_matches(player1_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_co_po_p2 ON co_playoff_matches(player2_id)")

        # === co_po_messages (KL PLAY-OFF chati — cl_po_messages bilan bir xil, read_at boshidan) ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_po_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES co_playoff_matches(id)
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_co_po_messages_match ON co_po_messages(match_id)"
        )

        # === co_playoff_state (mavsum bo'yicha: KL play-off boshlanganmi) ===
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_playoff_state (
                season INTEGER PRIMARY KEY,
                started INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMP
            )
        """)

        # === co_state (KL tur boshqaruvi — cl_state bilan bir xil) ===
        # started=0 -> hamma turlar yopiq; admin boshlaganda 1-tur ochiladi;
        # har kuni 23:30 (Toshkent) da joriy tur yopiladi (co_rounds.co_tick).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS co_state (
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
