"""
db_migrations.py — Sxemani TUZATUVCHI migratsiyalar va indekslar.

models.init_db() oxirida chaqiriladi (oddiy ALTER migratsiyalardan KEYIN).
Har bir amal idempotent: bir necha marta chaqirilsa ham xavfsiz.

Nega kerak (AUDIT A1): 2026-07-01 dan OLDIN yaratilgan DB'larda
wc_chat_notify/wc_chat_typing jadvallari PRIMARY KEY'ida `is_playoff` yo'q
(ALTER TABLE PK'ni o'zgartira olmaydi), shuning uchun wc_chat.py'dagi
`ON CONFLICT(..., is_playoff)` upsert'lari OperationalError beradi — WC chat
500 bilan buziladi. Shuningdek eski wc_messages'da `match_id -> wc_matches`
FOREIGN KEY qolgan — play-off xabarlari (match_id wc_playoff_matches'dan)
FK xatosiga uchrashi mumkin. Yechim: jadvalni YANGI sxema bilan qayta qurish
(rename -> create -> copy -> drop), ma'lumot to'liq saqlanadi.

AUDIT A2: registrations(league_id, club_name) va
wc_registrations(group_letter, team_name) uchun UNIQUE indeks — race'da
bitta klub/jamoa ikki kishiga yozilishining DB-darajasidagi himoyasi.

AUDIT B3: tez-tez so'raladigan ustunlarga oddiy indekslar (qoida #30).
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)


# ============ Yordamchilar ============

def _table_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cursor.fetchone() is not None


def _pk_columns(cursor, table: str) -> list[str]:
    """Jadval PRIMARY KEY ustunlari (pk tartibida)."""
    cursor.execute(f"PRAGMA table_info({table})")
    rows = [dict(r) for r in cursor.fetchall()]
    pk = [r for r in rows if r["pk"] > 0]
    pk.sort(key=lambda r: r["pk"])
    return [r["name"] for r in pk]


def _fk_ref_tables(cursor, table: str) -> set[str]:
    """Jadvalning FOREIGN KEY'lari ishora qiladigan jadval nomlari."""
    cursor.execute(f"PRAGMA foreign_key_list({table})")
    return {dict(r)["table"] for r in cursor.fetchall()}


# ============ A1: WC chat jadvallarini qayta qurish ============

def _rebuild(conn, table: str, create_sql: str, copy_cols: str) -> None:
    """
    Jadvalni yangi sxema bilan atomik qayta quradi (BEGIN IMMEDIATE ... COMMIT).
    copy_cols: eski jadvaldan ko'chiriladigan ustunlar (SELECT ro'yxati).
    """
    cursor = conn.cursor()
    cursor.execute("BEGIN IMMEDIATE")
    try:
        cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
        cursor.execute(create_sql)
        cursor.execute(
            f"INSERT INTO {table} ({copy_cols}) SELECT {copy_cols} FROM {table}_old"
        )
        cursor.execute(f"DROP TABLE {table}_old")
        cursor.execute("COMMIT")
        logger.info("Migratsiya: %s jadvali yangi sxema bilan qayta qurildi.", table)
    except Exception:
        cursor.execute("ROLLBACK")
        raise


def _fix_wc_chat_tables(conn) -> None:
    """Eski-PK wc_chat_notify/wc_chat_typing va FK'li wc_messages'ni tuzatadi."""
    cursor = conn.cursor()

    # wc_chat_notify: PK'da is_playoff bo'lishi shart (ON CONFLICT uchun)
    if _table_exists(cursor, "wc_chat_notify") and \
            "is_playoff" not in _pk_columns(cursor, "wc_chat_notify"):
        _rebuild(
            conn,
            "wc_chat_notify",
            """CREATE TABLE wc_chat_notify (
                match_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                is_playoff INTEGER NOT NULL DEFAULT 0,
                last_notified_at TIMESTAMP,
                PRIMARY KEY (match_id, recipient_id, is_playoff)
            )""",
            "match_id, recipient_id, is_playoff, last_notified_at",
        )

    # wc_chat_typing: PK'da is_playoff bo'lishi shart
    if _table_exists(cursor, "wc_chat_typing") and \
            "is_playoff" not in _pk_columns(cursor, "wc_chat_typing"):
        _rebuild(
            conn,
            "wc_chat_typing",
            """CREATE TABLE wc_chat_typing (
                match_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                is_playoff INTEGER NOT NULL DEFAULT 0,
                typing_at TIMESTAMP,
                PRIMARY KEY (match_id, user_id, is_playoff)
            )""",
            "match_id, user_id, is_playoff, typing_at",
        )

    # wc_messages: eski FK (match_id -> wc_matches) olib tashlanishi kerak
    # (play-off xabarlarining match_id'si wc_playoff_matches'dan keladi)
    if _table_exists(cursor, "wc_messages") and \
            "wc_matches" in _fk_ref_tables(cursor, "wc_messages"):
        _rebuild(
            conn,
            "wc_messages",
            """CREATE TABLE wc_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                is_playoff INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id)
            )""",
            "id, match_id, sender_id, text, is_read, is_playoff, created_at",
        )


