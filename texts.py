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
    "notify_chat_message": {
        LANGUAGE_UZ: "💬 {mode} raqibingiz sizga xabar yubordi:\n«{preview}»\nJavob berish uchun ilovani oching.",
        LANGUAGE_RU: "💬 Ваш соперник ({mode}) отправил вам сообщение:\n«{preview}»\nОткройте приложение, чтобы ответить.",
        LANGUAGE_EN: "💬 Your {mode} opponent sent you a message:\n«{preview}»\nOpen the app to reply.",
    },
    # Xabar ostidagi "ilovani ochish" tugmasi (chat bildirishnomalari uchun)
    "btn_open_app": {
        LANGUAGE_UZ: "📲 Ilovani ochish",
        LANGUAGE_RU: "📲 Открыть приложение",
        LANGUAGE_EN: "📲 Open the app",
    },
    # Rejim nomlari — bildirishnomada qaysi turnirdan xabar kelgani ko'rinsin
    "mode_name_league": {
        LANGUAGE_UZ: "Liga",
        LANGUAGE_RU: "Лига",
        LANGUAGE_EN: "League",
    },
    "mode_name_worldcup": {
        LANGUAGE_UZ: "Jahon Chempionati",
        LANGUAGE_RU: "Чемпионат мира",
        LANGUAGE_EN: "World Cup",
    },
    "mode_name_cl": {
        LANGUAGE_UZ: "Chempionlar ligasi",
        LANGUAGE_RU: "Лига чемпионов",
        LANGUAGE_EN: "Champions League",
    },
    "mode_name_division": {
        LANGUAGE_UZ: "Divizion",
        LANGUAGE_RU: "Дивизион",
        LANGUAGE_EN: "Division",
    },
    "notify_matchday_open": {
        LANGUAGE_UZ: "⚽️ {matchday}-tur ochildi! Bugungi o'yiningizni o'ynab, natijani ilovaga kiriting. Keyingi tur ertaga soat 23:30 da ochiladi.",
        LANGUAGE_RU: "⚽️ Тур {matchday} открыт! Сыграйте сегодняшний матч и внесите результат в приложение. Следующий тур откроется завтра в 23:30.",
        LANGUAGE_EN: "⚽️ Matchday {matchday} is open! Play today's match and submit the result in the app. The next matchday opens tomorrow at 23:30.",
    },
    "notify_deadline_soon": {
        LANGUAGE_UZ: "⏰ Diqqat! {league} ligasida deadline'ga 1 soat qoldi (23:30). O'yiningizni o'ynab, natijani kiritib ulguring!",
        LANGUAGE_RU: "⏰ Внимание! В лиге {league} до дедлайна 1 час (23:30). Успейте сыграть и внести результат!",
        LANGUAGE_EN: "⏰ Heads up! 1 hour left until the deadline in {league} (23:30). Play your match and submit the result in time!",
    },
    "notify_div_pair": {
        LANGUAGE_UZ: "🎲 Divizion qur'asi: bugungi raqibingiz — {opponent}. O'yinni o'ynab, natijani ilovaga 23:30 gacha kiriting!",
        LANGUAGE_RU: "🎲 Жеребьёвка дивизиона: ваш соперник сегодня — {opponent}. Сыграйте матч и внесите результат до 23:30!",
        LANGUAGE_EN: "🎲 Division draw: your opponent today is {opponent}. Play the match and submit the result by 23:30!",
    },
    "notify_div_reg_open": {
        LANGUAGE_UZ: "📝 Divizionda ro'yxatdan o'tish OCHILDI! Har kuni 17:00–19:00 (Toshkent) oralig'ida ro'yxatdan o'tishingiz mumkin. Qur'a 19:00 dan keyin o'tkaziladi. Qatnashish uchun ilovaga kiring! ⚽",
        LANGUAGE_RU: "📝 Регистрация в дивизионе ОТКРЫТА! Записаться можно каждый день с 17:00 до 19:00 (Ташкент). Жеребьёвка — после 19:00. Заходите в приложение, чтобы участвовать! ⚽",
        LANGUAGE_EN: "📝 Division registration is OPEN! You can sign up every day between 17:00–19:00 (Tashkent). The draw takes place after 19:00. Open the app to join! ⚽",
    },
    "notify_div_ban": {
        LANGUAGE_UZ: "🚫 Siz Divizionda qoidabuzarlik uchun {days} kunlik BAN oldingiz. {until} sanasigacha (shu kun ham kiradi) Divizion ro'yxatidan o'ta olmaysiz.",
        LANGUAGE_RU: "🚫 Вы получили БАН в дивизионе на {days} дн. за нарушение правил. До {until} (включительно) вы не сможете зарегистрироваться в дивизионе.",
        LANGUAGE_EN: "🚫 You have been BANNED from the Division for {days} day(s) due to a rules violation. You cannot register in the Division until {until} (inclusive).",
    },
    "notify_div_bye": {
        LANGUAGE_UZ: "🎲 Divizion qur'asi: bugun ishtirokchilar soni toq bo'lgani uchun sizga AVTOMATIK G'ALABA (+15 achko) berildi! 🎉",
        LANGUAGE_RU: "🎲 Жеребьёвка дивизиона: сегодня нечётное число участников — вам присуждена АВТОМАТИЧЕСКАЯ ПОБЕДА (+15 очков)! 🎉",
        LANGUAGE_EN: "🎲 Division draw: odd number of participants today — you get an AUTOMATIC WIN (+15 points)! 🎉",
    },
    "div_rules_list": {
        LANGUAGE_UZ: [
            "Har kuni **17:00–19:00** (Toshkent) oralig'ida ro'yxatdan o'tiladi.",
            "Ro'yxat yopilgach bot ishtirokchilarni **qur'a** orqali juftlaydi.",
            "Raqibingiz **profil** bo'limida va telegram xabarida ko'rinadi.",
            "O'yin natijasini **23:30** gacha kiritib, raqib tasdiqlashi kerak.",
            "Belgilangan vaqtgacha o'ynalmagan o'yin **0:0 durang** bo'ladi.",
            "Ishtirokchilar toq bo'lsa, bittasiga **avtomatik g'alaba** beriladi.",
            "G'alaba **+15**, durang **+10**, mag'lubiyat **−10** achko.",
            "Ko'p achko to'plagan ishtirokchi **reyting**da yuqoriga ko'tariladi.",
        ],
        LANGUAGE_RU: [
            "Каждый день регистрация с **17:00 до 19:00** (Ташкент).",
            "После закрытия регистрации бот проводит **жеребьёвку** пар.",
            "Соперник виден в разделе **профиль** и в сообщении telegram.",
            "Результат нужно внести до **23:30**, соперник подтверждает.",
            "Несыгранный вовремя матч засчитывается как **ничья 0:0**.",
            "При нечётном числе участников одному даётся **автопобеда**.",
            "Победа **+15**, ничья **+10**, поражение **−10** очков.",
            "Набравший больше очков поднимается выше в **рейтинге**.",
        ],
        LANGUAGE_EN: [
            "Registration is open daily from **17:00 to 19:00** (Tashkent).",
            "After registration closes, the bot **pairs** players by draw.",
            "Your opponent appears in the **profile** tab and a telegram message.",
            "Submit the result by **23:30**; the opponent must confirm it.",
            "A match not played in time is scored as a **0:0 draw**.",
            "With an odd number of players, one gets an **automatic win**.",
            "Win **+15**, draw **+10**, loss **−10** points.",
            "Players with more points rise higher in the **rating**.",
        ],
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
