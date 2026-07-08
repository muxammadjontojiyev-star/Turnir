"""
config.py — Bot sozlamalari va markazlashtirilgan constant qiymatlar.

QOIDA: Yangi magic number kerak bo'lsa — shu faylga qo'shiladi,
boshqa fayllarda hardcode qilinmaydi.
"""

import os

# === Telegram bot tokeni ===
# .env yoki environment variable orqali olinadi (xavfsizlik uchun kodga yozilmaydi)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# === Liga sozlamalari ===
MAX_PLAYERS_PER_LEAGUE = 20      # Har bir ligadagi maksimal ishtirokchilar soni
TOTAL_MATCHDAYS = 38              # Turnir necha kun (tur) davom etadi
MATCHES_PER_MATCHDAY = MAX_PLAYERS_PER_LEAGUE // 2  # Har turda nechta o'yin (10 ta)

# === Turnir vaqt jadvali ===
# Har kuni MATCHDAYS_PER_UNLOCK ta yangi tur (matchday) ochiladi. Boshlanish kuni
# (qur'a tashlangan kun) ham shuncha tur ochiq, keyingi kunlar
# TOURNAMENT_TIMEZONE_OFFSET bo'yicha MATCHDAY_UNLOCK_HOUR'da yana shuncha qo'shiladi.
# Ishtirokchi faqat ochilgan turlarning natijasini kirita oladi (kelajak turlar yopiq).
TOURNAMENT_TIMEZONE_OFFSET = 5   # Toshkent (UTC+5) — soat farqi
MATCHDAY_UNLOCK_HOUR = 23        # Har kuni soat 23:30 (Toshkent) da yangi turlar ochiladi / deadline o'tadi
MATCHDAY_UNLOCK_MINUTE = 30      # Tur ochilishi/deadline daqiqasi (23:30)
MATCHDAYS_PER_UNLOCK = 2         # Har kuni nechta tur ochiladi (turnir tezroq o'tishi uchun)

# Tur ochilgandan (01:00) so'ng hisob kiritish uchun kutish vaqti (daqiqa).
# O'yinchilar o'ynashga ulgurishi va o'ynalmagan o'yinga darrov yolg'on natija
# kiritilmasligi uchun. 1 soat 45 daqiqa = 105 daqiqa → 02:45 dan keyin ochiladi.
RESULT_ENTRY_DELAY_MINUTES = 105

# Deadline (keyingi tur ochilishi, 01:00) ga shuncha daqiqa qolganda hisob kiritish
# VA rad etish yopiladi. O'rtacha o'yin 8-15 daq davom etgani uchun, oxirgi 15 daqiqada
# yangi o'yin boshlab/rad etib bo'lmaydi. 00:45 dan keyin: kiritish yo'q, rad yo'q.
ENTRY_CUTOFF_BEFORE_DEADLINE_MINUTES = 15

# === Liga nomlari ===
LEAGUE_LALIGA = "LaLiga"
LEAGUE_PREMIER = "Premier Liga"
AVAILABLE_LEAGUES = [LEAGUE_LALIGA, LEAGUE_PREMIER]

# === Liga holatlari (status) ===
LEAGUE_STATUS_OPEN = "open"               # Ro'yxatdan o'tish ochiq
LEAGUE_STATUS_IN_PROGRESS = "in_progress"  # Turnir boshlangan
LEAGUE_STATUS_FINISHED = "finished"        # Turnir tugagan

# === Match holatlari (status) ===
MATCH_STATUS_PENDING = "pending"                          # Hali o'ynalmagan
MATCH_STATUS_AWAITING_CONFIRMATION = "awaiting_confirmation"  # Natija kiritilgan, tasdiq kutilmoqda
MATCH_STATUS_CONFIRMED = "confirmed"                      # Ikkala tomon tasdiqlagan
MATCH_STATUS_REJECTED = "rejected"                        # Natija rad etilgan

# === Tillar ===
LANGUAGE_UZ = "uz"
LANGUAGE_RU = "ru"
LANGUAGE_EN = "en"
AVAILABLE_LANGUAGES = [LANGUAGE_UZ, LANGUAGE_RU, LANGUAGE_EN]
DEFAULT_LANGUAGE = LANGUAGE_UZ

# === Ma'lumotlar bazasi ===
DB_PATH = os.getenv("DB_PATH", "efootball_bot.db")

