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
    # 2026-08-28: eFootball xona ID si — kod BILDIRISHNOMANING O'ZIDA ko'rinadi,
    # raqib ilovani ochmasdan nusxa ola oladi (maqsad: qadamni kamaytirish)
    "notify_room_code": {
        LANGUAGE_UZ: "🎮 {mode} raqibingiz xona ochdi.\nXona ID: {code}\nO'yinga kiring va natijani ilovada tasdiqlang.",
        LANGUAGE_RU: "🎮 Ваш соперник ({mode}) создал комнату.\nID комнаты: {code}\nЗайдите в игру и подтвердите результат в приложении.",
        LANGUAGE_EN: "🎮 Your {mode} opponent created a room.\nRoom ID: {code}\nJoin the match and confirm the result in the app.",
    },
    # Xabar ostidagi "ilovani ochish" tugmasi (chat bildirishnomalari uchun)
    # 2026-10-02: shaxsiy turnir to'lovi
    "pt_notify_receipt_admin": {
        LANGUAGE_UZ: "💳 Yangi to'lov cheki\nTurnir: «{name}» (#{id})\nTashkilotchi: {owner}\nSumma: {price} so'm\nTekshirish uchun ilovani oching: Shaxsiy turnirlar → To'lovlar.",
        LANGUAGE_RU: "💳 Новый чек оплаты\nТурнир: «{name}» (#{id})\nОрганизатор: {owner}\nСумма: {price} сум\nОткройте приложение: Частные турниры → Платежи.",
        LANGUAGE_EN: "💳 New payment receipt\nTournament: «{name}» (#{id})\nOrganizer: {owner}\nAmount: {price} UZS\nOpen the app: Private tournaments → Payments.",
    },
    "pt_notify_approved": {
        LANGUAGE_UZ: "✅ «{name}» turniri uchun to'lovingiz tasdiqlandi! Endi ishtirokchilarni taklif qilishingiz mumkin.",
        LANGUAGE_RU: "✅ Оплата турнира «{name}» подтверждена! Теперь можно приглашать участников.",
        LANGUAGE_EN: "✅ Payment for «{name}» has been approved! You can now invite players.",
    },
    "pt_notify_rejected": {
        LANGUAGE_UZ: "❌ «{name}» turniri uchun to'lov rad etildi.\nSabab: {reason}\nChekni qayta yuborishingiz mumkin.",
        LANGUAGE_RU: "❌ Оплата турнира «{name}» отклонена.\nПричина: {reason}\nВы можете отправить чек повторно.",
        LANGUAGE_EN: "❌ Payment for «{name}» was rejected.\nReason: {reason}\nYou can send the receipt again.",
    },
    # 2026-10-02: shaxsiy turnirga qo'shilish (3-bosqich)
    "pt_notify_join_request": {
        LANGUAGE_UZ: "🙋 {who} «{name}» turniringizga qo'shilmoqchi. Tasdiqlash uchun ilovani oching.",
        LANGUAGE_RU: "🙋 {who} хочет присоединиться к турниру «{name}». Откройте приложение, чтобы подтвердить.",
        LANGUAGE_EN: "🙋 {who} wants to join your tournament «{name}». Open the app to approve.",
    },
    "pt_notify_join_approved": {
        LANGUAGE_UZ: "✅ Siz «{name}» turniriga qabul qilindingiz!",
        LANGUAGE_RU: "✅ Вас приняли в турнир «{name}»!",
        LANGUAGE_EN: "✅ You've been accepted into «{name}»!",
    },
    "pt_notify_added": {
        LANGUAGE_UZ: "🏆 Sizni «{name}» shaxsiy turniriga qo'shishdi!",
        LANGUAGE_RU: "🏆 Вас добавили в частный турнир «{name}»!",
        LANGUAGE_EN: "🏆 You've been added to the private tournament «{name}»!",
    },
    "pt_notify_removed": {
        LANGUAGE_UZ: "«{name}» turniri tashkilotchisi sizning ishtirokingizni bekor qildi.",
        LANGUAGE_RU: "Организатор турнира «{name}» отменил ваше участие.",
        LANGUAGE_EN: "The organizer of «{name}» has cancelled your participation.",
    },
    "pt_invite_message": {
        LANGUAGE_UZ: "🏆 Sizni «{name}» shaxsiy turniriga taklif qilishdi!\nTashkilotchi: {owner}\nQo'shilish uchun quyidagi tugmani bosing.",
        LANGUAGE_RU: "🏆 Вас пригласили в частный турнир «{name}»!\nОрганизатор: {owner}\nНажмите кнопку ниже, чтобы присоединиться.",
        LANGUAGE_EN: "🏆 You've been invited to the private tournament «{name}»!\nOrganizer: {owner}\nTap the button below to join.",
    },
    "pt_invite_invalid": {
        LANGUAGE_UZ: "❌ Taklif havolasi yaroqsiz yoki turnir topilmadi.",
        LANGUAGE_RU: "❌ Ссылка-приглашение недействительна или турнир не найден.",
        LANGUAGE_EN: "❌ The invite link is invalid or the tournament was not found.",
    },
    "pt_invite_button": {
        LANGUAGE_UZ: "🏆 Turnirni ko'rish",
        LANGUAGE_RU: "🏆 Открыть турнир",
        LANGUAGE_EN: "🏆 View tournament",
    },
    # 2026-10-02: shaxsiy turnir o'yinlari (4-bosqich)
    "pt_notify_started": {
        LANGUAGE_UZ: "🏁 «{name}» turniri boshlandi! Siz {group}-guruhdasiz. O'yinlaringizni ilovada ko'ring.",
        LANGUAGE_RU: "🏁 Турнир «{name}» начался! Вы в группе {group}. Смотрите свои матчи в приложении.",
        LANGUAGE_EN: "🏁 «{name}» has started! You're in group {group}. See your matches in the app.",
    },
    "pt_notify_deleted": {
        LANGUAGE_UZ: "🗑 «{name}» turniri tashkilotchi tomonidan o'chirildi.",
        LANGUAGE_RU: "🗑 Турнир «{name}» удалён организатором.",
        LANGUAGE_EN: "🗑 The «{name}» tournament was deleted by the organizer.",
    },
    # 2026-10-07: yagona jadvalli formatlar (liga / ChL / YeL)
    "pt_notify_started_table": {
        LANGUAGE_UZ: "🏁 «{name}» turniri boshlandi! Jadval {rounds} turdan iborat. O'yinlaringizni ilovada ko'ring.",
        LANGUAGE_RU: "🏁 Турнир «{name}» начался! В таблице {rounds} туров. Смотрите свои матчи в приложении.",
        LANGUAGE_EN: "🏁 «{name}» has started! The table has {rounds} rounds. See your matches in the app.",
    },
    "pt_notify_table_done": {
        LANGUAGE_UZ: "🏁 «{name}»: liga bosqichi yakunlandi! Jadval va pley-off juftliklarini ilovada ko'ring.",
        LANGUAGE_RU: "🏁 «{name}»: общий этап завершён! Таблица и пары плей-офф — в приложении.",
        LANGUAGE_EN: "🏁 «{name}»: the league phase is over! See the table and play-off pairs in the app.",
    },
    "pt_notify_round_open": {
        LANGUAGE_UZ: "⏰ «{name}»: {round}-tur o'yinlarini {deadline} gacha (Toshkent vaqti) o'ynang.",
        LANGUAGE_RU: "⏰ «{name}»: сыграйте матчи {round}-го тура до {deadline} (по Ташкенту).",
        LANGUAGE_EN: "⏰ «{name}»: play your round {round} matches by {deadline} (Tashkent time).",
    },
    "pt_notify_round_closed": {
        LANGUAGE_UZ: "✅ «{name}»: {round}-tur yopildi. {next}-tur ochildi.",
        LANGUAGE_RU: "✅ «{name}»: {round}-й тур завершён. Открыт {next}-й тур.",
        LANGUAGE_EN: "✅ «{name}»: round {round} is closed. Round {next} is open.",
    },
    "pt_notify_groups_done": {
        LANGUAGE_UZ: "🏁 «{name}»: guruh bosqichi yakunlandi! Jadvallarni ilovada ko'ring.",
        LANGUAGE_RU: "🏁 «{name}»: групповой этап завершён! Смотрите таблицы в приложении.",
        LANGUAGE_EN: "🏁 «{name}»: the group stage is over! See the tables in the app.",
    },
    # 2026-10-02: shaxsiy turnir pley-offi (5-bosqich)
    "pt_notify_ko_start": {
        LANGUAGE_UZ: "⚔️ «{name}»: pley-off boshlandi — {stage}.\nSizning juftligingiz va setka ilovada. Durang yo'q — penalti o'yin ichida.",
        LANGUAGE_RU: "⚔️ «{name}»: начался плей-офф — {stage}.\nВаша пара и сетка в приложении. Ничьих нет — пенальти внутри матча.",
        LANGUAGE_EN: "⚔️ «{name}»: the play-off has started — {stage}.\nYour pairing and the bracket are in the app. No draws — penalties in the match.",
    },
    "pt_notify_next_stage": {
        LANGUAGE_UZ: "➡️ «{name}»: {stage} juftliklari tayyor. O'yiningizni ilovada ko'ring.",
        LANGUAGE_RU: "➡️ «{name}»: пары стадии «{stage}» готовы. Смотрите свой матч в приложении.",
        LANGUAGE_EN: "➡️ «{name}»: the {stage} pairs are ready. See your match in the app.",
    },
    "pt_notify_final": {
        LANGUAGE_UZ: "🏟 «{name}» FINALI: {p1} — {p2}!",
        LANGUAGE_RU: "🏟 ФИНАЛ «{name}»: {p1} — {p2}!",
        LANGUAGE_EN: "🏟 «{name}» FINAL: {p1} — {p2}!",
    },
    "pt_notify_champion": {
        LANGUAGE_UZ: "🏆 «{name}» chempioni — {champion}! Tabriklaymiz!",
        LANGUAGE_RU: "🏆 Чемпион «{name}» — {champion}! Поздравляем!",
        LANGUAGE_EN: "🏆 The «{name}» champion is {champion}! Congratulations!",
    },
    "pt_notify_ko_deadline": {
        LANGUAGE_UZ: "⏰ «{name}»: {stage} o'yinini {deadline} gacha (Toshkent vaqti) o'ynang.",
        LANGUAGE_RU: "⏰ «{name}»: сыграйте матч ({stage}) до {deadline} (по Ташкенту).",
        LANGUAGE_EN: "⏰ «{name}»: play your {stage} match by {deadline} (Tashkent time).",
    },
    "pt_notify_ko_pending": {
        LANGUAGE_UZ: "⚠️ «{name}»: pley-off muddati o'tdi, {count} ta o'yin o'ynalmagan. Natijani ilovada «Natijani tuzatish» orqali hal qiling.",
        LANGUAGE_RU: "⚠️ «{name}»: срок плей-офф истёк, не сыграно матчей: {count}. Решите результат в приложении («Исправить результат»).",
        LANGUAGE_EN: "⚠️ «{name}»: the play-off deadline passed, {count} match(es) unplayed. Decide the result in the app («Fix a result»).",
    },
    "pt_stage_po": {LANGUAGE_UZ: "pley-off raundi", LANGUAGE_RU: "раунд плей-офф", LANGUAGE_EN: "knockout round play-off"},
    "pt_stage_r64": {LANGUAGE_UZ: "1/32 final", LANGUAGE_RU: "1/32 финала", LANGUAGE_EN: "round of 64"},
    "pt_stage_r32": {LANGUAGE_UZ: "1/16 final", LANGUAGE_RU: "1/16 финала", LANGUAGE_EN: "round of 32"},
    "pt_stage_r16": {LANGUAGE_UZ: "1/8 final", LANGUAGE_RU: "1/8 финала", LANGUAGE_EN: "round of 16"},
    "pt_stage_qf": {LANGUAGE_UZ: "1/4 final", LANGUAGE_RU: "1/4 финала", LANGUAGE_EN: "quarter-final"},
    "pt_stage_semi": {LANGUAGE_UZ: "yarim final", LANGUAGE_RU: "полуфинал", LANGUAGE_EN: "semi-final"},
    "pt_stage_final": {LANGUAGE_UZ: "final", LANGUAGE_RU: "финал", LANGUAGE_EN: "final"},
    # 2026-10-03: shaxsiy turnir obunalari
    "pt_plan_week": {LANGUAGE_UZ: "haftalik", LANGUAGE_RU: "недельная", LANGUAGE_EN: "weekly"},
    "pt_plan_month": {LANGUAGE_UZ: "oylik", LANGUAGE_RU: "месячная", LANGUAGE_EN: "monthly"},
    "pt_plan_year": {LANGUAGE_UZ: "yillik", LANGUAGE_RU: "годовая", LANGUAGE_EN: "yearly"},
    "pt_notify_sub_receipt_admin": {
        LANGUAGE_UZ: "💳 Obuna to'lovi cheki\nTarif: {plan} (#{id})\nFoydalanuvchi: {owner}\nSumma: {price} so'm\nIlovada: Shaxsiy turnirlar → To'lovlar.",
        LANGUAGE_RU: "💳 Чек оплаты подписки\nТариф: {plan} (#{id})\nПользователь: {owner}\nСумма: {price} сум\nВ приложении: Частные турниры → Платежи.",
        LANGUAGE_EN: "💳 Subscription payment receipt\nPlan: {plan} (#{id})\nUser: {owner}\nAmount: {price} UZS\nIn the app: Private tournaments → Payments.",
    },
    "pt_notify_sub_approved": {
        LANGUAGE_UZ: "✅ {plan} obunangiz faollashtirildi! Amal qilish muddati: {until} gacha. Endi turnirlarni to'lovsiz yaratishingiz mumkin.",
        LANGUAGE_RU: "✅ Ваша {plan} подписка активирована! Действует до {until}. Теперь турниры создаются без оплаты.",
        LANGUAGE_EN: "✅ Your {plan} subscription is active until {until}. You can now create tournaments without paying.",
    },
    "pt_notify_sub_rejected": {
        LANGUAGE_UZ: "❌ {plan} obuna to'lovi rad etildi.\nSabab: {reason}\nChekni qayta yuborishingiz mumkin.",
        LANGUAGE_RU: "❌ Оплата подписки ({plan}) отклонена.\nПричина: {reason}\nВы можете отправить чек повторно.",
        LANGUAGE_EN: "❌ The {plan} subscription payment was rejected.\nReason: {reason}\nYou can send the receipt again.",
    },
    "pt_notify_admin_added": {
        LANGUAGE_UZ: "🛡 Sizni «{name}» shaxsiy turniriga ADMIN qilib tayinlashdi. Endi a'zolar, muddatlar va natijalarni boshqarishingiz mumkin.",
        LANGUAGE_RU: "🛡 Вас назначили АДМИНОМ частного турнира «{name}». Теперь вы можете управлять участниками, сроками и результатами.",
        LANGUAGE_EN: "🛡 You've been made an ADMIN of the private tournament «{name}». You can now manage players, deadlines and results.",
    },
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
    "mode_name_el": {
        LANGUAGE_UZ: "Yevropa ligasi",
        LANGUAGE_RU: "Лига Европы",
        LANGUAGE_EN: "Europa League",
    },
    "mode_name_pt": {
        LANGUAGE_UZ: "Shaxsiy turnir",
        LANGUAGE_RU: "Частный турнир",
        LANGUAGE_EN: "Private tournament",
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
        LANGUAGE_UZ: "🎲 Divizion qur'asi: bugungi raqibingiz — {opponent}. O'yinni o'ynab, natijani ilovaga 16:00 gacha kiriting!",
        LANGUAGE_RU: "🎲 Жеребьёвка дивизиона: ваш соперник сегодня — {opponent}. Сыграйте матч и внесите результат до 16:00!",
        LANGUAGE_EN: "🎲 Division draw: your opponent today is {opponent}. Play the match and submit the result by 16:00!",
    },
    "notify_div_reg_open": {
        LANGUAGE_UZ: "📝 Divizionda ro'yxatdan o'tish OCHILDI! Har kuni 17:00–20:00 (Toshkent) oralig'ida ro'yxatdan o'tishingiz mumkin. Qur'a 20:00 dan keyin o'tkaziladi. Qatnashish uchun ilovaga kiring! ⚽",
        LANGUAGE_RU: "📝 Регистрация в дивизионе ОТКРЫТА! Записаться можно каждый день с 17:00 до 20:00 (Ташкент). Жеребьёвка — после 20:00. Заходите в приложение, чтобы участвовать! ⚽",
        LANGUAGE_EN: "📝 Division registration is OPEN! You can sign up every day between 17:00–20:00 (Tashkent). The draw takes place after 20:00. Open the app to join! ⚽",
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
            "Har kuni **17:00–20:00** (Toshkent) oralig'ida ro'yxatdan o'tiladi.",
            "Ro'yxat yopilgach bot ishtirokchilarni **qur'a** orqali juftlaydi.",
            "Raqibingiz **profil** bo'limida va telegram xabarida ko'rinadi.",
            "O'yin natijasini **16:00** gacha kiritib, raqib tasdiqlashi kerak.",
            "Belgilangan vaqtgacha o'ynalmagan o'yin **0:0 durang** bo'ladi.",
            "Ishtirokchilar toq bo'lsa, bittasiga **avtomatik g'alaba** beriladi.",
            "G'alaba **+15**, durang **+10**, mag'lubiyat **−10** achko.",
            "Ko'p achko to'plagan ishtirokchi **reyting**da yuqoriga ko'tariladi.",
        ],
        LANGUAGE_RU: [
            "Каждый день регистрация с **17:00 до 20:00** (Ташкент).",
            "После закрытия регистрации бот проводит **жеребьёвку** пар.",
            "Соперник виден в разделе **профиль** и в сообщении telegram.",
            "Результат нужно внести до **16:00**, соперник подтверждает.",
            "Несыгранный вовремя матч засчитывается как **ничья 0:0**.",
            "При нечётном числе участников одному даётся **автопобеда**.",
            "Победа **+15**, ничья **+10**, поражение **−10** очков.",
            "Набравший больше очков поднимается выше в **рейтинге**.",
        ],
        LANGUAGE_EN: [
            "Registration is open daily from **17:00 to 20:00** (Tashkent).",
            "After registration closes, the bot **pairs** players by draw.",
            "Your opponent appears in the **profile** tab and a telegram message.",
            "Submit the result by **16:00**; the opponent must confirm it.",
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
