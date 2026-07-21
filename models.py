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
    # season_number: mavsum raqami (1, 2, 3...) — o'z turi (kind) ichida.
    # season_kind: 'league' (golden_ball/golden_boot/league_cup) yoki 'wc' (wc_cup).
    #   Liga va WC mavsumi alohida yakunlangani uchun season_number ular uchun
    #   mustaqil sanaladi — kind bilan birga o'qiladi.
    # telegram_id: sovrin egasining Telegram ID'si — DOIMIY bog'lanish. users
    #   jadvali mavsum resetida o'chsa ham sovrin tarixi telegram_id orqali
    #   egasiga bog'liq qoladi (odam qayta kirsa o'sha telegram_id bilan tanaladi).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS season_prizes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            telegram_id INTEGER,
            prize_type TEXT NOT NULL,
            league_id INTEGER,
            season_number INTEGER NOT NULL,
            season_kind TEXT NOT NULL DEFAULT 'league',
            awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues(id)
        )
    """)

    # === season_state (joriy mavsum raqami) ===
    # Bitta qator (id=1). Liga va WC mavsumi ALOHIDA yakunlanadi:
    #   current_season — LIGA mavsumi ("Liga mavsumini yakunlash" da oshadi).
    #   wc_season      — WC mavsumi ("WC mavsumini yakunlash" da oshadi).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS season_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            current_season INTEGER NOT NULL DEFAULT 1,
            wc_season INTEGER NOT NULL DEFAULT 1
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO season_state (id, current_season) VALUES (1, 1)")

    # === season_celebration_seen (mavsum yakuni tabrik oynasi — bir martalik) ===
    # Mavsum yakunlangach web app'ga birinchi kirishda ko'rsatiladigan tabrik/
    # sovrindorlar oynasi HAR BIR (telegram_id, mavsum, kind) uchun faqat 1 marta
    # ko'rsatiladi. UNIQUE — idempotentlik (qoida #38). telegram_id ishlatiladi,
    # chunki users reset'da user_id o'zgarishi mumkin emas-u, lekin sovrinlar
    # mantig'i telegram_id ga bog'langan (izchillik uchun shu kalit).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS season_celebration_seen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            season_number INTEGER NOT NULL,
            season_kind TEXT NOT NULL DEFAULT 'league',
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (telegram_id, season_number, season_kind)
        )
    """)

    # === cl_qualifiers (Chempionlar ligasi kvalifikatsiyasi) ===
    # Liga mavsumi yakunlanganda: 5 liga × top-6 (30) + eng yaxshi 2 ta 7-o'rin = 32.
    # telegram_id — ASOSIY kalit-tushuncha: ishtirokchi yangi mavsumda boshqa klub
    # bilan ro'yxatdan o'tsa ham, ChL'da qatnashish huquqi SHU odamga tegishli.
    # nickname/league_name — snapshot (reset'da registrations o'chadi, tarix qolsin).
    # qualified_via: 'top6' yoki 'best7'. from_season: qaysi mavsum natijasidan.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cl_qualifiers (
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
    # Tez-tez from_season bo'yicha o'qiladi (qoida #30)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cl_qualifiers_season ON cl_qualifiers(from_season)"
    )

    # === cl_participants (Chempionlar ligasi ishtirokchilari — joriy mavsum) ===
    # Kvalifikant (cl_qualifiers) yangi mavsumda liga ro'yxatidan o'tgach shu
    # jadvalga sinxronlanadi (cl_core.cl_sync_participants) — YANGI tanlagan
    # klubi bilan. E'tibor klubda emas, ODAMDA (telegram_id).
    # group_number: qur'adan keyin 1..8; ungacha NULL.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cl_participants (
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
        "CREATE INDEX IF NOT EXISTS idx_cl_participants_season_group "
        "ON cl_participants(season, group_number)"
    )

    # === cl_matches (ChL guruh o'yinlari) ===
    # WC guruh o'yinlari sxemasi asosida: 4 kishilik guruh, 3 tur (matchday),
    # status oqimi liga/WC bilan bir xil (pending -> awaiting_confirmation ->
    # confirmed / admin_pending). player*_id = users.id.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cl_matches (
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
        "CREATE INDEX IF NOT EXISTS idx_cl_matches_season_group "
        "ON cl_matches(season, group_number, matchday)"
    )

    # === DIVIZION (3-tab) ===
    # Har kuni 17:00-19:00 (Toshkent) ro'yxat, 19:00 dan keyin qur'a (juftlash),
    # deadline 23:30. Achko: g'alaba +15, durang +10, mag'lubiyat -10.
    # div_registrations: kunlik ro'yxat (day = 'YYYY-MM-DD').
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS div_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            telegram_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            nickname TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (day, telegram_id)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_registrations_day ON div_registrations(day)"
    )
    # div_matches: kunlik juftliklar. player2_id NULL = toq qolgan (avtomatik
    # g'alaba, status darhol 'confirmed'). Status oqimi liga/WC/ChL bilan bir xil.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS div_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            player1_id INTEGER NOT NULL,
            player2_id INTEGER,
            score1 INTEGER,
            score2 INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            submitted_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player1_id) REFERENCES users(id)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_matches_day ON div_matches(day)"
    )
    # div_state: qur'a/deadline bir marta bajarilishi belgilari (idempotentlik)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS div_state (
            day TEXT PRIMARY KEY,
            paired_at TIMESTAMP,
            resolved_at TIMESTAMP,
            reg_announced_at TIMESTAMP
        )
    """)
    # div_bans: divizion kunlik banlar (2026-07-17, division_bans.py) —
    # start_day..until_day (ikkalasi ham kiradi) oralig'ida ro'yxat yopiq
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS div_bans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            telegram_id INTEGER NOT NULL,
            start_day TEXT NOT NULL,
            until_day TEXT NOT NULL,
            days INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_bans_tg ON div_bans(telegram_id, until_day)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_bans_user ON div_bans(user_id, until_day)"
    )
    # div_messages: divizion o'yin ichidagi sodda chat (bot chati)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS div_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES div_matches(id)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_messages_match ON div_messages(match_id)"
    )

    # === cl_messages (ChL o'yin ichidagi chat — div_messages naqshi) ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cl_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES cl_matches(id)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cl_messages_match ON cl_messages(match_id)"
    )

    # === cl_state (ChL tur boshqaruvi: boshlangan/joriy tur) ===
    # started=0 → hamma turlar yopiq. Admin boshlaganda started=1, current_matchday=1.
    # Har kuni 23:30 (Toshkent) da joriy tur yopiladi va keyingisi ochiladi (cl_rounds).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cl_state (
            season INTEGER PRIMARY KEY,
            started INTEGER NOT NULL DEFAULT 0,
            current_matchday INTEGER NOT NULL DEFAULT 0,
            last_advance_date TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # === Migratsiyalar (qoida #31 — baza qo'lda o'zgartirilmaydi) ===
    # M1: eski bazadagi div_messages'ga is_read ustuni qo'shish
    try:
        cursor.execute("ALTER TABLE div_messages ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass  # ustun allaqachon bor
    # M2: eski 'cancelled' Divizion o'yinlari endi ishlatilmaydi — pending'ga
    # qaytariladi (ishtirokchilar natijani qayta kirita olishi uchun)
    cursor.execute(
        "UPDATE div_matches SET status='pending', score1=NULL, score2=NULL, "
        "submitted_by=NULL WHERE status='cancelled'"
    )

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

    # === cl_playoff_matches (ChL play-off: 2 o'yinli juftliklar, final — 1 o'yin) ===
    # 2026-07-20: round: r16|r8|r4|final. position: juftlik o'rni (r16: 0..7).
    # leg: 1|2 (final faqat 1). player1_id = shu O'YINDA UY egasi.
    # Juftlik tomonlari: sideA = leg1.player2 (2-o'yinda uyda), sideB = leg1.player1.
    # 2-o'yin 1-o'yin tasdiqlangandan KEYIN yaratiladi. Agregat teng bo'lishi
    # taqiqlanadi (eFootball'da qo'shimcha vaqt/penalti o'yin ichida hal qilinadi).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cl_playoff_matches (
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
    # Tez-tez qidiriladigan ustunlar (qoida #30)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cl_po_season_round ON cl_playoff_matches(season, round)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cl_po_p1 ON cl_playoff_matches(player1_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cl_po_p2 ON cl_playoff_matches(player2_id)")

    # === cl_playoff_state (mavsum bo'yicha: play-off boshlanganmi) ===
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cl_playoff_state (
            season INTEGER PRIMARY KEY,
            started INTEGER NOT NULL DEFAULT 0,
            started_at TIMESTAMP
        )
    """)

    # === cl_po_messages (ChL PLAY-OFF o'yin ichidagi chat — cl_messages naqshi) ===
    # 2026-07-21: alohida jadval (cl_messages bilan match_id to'qnashuvi bo'lmasligi
    # uchun — u cl_matches'ga, bu cl_playoff_matches'ga bog'langan).
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cl_po_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES cl_playoff_matches(id)
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_cl_po_messages_match ON cl_po_messages(match_id)"
    )

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
        # 2026-07-16: 17:00 "ro'yxat ochildi" e'loni — kuniga bir marta (idempotentlik)
        "ALTER TABLE div_state ADD COLUMN reg_announced_at TIMESTAMP",
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
        # Liga/WC mavsumini ajratish: WC uchun alohida mavsum raqami + cooldown vaqti
        "ALTER TABLE season_state ADD COLUMN wc_season INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE season_state ADD COLUMN wc_last_finalized_at TIMESTAMP",
        # Sovrin yozuvini liga/WC turiga ajratish (eski yozuvlar quyida to'g'rilanadi)
        "ALTER TABLE season_prizes ADD COLUMN season_kind TEXT NOT NULL DEFAULT 'league'",
        # Sovrinni DOIMIY telegram_id ga bog'lash (users o'chsa ham tarix qoladi)
        "ALTER TABLE season_prizes ADD COLUMN telegram_id INTEGER",
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

    # Data-fix (bir martalik, idempotent): eski wc_cup sovrinlari yangi
    # season_kind ustunida default 'league' bo'lib qolmasin — 'wc' ga to'g'rilanadi.
    # Liga turlari (golden_ball/golden_boot/league_cup) allaqachon 'league' — tegilmaydi.
    try:
        cursor.execute(
            "UPDATE season_prizes SET season_kind = 'wc' "
            "WHERE prize_type = 'wc_cup' AND season_kind != 'wc'"
        )
        conn.commit()
    except sqlite3.OperationalError as exc:
        logger.error("season_kind data-fix xatosi: %s", exc)
        raise

    # Data-fix: eski sovrinlarga telegram_id ni users'dan to'ldiramiz (users hali
    # o'chirilmagan bo'lsa). Keyin reset users'ni o'chirsa ham telegram_id qoladi.
    try:
        cursor.execute(
            "UPDATE season_prizes SET telegram_id = ("
            "  SELECT u.telegram_id FROM users u WHERE u.id = season_prizes.user_id"
            ") WHERE telegram_id IS NULL AND user_id IS NOT NULL"
        )
        conn.commit()
    except sqlite3.OperationalError as exc:
        logger.error("telegram_id backfill xatosi: %s", exc)
        raise

    # BIR MARTALIK TUZATISH (guarded flag bilan — faqat 1 marta ishlaydi):
    # Sinov paytida WC bir necha marta yakunlanib, wc_season 3 ga chiqib ketgan va
    # 2-mavsum WC sovrinlari (kubok/to'purar) yozilib qolgan. Aslida faqat 1-mavsum
    # yakunlangan (chempion 1-mavsum g'olibi). Shuning uchun:
    #   - season_number >= 2 bo'lgan barcha WC sovrinlari o'chiriladi (fantom yozuvlar),
    #   - wc_season 2 ga qaytariladi (2-mavsum endi boshlanadi).
    # Faqat WC ga tegadi (season_kind='wc'); liga sovrinlariga TEGMAYDI.
    # Guard: season_state.wc_season_fix_done = 1 belgisi — qayta ishlamaydi (idempotent
    # va kelajakda haqiqiy 3-mavsumni buzib qo'ymaydi).
    try:
        cursor.execute("ALTER TABLE season_state ADD COLUMN wc_season_fix_done INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            logger.error("wc_season_fix_done ustun xatosi: %s", exc)
            raise
    try:
        cursor.execute("SELECT wc_season_fix_done, wc_season FROM season_state WHERE id = 1")
        row = cursor.fetchone()
        if row is not None and not row["wc_season_fix_done"]:
            cursor.execute(
                "DELETE FROM season_prizes WHERE season_kind = 'wc' AND season_number >= 2"
            )
            deleted = cursor.rowcount
            cursor.execute(
                "UPDATE season_state SET wc_season = 2, wc_last_finalized_at = NULL, "
                "wc_season_fix_done = 1 WHERE id = 1"
            )
            conn.commit()
            logger.info("WC mavsum tuzatildi: wc_season=2, o'chirilgan fantom WC sovrini=%s", deleted)
    except sqlite3.OperationalError as exc:
        logger.error("WC mavsum tuzatish xatosi: %s", exc)
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