# === Validatsiya ===
# Bitta o'yinda kiritilishi mumkin bo'lgan maksimal gol soni (real 8-daqiqalik
# o'yin uchun yetarli; noto'g'ri/zararli kiritishdan himoya)
MAX_SCORE = int(os.getenv("MAX_SCORE", "30"))

# === IP darajasidagi rate-limit (auth'siz endpointlar uchun ham) ===
# Bitta IP'dan 10 sekundda maksimal so'rovlar soni. /webapp statik fayllar
# hisobga olinmaydi. Oddiy foydalanish (chat polling ~15 so'rov/10s) bemalol
# sig'adi; skript/flood 429 oladi.
IP_RATE_LIMIT_MAX = int(os.getenv("IP_RATE_LIMIT_MAX", "120"))
IP_RATE_LIMIT_WINDOW = 10  # sekund

# === Mavsum yakunlash himoyasi ===
# "Mavsumni yakunlash" tugmasi takror bosilsa (yoki so'rov qayta yuborilsa),
# shu soniya ichida ikkinchi yakunlash rad etiladi (audit A3, qoida #38).
# Haqiqiy keyingi mavsum yakunlashi haftalar keyin bo'ladi — 5 daqiqa yetarli.
SEASON_FINALIZE_COOLDOWN_SECONDS = int(os.getenv("SEASON_FINALIZE_COOLDOWN_SECONDS", "300"))

# === Katta hisob (score farming) himoyasi ===
# Bir tomon shu qiymatdan KO'P gol kiritsa (masalan 20:0), natija darhol
# tasdiqlanmaydi — 'admin_pending' holatiga tushadi va bosh admin tasdig'ini kutadi.
# 0..MAX_NORMAL_SCORE oralig'idagi hisoblar oddiy oqim (raqib tasdig'i) bilan o'tadi.
# Maqsad: oltin to'p/butsa reytingini soxta katta hisoblar bilan shishirishni to'xtatish.
MAX_NORMAL_SCORE = int(os.getenv("MAX_NORMAL_SCORE", "5"))

# === Profil rasm proxy keshi ===
# /players/{id}/photo har chaqiriqda Telegram API'ga 3 tagacha so'rov qilardi —
# kesh bot tokenining Telegram limitini himoya qiladi (audit A4).
PHOTO_CACHE_TTL_SECONDS = int(os.getenv("PHOTO_CACHE_TTL_SECONDS", "600"))   # topilgan rasm
PHOTO_CACHE_NEGATIVE_TTL_SECONDS = 60   # rasm yo'q/maxfiy holat qisqa keshlanadi
PHOTO_CACHE_MAX_ENTRIES = 500           # xotira o'smasligi uchun yuqori chegara

# === WebApp ===
# ⚠️ PLACEHOLDER — WebApp hostingga joylashgach, haqiqiy URL bilan almashtirilishi kerak
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com/webapp")

# === Sovrinlar ===
PRIZE_TOP_SCORER = "golden_boot"   # Eng ko'p gol urgan — Oltin Butsa
PRIZE_WINNER = "golden_ball"       # Turnir g'olibi — Oltin To'p znachogi

# === Adminlar ===
# Shu Telegram ID'lar WebApp'da admin paneliga kira oladi (bosh admin).
# Env'dan o'qiladi (qoida #46): ADMIN_TELEGRAM_IDS="6829293074" yoki
# vergul bilan bir nechta: "111,222". Env yo'q bo'lsa joriy qiymat ishlaydi
# (mavjud deploy buzilmasligi uchun).
_admin_ids_raw = os.getenv("ADMIN_TELEGRAM_IDS", "6829293074")
ADMIN_TELEGRAM_IDS = [int(x) for x in _admin_ids_raw.replace(" ", "").split(",") if x]

# === Majburiy kanal a'zoligi ===
# Foydalanuvchi botdan/WebApp'dan foydalanish uchun shu kanalga a'zo bo'lishi shart.
# ⚠️ Bot shu kanalda ADMIN bo'lishi kerak — aks holda getChatMember ishlamaydi.
REQUIRED_CHANNEL_USERNAME = os.getenv("REQUIRED_CHANNEL_USERNAME", "@efootball_liga_turnir")
REQUIRED_CHANNEL_URL = os.getenv("REQUIRED_CHANNEL_URL", "https://t.me/efootball_liga_turnir")
# A'zolikni majburiy qilishni o'chirish/yoqish (test uchun False qilish mumkin)
REQUIRE_CHANNEL_MEMBERSHIP = os.getenv("REQUIRE_CHANNEL_MEMBERSHIP", "true").lower() == "true"
