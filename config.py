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

# === Sovrinlar ===
PRIZE_TOP_SCORER = "golden_boot"   # Eng ko'p gol urgan — Oltin Butsa
PRIZE_WINNER = "golden_ball"       # Turnir g'olibi — Oltin To'p znachogi