# ============ A2: UNIQUE indekslar (race himoyasi) ============

def _ensure_unique_indexes(conn) -> None:
    """
    Klub/jamoa band qilish uchun UNIQUE indekslar. Agar DB'da ALLAQACHON
    dublikat bo'lsa — indeks yaratilmaydi, WARNING log yoziladi (bot yiqilmaydi;
    dublikatlarni admin qo'lda hal qilgach keyingi startda indeks o'zi tushadi).
    """
    cursor = conn.cursor()
    uniques = [
        ("idx_registrations_league_club_uq",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_registrations_league_club_uq "
         "ON registrations(league_id, club_name)"),
        ("idx_wc_registrations_group_team_uq",
         "CREATE UNIQUE INDEX IF NOT EXISTS idx_wc_registrations_group_team_uq "
         "ON wc_registrations(group_letter, team_name)"),
    ]
    for name, sql in uniques:
        try:
            cursor.execute(sql)
            conn.commit()
        except sqlite3.IntegrityError as exc:
            logger.warning(
                "UNIQUE indeks %s yaratilmadi — jadvalda dublikat bor: %s "
                "(dublikatni tozalagach keyingi startda avtomatik yaratiladi)",
                name, exc,
            )


# ============ B3: samaradorlik indekslari ============

def _ensure_perf_indexes(conn) -> None:
    """Tez-tez so'raladigan ustunlarga oddiy indekslar (qoida #30)."""
    cursor = conn.cursor()
    indexes = [
        # matches: reyting (league_id+status), o'yinchi ro'yxatlari
        "CREATE INDEX IF NOT EXISTS idx_matches_league_status ON matches(league_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_matches_player1 ON matches(player1_id)",
        "CREATE INDEX IF NOT EXISTS idx_matches_player2 ON matches(player2_id)",
        # chat polling (2s da bir): messages/wc_messages
        "CREATE INDEX IF NOT EXISTS idx_messages_match_read ON messages(match_id, is_read)",
        "CREATE INDEX IF NOT EXISTS idx_wc_messages_match_playoff ON wc_messages(match_id, is_playoff)",
        # WC guruh o'yinlari
        "CREATE INDEX IF NOT EXISTS idx_wc_matches_group_status ON wc_matches(group_letter, status)",
        "CREATE INDEX IF NOT EXISTS idx_wc_matches_player1 ON wc_matches(player1_id)",
        "CREATE INDEX IF NOT EXISTS idx_wc_matches_player2 ON wc_matches(player2_id)",
    ]
    for sql in indexes:
        cursor.execute(sql)
    conn.commit()


# ============ Kirish nuqtasi ============

def run_migrations() -> None:
    """
    Barcha tuzatuvchi migratsiyalarni bajaradi. O'z ulanishini ochadi
    (autocommit rejimida — BEGIN IMMEDIATE'ni o'zi boshqaradi).
    init_db() oxirida chaqiriladi.
    """
    from models import get_connection  # lokal import — circular import oldini olish

    conn = get_connection()
    conn.isolation_level = None  # tranzaksiyani qo'lda boshqaramiz (BEGIN/COMMIT)
    try:
        _fix_wc_chat_tables(conn)
        _ensure_unique_indexes(conn)
        _ensure_perf_indexes(conn)
    finally:
        conn.close()
