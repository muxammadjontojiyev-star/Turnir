"""
texts.py — Barcha foydalanuvchiga ko'rinadigan matnlar, 3 tilda (UZ/RU/EN).

QOIDA: Yangi matn kerak bo'lganda — shu faylga TEXTS dict'iga qo'shiladi,
handlerlarda hardcode string yozilmaydi.

Ishlatilishi:
    from texts import t
    t("menu_main", language)
"""

from config import LANGUAGE_UZ, LANGUAGE_RU, LANGUAGE_EN

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
    "enter_webapp": {
        LANGUAGE_UZ: "🚀 Kirish",
        LANGUAGE_RU: "🚀 Войти",
        LANGUAGE_EN: "🚀 Enter",
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

    # === Inline bildirishnomalar (bot orqali yuboriladi) ===
    "notify_draw_done": {
        LANGUAGE_UZ: "🎲 Qur'a tashlandi! \"{league}\" ligasida turnir boshlandi. O'yinlaringizni ko'rish va natija kiritish uchun ilovaga kiring.",
        LANGUAGE_RU: "🎲 Жребий проведён! В лиге \"{league}\" турнир начался. Откройте приложение, чтобы посмотреть свои матчи и внести результаты.",
        LANGUAGE_EN: "🎲 The draw is done! The tournament has started in the \"{league}\" league. Open the app to see your matches and submit results.",
    },
    "notify_result_submitted": {
        LANGUAGE_UZ: "📝 Natija kiritildi, tasdiqlaysizmi? Ilovaga kirib o'yin natijasini tasdiqlang yoki rad eting.",
        LANGUAGE_RU: "📝 Результат внесён, подтверждаете? Откройте приложение, чтобы подтвердить или отклонить результат матча.",
        LANGUAGE_EN: "📝 A result was submitted, do you confirm? Open the app to confirm or reject the match result.",
    },
    "notify_matchday_open": {
        LANGUAGE_UZ: "⚽️ {matchday}-tur ochildi! Bugungi o'yiningizni o'ynab, natijani ilovaga kiriting. Keyingi tur ertaga soat 01:00 da ochiladi.",
        LANGUAGE_RU: "⚽️ Тур {matchday} открыт! Сыграйте сегодняшний матч и внесите результат в приложение. Следующий тур откроется завтра в 01:00.",
        LANGUAGE_EN: "⚽️ Matchday {matchday} is open! Play today's match and submit the result in the app. The next matchday opens tomorrow at 01:00.",
    },
    "notify_deadline_soon": {
        LANGUAGE_UZ: "⏰ Diqqat! {league} ligasida deadline'ga 1 soat qoldi (01:00). O'yiningizni o'ynab, natijani kiritib ulguring. 00:45 dan keyin natija kiritish yopiladi!",
        LANGUAGE_RU: "⏰ Внимание! В лиге {league} до дедлайна 1 час (01:00). Успейте сыграть и внести результат. После 00:45 ввод результата закроется!",
        LANGUAGE_EN: "⏰ Heads up! 1 hour left until the deadline in {league} (01:00). Play your match and submit the result in time. Entry closes after 00:45!",
    },

    # === Majburiy kanal a'zoligi ===
    "subscribe_required": {
        LANGUAGE_UZ: "📢 Botdan foydalanish uchun avval rasmiy kanalimizga a'zo bo'ling:",
        LANGUAGE_RU: "📢 Чтобы пользоваться ботом, сначала подпишитесь на наш канал:",
        LANGUAGE_EN: "📢 To use the bot, please subscribe to our channel first:",
    },
    "subscribe_button": {
        LANGUAGE_UZ: "📢 Kanalga a'zo bo'lish",
        LANGUAGE_RU: "📢 Подписаться на канал",
        LANGUAGE_EN: "📢 Subscribe to channel",
    },
    "subscribe_check_button": {
        LANGUAGE_UZ: "✅ A'zo bo'ldim, tekshirish",
        LANGUAGE_RU: "✅ Я подписался, проверить",
        LANGUAGE_EN: "✅ I subscribed, check",
    },
    "subscribe_not_yet": {
        LANGUAGE_UZ: "❌ Siz hali kanalga a'zo bo'lmadingiz. Iltimos, a'zo bo'lib qayta tekshiring.",
        LANGUAGE_RU: "❌ Вы ещё не подписались на канал. Пожалуйста, подпишитесь и проверьте снова.",
        LANGUAGE_EN: "❌ You haven't subscribed yet. Please subscribe and check again.",
    },
    "subscribe_success": {
        LANGUAGE_UZ: "✅ Rahmat! Endi botdan foydalanishingiz mumkin.",
        LANGUAGE_RU: "✅ Спасибо! Теперь вы можете пользоваться ботом.",
        LANGUAGE_EN: "✅ Thank you! Now you can use the bot.",
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
