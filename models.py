"""
models.py — SQLite jadval sxemalari.

Bu fayl faqat jadval strukturasini belgilaydi (CREATE TABLE).
CRUD amallari uchun queries.py ga qarang.
"""

import logging
import sqlite3
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection():
    """Yangi DB ulanish qaytaradi.

    MUSTAHKAMLIK: bot + API + scheduler bitta SQLite faylni bo'lishadi,
    shuning uchun:
      - timeout=15      → qulf kutish (Python darajasida)
      - busy_timeout    → qulf kutish (SQLite darajasida, ms)
      - WAL журнали     → o'qish va yozish bir-birini bloklamaydi
    """
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
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

    # === SEASON PRIZES (sovrin tarixi — mavsum bo'yicha) ===
    # Har mavsum yakunlanganda ishtirokchilar qo'lga kiritgan sovrinlar shu yerda
    # saqlanadi. "Sovrinlarim" profil bo'limi shu jadvaldan o'qiydi.
    # prize_type: 'golden_ball'(5 liga eng ko'p ochko), 'golden_boot'(5 liga eng
    #   ko'p gol), 'league_cup'(liga 1-o'rni — league_id bilan), 'wc_cup'(WC chempioni).
    # league_id: faqat league_cup uchun (qaysi liga kubogi); boshqalarda NULL.
    # season_number: mavsum raqami (1, 2, 3...).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS season_prizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prize_type TEXT NOT NULL,
            league_id INTEGER,
            season_number INTEGER NOT NULL,
            awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (league_id) REFERENCES leagues(id)
        )
    """)

    # === season_state (joriy mavsum raqami) ===
    # Bitta qator (id=1). current_season har "Mavsumni yakunlash" da oshadi.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS season_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_season INTEGER NOT NULL DEFAULT 1
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO season_state (id, current_season) VALUES (1, 1)")

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

    # === admins (qo'shimcha adminlar — bosh admindan tashqari) ===
    # Bosh admin config.py ADMIN_TELEGRAM_IDS'da (hamma narsa). Bu jadval esa
    # bosh admin tayinlagan "oddiy adminlar" — faqat natija tuzata oladi.
    # scope: 'league' (faqat liga natijasi) yoki 'wc' (faqat WC natijasi).
    # UNIQUE(telegram_id, scope): bir odam liga VA wc admin bo'la oladi (ikki qator).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            scope TEXT NOT NULL,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(telegram_id, scope)
        )
    """)

    # === admin_leagues (liga adminini AYNAN qaysi ligalarga biriktirish) ===
    # Bir liga admini (scope='league') bir nechta ligaga biriktirilishi mumkin.
    # Bu jadval bo'sh bo'lsa (admin hech qaysi ligaga biriktirilmagan) — u hech
    # qaysi liga natijasini tuzata olmaydi. Bosh admin esa hamma ligaga ega.
    # UNIQUE(telegram_id, league_id): takror biriktirishni oldini oladi.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            league_id INTEGER NOT NULL,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(telegram_id, league_id)
        )
    """)

    # === WC PLAY-OFF (chiqib ketish bosqichi — 32 jamoa) ===
    # Guruh bosqichidan keyin 32 jamoa: 12 g'olib + 12 ikkinchi + 8 eng yaxshi 3-o'rin.
    # round: 'r32'(1/16) -> 'r16'(1/8) -> 'r8'(1/4) -> 'r4'(1/2) -> 'final' / 'bronze'.
    # position: shu rounddagi o'yin tartibi (0-asosli) — bracket joylashuvi uchun.
    # player1_id/player2_id: NULL bo'lishi mumkin (keyingi bosqich raqibi hali noma'lum).
    # next_match_id + next_slot: g'olib qaysi keyingi matchning qaysi slotiga (1/2) o'tadi.
    #   bronze uchun next yo'q (final mag'lublari bronza o'ynaydi — alohida mantiq).
    # open_date: shu match qachon ochilgan (har kuni 1 match oqimi uchun, NULL=hali yopiq).
    # status: 'pending'(o'ynalmagan) / 'awaiting_confirmation' / 'confirmed'.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wc_playoff_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round TEXT NOT NULL,
            position INTEGER NOT NULL,
            player1_id INTEGER,
            player2_id INTEGER,
            score1 INTEGER,
            score2 INTEGER,
            submitted_by INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            next_match_id INTEGER,
            next_slot INTEGER,
            open_date TIMESTAMP,
            FOREIGN KEY (player1_id) REFERENCES users(id),
            FOREIGN KEY (player2_id) REFERENCES users(id),
            FOREIGN KEY (next_match_id) REFERENCES wc_playoff_matches(id)
        )
    """)

    # === wc_playoff_state (play-off umumiy holati: boshlanganmi, qachon) ===
    # Bitta qator (id=1). started=1 bo'lsa play-off boshlangan. start_date'dan
    # har kuni 23:30 da yangi bosqich/match oqimi hisoblanadi (liga matchday kabi).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wc_playoff_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            started INTEGER NOT NULL DEFAULT 0,
            start_date TIMESTAMP
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

    # === WC CHAT (World Cup chati — liga chatidan alohida, wc_matches uchun) ===
    # Liga messages/chat_notify/chat_typing naqshida, lekin match_id wc_matches'ga
    # ishora qiladi. Alohida jadval — liga chatiga umuman tegmaydi, ID aralashmaydi.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wc_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            is_playoff INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wc_chat_notify (
            match_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            is_playoff INTEGER NOT NULL DEFAULT 0,
            last_notified_at TIMESTAMP,
            PRIMARY KEY (match_id, recipient_id, is_playoff)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wc_chat_typing (
            match_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            is_playoff INTEGER NOT NULL DEFAULT 0,
            typing_at TIMESTAMP,
            PRIMARY KEY (match_id, user_id, is_playoff)
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
        "ALTER TABLE wc_messages ADD COLUMN is_playoff INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE wc_chat_notify ADD COLUMN is_playoff INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE wc_chat_typing ADD COLUMN is_playoff INTEGER NOT NULL DEFAULT 0",
        # A3: takror "Mavsumni yakunlash" bosishdan himoya uchun oxirgi yakunlash vaqti
        "ALTER TABLE season_state ADD COLUMN last_finalized_at TIMESTAMP",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
            conn.commit()
        except sqlite3.OperationalError as exc:
            # "duplicate column" — ustun allaqachon mavjud, bu normal (idempotent).
            # Boshqa har qanday xato — sxema buzilishi, jim yutmaymiz (qoida #44).
            if "duplicate column" in str(exc).lower():
                logger.debug("Migratsiya o'tkazib yuborildi (ustun bor): %s", sql)
            else:
                logger.error("Migratsiya xatosi: %s — %s", sql, exc)
                raise

    conn.close()

    # Tuzatuvchi migratsiyalar (jadval rebuild + UNIQUE + indekslar) —
    # db_migrations.py'da, oddiy ALTER'lardan KEYIN ishlashi shart
    # (is_playoff ustuni allaqachon qo'shilgan bo'ladi).
    from db_migrations import run_migrations  # lokal import — circular oldini olish
    run_migrations()


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
