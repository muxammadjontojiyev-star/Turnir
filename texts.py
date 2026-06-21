"""
texts.py — Barcha foydalanuvchiga ko'rinadigan matnlar, 3 tilda (UZ/RU/EN).

QOIDA: Yangi matn kerak bo'lganda — shu faylga TEXTS dict'iga qo'shiladi,
handlerlarda hardcode string yozilmaydi.

Ishlatilishi:
    from bot.texts import t
    t("menu_main", language)
"""

from bot.config import LANGUAGE_UZ, LANGUAGE_RU, LANGUAGE_EN

TEXTS = {
    # === Pastki asosiy tugmalar (4 ta) ===
    "menu_main": {
        LANGUAGE_UZ: "🏠 Asosiy",
        LANGUAGE_RU: "🏠 Главная",
        LANGUAGE_EN: "🏠 Main",
    },
    "menu_rating": {
        LANGUAGE_UZ: "🏆 Reyting",
        LANGUAGE_RU: "🏆 Рейтинг",
        LANGUAGE_EN: "🏆 Rating",
    },
    "menu_profile": {
        LANGUAGE_UZ: "👤 Profil",
        LANGUAGE_RU: "👤 Профиль",
        LANGUAGE_EN: "👤 Profile",
    },
    "menu_prizes": {
        LANGUAGE_UZ: "🎁 Sovrinlar",
        LANGUAGE_RU: "🎁 Призы",
        LANGUAGE_EN: "🎁 Prizes",
    },

    # === Umumiy / start ===
    "welcome": {
        LANGUAGE_UZ: "Assalomu alaykum! eFootball turnir botiga xush kelibsiz ⚽️",
        LANGUAGE_RU: "Здравствуйте! Добро пожаловать в турнирного бота eFootball ⚽️",
        LANGUAGE_EN: "Hello! Welcome to the eFootball tournament bot ⚽️",
    },
    "choose_language": {
        LANGUAGE_UZ: "Tilni tanlang:",
        LANGUAGE_RU: "Выберите язык:",
        LANGUAGE_EN: "Choose a language:",
    },
    "language_changed": {
        LANGUAGE_UZ: "Til muvaffaqiyatli o'zgartirildi ✅",
        LANGUAGE_RU: "Язык успешно изменён ✅",
        LANGUAGE_EN: "Language changed successfully ✅",
    },

    # === Asosiy bo'lim ===
    "tournament_info": {
        LANGUAGE_UZ: "Joriy turnir haqida ma'lumot",
        LANGUAGE_RU: "Информация о текущем турнире",
        LANGUAGE_EN: "Current tournament information",
    },
    "register_button": {
        LANGUAGE_UZ: "📝 Ro'yxatdan o'tish",
        LANGUAGE_RU: "📝 Регистрация",
        LANGUAGE_EN: "📝 Register",
    },
    "rules_button": {
        LANGUAGE_UZ: "📖 Qoidalar",
        LANGUAGE_RU: "📖 Правила",
        LANGUAGE_EN: "📖 Rules",
    },
    "announcements_button": {
        LANGUAGE_UZ: "📢 E'lonlar",
        LANGUAGE_RU: "📢 Объявления",
        LANGUAGE_EN: "📢 Announcements",
    },

    # === Ro'yxatdan o'tish natijalari ===
    "registration_success": {
        LANGUAGE_UZ: "Siz muvaffaqiyatli ro'yxatdan o'tdingiz! ✅",
        LANGUAGE_RU: "Вы успешно зарегистрированы! ✅",
        LANGUAGE_EN: "You have successfully registered! ✅",
    },
    "registration_already_registered": {
        LANGUAGE_UZ: "Siz allaqachon bir ligaga ro'yxatdan o'tgansiz.",
        LANGUAGE_RU: "Вы уже зарегистрированы в одной из лиг.",
        LANGUAGE_EN: "You are already registered in a league.",
    },
    "registration_league_full": {
        LANGUAGE_UZ: "Afsuski, bu liga to'lib bo'ldi (20/20).",
        LANGUAGE_RU: "К сожалению, эта лига заполнена (20/20).",
        LANGUAGE_EN: "Sorry, this league is full (20/20).",
    },

    # === Reyting bo'limi ===
    "rating_overall": {
        LANGUAGE_UZ: "Umumiy reyting jadvali",
        LANGUAGE_RU: "Общая таблица рейтинга",
        LANGUAGE_EN: "Overall rating table",
    },
    "rating_current_league": {
        LANGUAGE_UZ: "Joriy turnir reytingi",
        LANGUAGE_RU: "Рейтинг текущего турнира",
        LANGUAGE_EN: "Current tournament rating",
    },
    "rating_winners_history": {
        LANGUAGE_UZ: "G'oliblar tarixi",
        LANGUAGE_RU: "История победителей",
        LANGUAGE_EN: "Winners history",
    },

    # === Profil bo'limi ===
    "profile_my_position": {
        LANGUAGE_UZ: "Mening reyting o'rnim",
        LANGUAGE_RU: "Моё место в рейтинге",
        LANGUAGE_EN: "My rating position",
    },
    "profile_my_matches": {
        LANGUAGE_UZ: "O'tgan o'yinlarim tarixi",
        LANGUAGE_RU: "История моих матчей",
        LANGUAGE_EN: "My match history",
    },
    "profile_edit_nickname": {
        LANGUAGE_UZ: "Ism/nickname tahrirlash",
        LANGUAGE_RU: "Изменить имя/никнейм",
        LANGUAGE_EN: "Edit name/nickname",
    },
    "profile_my_stats": {
        LANGUAGE_UZ: "Mening statistikam",
        LANGUAGE_RU: "Моя статистика",
        LANGUAGE_EN: "My statistics",
    },

    # === Sovrinlar bo'limi ===
    "prize_top_scorer": {
        LANGUAGE_UZ: "🥇 Eng ko'p gol urgan ishtirokchiga — Oltin Butsa",
        LANGUAGE_RU: "🥇 Игроку с наибольшим числом голов — Золотая бутса",
        LANGUAGE_EN: "🥇 Top goal scorer — Golden Boot",
    },
    "prize_winner": {
        LANGUAGE_UZ: "🏆 Turnir g'olibiga — Oltin To'p znachogi",
        LANGUAGE_RU: "🏆 Победителю турнира — значок Золотой мяч",
        LANGUAGE_EN: "🏆 Tournament winner — Golden Ball badge",
    },
}


def t(key: str, language: str) -> str:
    """
    Berilgan kalit va til uchun matnni qaytaradi.

    Agar til topilmasa — UZ (default) qaytariladi.
    Agar kalit topilmasa — kalitning o'zi qaytariladi (xato sezilishi uchun).
    """
    entry = TEXTS.get(key)
    if entry is None:
        return key
    return entry.get(language, entry.get(LANGUAGE_UZ, key))
