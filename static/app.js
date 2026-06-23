/**
 * app.js — eFootball Turnir WebApp
 * Init, til tizimi (UZ/RU/EN), navigatsiya, toast, eventlar.
 * api.js bilan birga ishlaydi — u APP global ob'ektidan foydalanadi.
 */

// ============================================================
//  SVG IKONLAR (premium, ingichka chiziqli — currentColor bilan ranglanadi)
//  Emoji o'rniga ishlatiladi. ICON.get("home") -> SVG matni.
// ============================================================

const ICON_PATHS = {
  // Navigatsiya
  home:    '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9.5 21v-6h5v6"/>',
  trophy:  '<path d="M7 4h10v4a5 5 0 0 1-10 0V4Z"/><path d="M7 6H4.5A1.5 1.5 0 0 0 3 7.5 3.5 3.5 0 0 0 6.5 11H7"/><path d="M17 6h2.5A1.5 1.5 0 0 1 21 7.5 3.5 3.5 0 0 1 17.5 11H17"/><path d="M9 14.5 8 21h8l-1-6.5"/><path d="M7 21h10"/>',
  user:    '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  gift:    '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v9h14v-9"/><path d="M12 8v13"/><path d="M12 8S10.5 3 8 3a2.5 2.5 0 0 0 0 5h4Z"/><path d="M12 8s1.5-5 4-5a2.5 2.5 0 0 1 0 5h-4Z"/>',
  // Sarlavha / holat
  clipboard:'<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3h6v1"/><path d="M9 10h6"/><path d="M9 14h6"/><path d="M9 18h4"/>',
  lock:    '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  unlock:  '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 7.5-2"/>',
  megaphone:'<path d="m3 11 13-6v14l-13-6Z"/><path d="M16 9a3 3 0 0 1 0 6"/><path d="M7 12.5V18a1 1 0 0 0 1 1h2"/>',
  dice:    '<rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="9" cy="9" r="1.1"/><circle cx="15" cy="15" r="1.1"/><circle cx="15" cy="9" r="1.1"/><circle cx="9" cy="15" r="1.1"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.3"/><path d="M21 4v5h-5"/>',
  recycle: '<path d="M7 19H5a2 2 0 0 1-1.7-3l2-3.3"/><path d="m9.5 4.5 1.5-2.5 1.5 2.5"/><path d="M11 2.5 14 8"/><path d="M17 19h2a2 2 0 0 0 1.7-3l-1.2-2"/><path d="m14 21-2.5-1.5L14 18"/>',
  chat:    '<path d="M4 5h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H9l-4 4v-4H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z"/>',
  back:    '<path d="M15 18l-6-6 6-6"/>',
  close:   '<path d="M6 6l12 12M18 6 6 18"/>',
  check:   '<path d="M5 12.5 10 17l9-10"/>',
  cross:   '<path d="M6 6l12 12M18 6 6 18"/>',
  play:    '<path d="M7 4v16l13-8L7 4Z"/>',
};

const ICON = {
  get(name, size = 24) {
    const p = ICON_PATHS[name];
    if (!p) return "";
    return `<svg class="icon icon--${name}" viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
  },
};

// ============================================================
//  GLOBAL STATE
// ============================================================

const APP = {
  currentUser:      null,   // Telegram foydalanuvchisi
  leagues:          [],     // /leagues javobi
  selectedLeagueId: null,   // Tanlangan liga
  selectedClub:     null,   // Tanlangan klub nomi
  selectedClubLogo: null,   // Tanlangan klub logo URL
  profileData:      null,   // /profile javobi
  activeMatchId:    null,   // Natija kiritish uchun
  adminResolveMatchId: null,  // Admin: rad etilgan natijani belgilash uchun
  ratingTab:        "league",  // Reyting bo'limidagi tab: "league" yoki "top_scorers"
  lang:             "uz",   // Joriy til
  t:                {},     // Aktiv tarjimalar
};

// ============================================================
//  I18N — 3 TILLI MATNLAR
// ============================================================

const TEXTS = {
  uz: {
    // Nav
    nav_home:    "Asosiy",
    nav_rating:  "Reyting",
    nav_profile: "Profil",
    nav_prizes:  "Sovrinlar",
    // Home
    players:         "O'yinchilar",
    max_players:     "Maksimal",
    matchday:        "Tur",
    season:          "Mavsum",
    register:        "Ro'yxatdan o'tish",
    choose_league:   "LIGA TANLASH",
    clubs_in_league: "LIGADAGI KLUBLAR",
    home_my_matches: "JORIY O'YINLARIM",
    select_club:     "Klub tanlang",
    already_in_season: "Siz bu mavsumda allaqachon ro'yxatdansiz",
    open:            "OCHIQ",
    full:            "TO'LIQ",
    league_locked_badge: "YOPIQ",
    league_locked_toast: "Bu liga hali yopiq. Avval oldingi liga to'lishi kerak.",
    league_open:     "OCHIQ — RO'YXAT DAVOM ETMOQDA",
    league_full:     "TO'LIQ",
    rules:           "Qoidalar",
    rules_list: [
      "O'yin 8 daqiqa davom etadi.",
      "Ikkitalik himoya yoqish mumkin emas.",
      "O'yinchilar holati \"Excellent\" bo'lishi kerak.",
      "Extra time va penalti yo'q.",
      "Dedline har kuni tungi soat 01:00 da.",
      "Agar raqib javob bermasa yoki hisobni noto'g'ri kiritsa — rasm yoki video bilan adminga murojaat qiling.",
    ],
    rules_detail: [
      "📢 Bot a'zo bo'lishni so'ragan kanalda yangiliklar joriy qilinadi.",
      "",
      "Batafsil: Botni haqiqiy futbol formatiga asta-sekin o'tkazib boramiz. Ishtirokchilar soni oshsa, ligalar soni 5 taga oshiriladi va Chempionlar ligasi ham qo'shiladi. Milliy ligadagi 1-o'rindan 6-o'ringacha bo'lgan klublar Chempionlar ligasida qatnashish imkoniyatiga ega bo'lishadi.",
      "",
      "🏆 Sovrinlar masalasida homiylarga mutanosib ravishda pul ham beriladi.",
    ],
    // Rating
    rating_title: "REYTING JADVALI",
    tab_top_scorers: "⚽ To'p urarlar",
    th_player: "O'yinchi",
    th_pts: "B",
    th_w:   "G",
    th_d:   "D",
    th_l:   "M",
    th_gf:  "GF",
    th_ga:  "GA",
    th_gd:  "GD",
    th_league: "Liga",
    th_goals_col: "Gol",
    no_data: "Ma'lumot yo'q",
    // Profile
    not_registered:  "Ro'yxatdan o'tilmagan",
    my_stats:        "STATISTIKA",
    my_matches:      "MENING O'YINLARIM",
    stat_pos: "O'rin",
    stat_w:   "G'alaba",
    stat_d:   "Durang",
    stat_l:   "Mag'lubiyat",
    no_matches:      "Hali o'yinlar yo'q",
    edit_nickname:   "Nickname tahrirlash",
    cancel:          "Bekor",
    save:            "Saqlash",
    nickname_invalid: "2–20 belgi bo'lishi kerak",
    nickname_saved:   "✅ Nickname saqlandi",
    // Result modal
    submit_result:    "Natija kiritish",
    submit:           "Yuborish",
    enter_result:     "Natija",
    me_vs_opponent:   "Men vs Raqib",
    matchday_locked:  "Bu tur hali ochilmagan. Har kuni soat 01:00 da yangi tur ochiladi.",
    matchday_locked_short: "Tur hali ochilmagan",
    opp_write_button: "Raqib chatiga yozish",
    opp_no_contact:   "Raqib bilan bog'lanib bo'lmaydi",
    result_submitted: "✅ Natija yuborildi",
    result_confirmed: "✅ Tasdiqlandi",
    result_rejected:  "❌ Rad etildi",
    // Match statuses
    status_pending:   "KUTILMOQDA",
    status_awaiting:  "TASDIQ",
    status_confirmed: "TASDIQLANDI",
    status_rejected:  "RAD ETILDI",
    // Register
    registered_ok:      "✅ Ro'yxatdan o'tdingiz!",
    already_registered: "Siz allaqachon ro'yxatdansiz",
    league_full_err:    "Liga to'liq",
    club_taken:          "Bu klub allaqachon band qilingan",
    // Prizes
    prizes_title:       "SOVRINLAR",
    golden_boot:        "Oltin Butsa",
    golden_boot_desc:   "Eng ko'p gol urgan o'yinchi",
    golden_ball:        "Oltin To'p",
    golden_ball_desc:   "Turnir g'olibi",
    by_league:          "LIGA BO'YICHA",
    goals:              "gol",
    // Admin panel
    admin_panel_title:    "ADMIN PANEL",
    admin_draw_title:     "QUR'A",
    admin_draw_button:    "Qur'a o'tkazish",
    admin_draw_confirm:   "Bu liga uchun qur'a o'tkazishni tasdiqlaysizmi? Bu amalni qaytarib bo'lmaydi.",
    admin_draw_success:   "✅ Qur'a o'tkazildi",
    admin_draw_not_full:  "Liga hali to'lmagan",
    admin_draw_already:   "Qur'a allaqachon o'tkazilgan",
    admin_state_not_started: "Qur'a o'tkazilgan, hali boshlanmagan",
    admin_state_running:  "Turnir davom etmoqda",
    admin_start_button:   "Turnirni boshlash",
    admin_start_confirm:  "Turnirni bugundan boshlashni tasdiqlaysizmi? Natijalar saqlanadi, bugun 1-tur ochiladi.",
    admin_start_success:  "✅ Turnir boshlandi",
    admin_start_no_matches: "Avval qur'a o'tkazing",
    admin_redraw_button:  "Qayta qur'a",
    admin_redraw_confirm: "DIQQAT: Qayta qur'a barcha kiritilgan natijalarni o'chiradi! Davom etasizmi?",
    admin_redraw_confirm2: "Aniqmisiz? Bu amalni ortga qaytarib bo'lmaydi.",
    admin_redraw_success: "✅ Qayta qur'a o'tkazildi",
    admin_redraw_keep_button: "Natijani saqlab qayta qur'a",
    admin_redraw_keep_confirm: "Jadval qayta tuziladi va yangi o'yinchi(lar) jadvalga qo'shiladi. Kiritilgan natijalar saqlanadi. Davom etasizmi?",
    admin_redraw_keep_success: "✅ Qayta qur'a tayyor. Saqlangan natijalar: ",
    admin_reopen_button: "Avtomatik turlarni qayta ochish",
    admin_reopen_confirm: "Turnir BUGUNDAN qayta boshlanadi: bugun faqat birinchi turlar ochiq, qolgani yopiq. Avtomatik 0:0 turlar qayta o'ynaladi. Qo'lda kiritilgan natijalar saqlanadi. Davom etasizmi?",
    admin_reopen_success: "✅ Qayta ochilgan avtomatik turlar: ",
    admin_remove_player:  "Chiqarish",
    admin_confirm_remove: "Bu o'yinchini chiqarishni tasdiqlaysizmi?",
    admin_player_removed: "✅ O'yinchi chiqarildi",
    admin_rejected_title:    "RAD ETILGAN NATIJALAR",
    admin_set_result_title:  "Natijani belgilash",
    admin_set_result:        "Natija",
    admin_reset_match:       "Qayta tiklash",
    admin_match_resolved:    "✅ Natija belgilandi",
    admin_fix_title:                  "TASDIQLANGAN NATIJANI TUZATISH",
    admin_fix_match_id_placeholder:   "Match ID",
    admin_fix_submit:                 "Tuzatish",
    admin_fix_success:                "✅ Natija tuzatildi",
    admin_fix_match_id_required:      "Match ID kiritilmadi",
    player_matches:       "O'YINLARI",
    back:                 "Ortga",
    no_username:          "Username yo'q",
  },

  ru: {
    nav_home:    "Главная",
    nav_rating:  "Рейтинг",
    nav_profile: "Профиль",
    nav_prizes:  "Призы",
    players:         "Игроки",
    max_players:     "Максимум",
    matchday:        "Тур",
    season:          "Сезон",
    register:        "Зарегистрироваться",
    choose_league:   "ВЫБОР ЛИГИ",
    clubs_in_league: "КЛУБЫ ЛИГИ",
    home_my_matches: "МОИ ТЕКУЩИЕ МАТЧИ",
    select_club:     "Выберите клуб",
    already_in_season: "Вы уже зарегистрированы в этом сезоне",
    open:            "ОТКРЫТА",
    full:            "ЗАПОЛНЕНА",
    league_locked_badge: "ЗАКРЫТА",
    league_locked_toast: "Эта лига пока закрыта. Сначала должна заполниться предыдущая лига.",
    league_open:     "ОТКРЫТА — РЕГИСТРАЦИЯ ИДЁТ",
    league_full:     "ЗАПОЛНЕНА",
    rules:           "Правила",
    rules_list: [
      "Матч длится 8 минут.",
      "Двойной отбор (dual press) включать запрещено.",
      "Состояние игроков должно быть \"Excellent\".",
      "Дополнительное время и пенальти отсутствуют.",
      "Дедлайн каждый день в 01:00 ночи.",
      "Если соперник не отвечает или вводит неверный счёт — обратитесь к админу со скриншотом или видео.",
    ],
    rules_detail: [
      "📢 Новости публикуются в канале, на который требуется подписка.",
      "",
      "Подробно: Бот постепенно переводим в формат настоящего футбола. При росте числа участников количество лиг увеличится до 5, а также добавится Лига чемпионов. Клубы с 1-го по 6-е место в национальной лиге получат право участвовать в Лиге чемпионов.",
      "",
      "🏆 По призам спонсорам также выплачиваются денежные средства пропорционально.",
    ],
    rating_title: "ТАБЛИЦА РЕЙТИНГА",
    tab_top_scorers: "⚽ Бомбардиры",
    th_player: "Игрок",
    th_pts: "О",
    th_w:   "П",
    th_d:   "Н",
    th_l:   "П",
    th_gf:  "ЗГ",
    th_ga:  "ПГ",
    th_gd:  "РГ",
    th_league: "Лига",
    th_goals_col: "Гол",
    no_data: "Нет данных",
    not_registered:  "Не зарегистрирован",
    my_stats:        "СТАТИСТИКА",
    my_matches:      "МОИ МАТЧИ",
    stat_pos: "Место",
    stat_w:   "Победы",
    stat_d:   "Ничьи",
    stat_l:   "Пор.",
    no_matches:      "Матчей пока нет",
    edit_nickname:   "Изменить никнейм",
    cancel:          "Отмена",
    save:            "Сохранить",
    nickname_invalid: "Должно быть 2–20 символов",
    nickname_saved:   "✅ Никнейм сохранён",
    submit_result:    "Внести результат",
    submit:           "Отправить",
    enter_result:     "Результат",
    me_vs_opponent:   "Я против соперника",
    matchday_locked:  "Этот тур ещё не открыт. Новый тур открывается каждый день в 01:00.",
    matchday_locked_short: "Тур ещё не открыт",
    opp_write_button: "Написать сопернику",
    opp_no_contact:   "Не удаётся связаться с соперником",
    result_submitted: "✅ Результат отправлен",
    result_confirmed: "✅ Подтверждено",
    result_rejected:  "❌ Отклонено",
    status_pending:   "ОЖИДАНИЕ",
    status_awaiting:  "ПОДТВЕРДИТЬ",
    status_confirmed: "ПОДТВЕРЖДЁН",
    status_rejected:  "ОТКЛОНЁН",
    registered_ok:      "✅ Вы зарегистрированы!",
    already_registered: "Вы уже зарегистрированы",
    league_full_err:    "Лига заполнена",
    club_taken:          "Этот клуб уже занят",
    prizes_title:       "ПРИЗЫ",
    golden_boot:        "Золотая Бутса",
    golden_boot_desc:   "Лучший бомбардир турнира",
    golden_ball:        "Золотой Мяч",
    golden_ball_desc:   "Победитель турнира",
    by_league:          "ПО ЛИГЕ",
    goals:              "голов",
    // Admin panel
    admin_panel_title:    "АДМИН-ПАНЕЛЬ",
    admin_draw_title:     "ЖРЕБИЙ",
    admin_draw_button:    "Провести жребий",
    admin_draw_confirm:   "Провести жребий для этой лиги? Это действие нельзя отменить.",
    admin_draw_success:   "✅ Жребий проведён",
    admin_draw_not_full:  "Лига пока не заполнена",
    admin_draw_already:   "Жребий уже проведён",
    admin_state_not_started: "Жребий проведён, ещё не начат",
    admin_state_running:  "Турнир идёт",
    admin_start_button:   "Начать турнир",
    admin_start_confirm:  "Начать турнир с сегодняшнего дня? Результаты сохранятся, сегодня откроется 1-й тур.",
    admin_start_success:  "✅ Турнир начат",
    admin_start_no_matches: "Сначала проведите жребий",
    admin_redraw_button:  "Повторный жребий",
    admin_redraw_confirm: "ВНИМАНИЕ: Повторный жребий удалит все внесённые результаты! Продолжить?",
    admin_redraw_confirm2: "Вы уверены? Это действие нельзя отменить.",
    admin_redraw_success: "✅ Повторный жребий проведён",
    admin_redraw_keep_button: "Пересоставить (сохранить результаты)",
    admin_redraw_keep_confirm: "Расписание будет пересоставлено, новые игроки добавлены. Внесённые результаты сохранятся. Продолжить?",
    admin_redraw_keep_success: "✅ Готово. Сохранено результатов: ",
    admin_reopen_button: "Заново открыть авто-туры",
    admin_reopen_confirm: "Турнир начнётся ЗАНОВО с сегодня: открыты только первые туры, остальные закрыты. Авто-туры 0:0 переиграются. Введённые вручную результаты сохраняются. Продолжить?",
    admin_reopen_success: "✅ Заново открыто авто-туров: ",
    admin_remove_player:  "Удалить",
    admin_confirm_remove: "Удалить этого игрока?",
    admin_player_removed: "✅ Игрок удалён",
    admin_rejected_title:    "ОТКЛОНЁННЫЕ РЕЗУЛЬТАТЫ",
    admin_set_result_title:  "Указать результат",
    admin_set_result:        "Результат",
    admin_reset_match:       "Сбросить",
    admin_match_resolved:    "✅ Результат обновлён",
    admin_fix_title:                  "ИСПРАВИТЬ ПОДТВЕРЖДЁННЫЙ РЕЗУЛЬТАТ",
    admin_fix_match_id_placeholder:   "ID матча",
    admin_fix_submit:                 "Исправить",
    admin_fix_success:                "✅ Результат исправлен",
    admin_fix_match_id_required:      "Введите ID матча",
    player_matches:       "МАТЧИ",
    back:                 "Назад",
    no_username:          "Нет username",
  },

  en: {
    nav_home:    "Home",
    nav_rating:  "Rating",
    nav_profile: "Profile",
    nav_prizes:  "Prizes",
    players:         "Players",
    max_players:     "Max",
    matchday:        "Round",
    season:          "Season",
    register:        "Register",
    choose_league:   "CHOOSE LEAGUE",
    clubs_in_league: "CLUBS IN LEAGUE",
    home_my_matches: "MY CURRENT MATCHES",
    select_club:     "Select a club",
    already_in_season: "You are already registered this season",
    open:            "OPEN",
    full:            "FULL",
    league_locked_badge: "LOCKED",
    league_locked_toast: "This league is locked. The previous league must fill up first.",
    league_open:     "OPEN — REGISTRATION ONGOING",
    league_full:     "FULL",
    rules:           "Rules",
    rules_list: [
      "A match lasts 8 minutes.",
      "Dual press (double-team defending) is not allowed.",
      "Player condition must be \"Excellent\".",
      "No extra time and no penalties.",
      "Deadline every day at 01:00 at night.",
      "If your opponent doesn't respond or enters the wrong score, contact an admin with a screenshot or video.",
    ],
    rules_detail: [
      "📢 News is published in the channel you're required to join.",
      "",
      "Details: We're gradually moving the bot toward a real football format. As the number of participants grows, the number of leagues will increase to 5 and a Champions League will be added. Clubs finishing 1st to 6th in the national league qualify for the Champions League.",
      "",
      "🏆 Regarding prizes, sponsors are also paid proportionally in cash.",
    ],
    rating_title: "STANDINGS",
    tab_top_scorers: "⚽ Top Scorers",
    th_player: "Player",
    th_pts: "Pts",
    th_w:   "W",
    th_d:   "D",
    th_l:   "L",
    th_gf:  "GF",
    th_ga:  "GA",
    th_gd:  "GD",
    th_league: "League",
    th_goals_col: "Goals",
    no_data: "No data",
    not_registered:  "Not registered",
    my_stats:        "STATS",
    my_matches:      "MY MATCHES",
    stat_pos: "Rank",
    stat_w:   "Wins",
    stat_d:   "Draws",
    stat_l:   "Losses",
    no_matches:      "No matches yet",
    edit_nickname:   "Edit nickname",
    cancel:          "Cancel",
    save:            "Save",
    nickname_invalid: "Must be 2–20 characters",
    nickname_saved:   "✅ Nickname saved",
    submit_result:    "Submit result",
    submit:           "Submit",
    enter_result:     "Result",
    me_vs_opponent:   "Me vs Opponent",
    matchday_locked:  "This matchday is not open yet. A new matchday opens every day at 01:00.",
    matchday_locked_short: "Matchday not open yet",
    opp_write_button: "Message opponent",
    opp_no_contact:   "Can't contact this opponent",
    result_submitted: "✅ Result submitted",
    result_confirmed: "✅ Confirmed",
    result_rejected:  "❌ Rejected",
    status_pending:   "PENDING",
    status_awaiting:  "CONFIRM",
    status_confirmed: "CONFIRMED",
    status_rejected:  "REJECTED",
    registered_ok:      "✅ You are registered!",
    already_registered: "You are already registered",
    league_full_err:    "League is full",
    club_taken:          "This club is already taken",
    prizes_title:       "PRIZES",
    golden_boot:        "Golden Boot",
    golden_boot_desc:   "Top scorer of the tournament",
    golden_ball:        "Golden Ball",
    golden_ball_desc:   "Tournament winner",
    by_league:          "BY LEAGUE",
    goals:              "goals",
    // Admin panel
    admin_panel_title:    "ADMIN PANEL",
    admin_draw_title:     "DRAW",
    admin_draw_button:    "Run draw",
    admin_draw_confirm:   "Run the draw for this league? This action cannot be undone.",
    admin_draw_success:   "✅ Draw completed",
    admin_draw_not_full:  "League is not full yet",
    admin_draw_already:   "Draw already completed",
    admin_state_not_started: "Drawn, not started yet",
    admin_state_running:  "Tournament in progress",
    admin_start_button:   "Start tournament",
    admin_start_confirm:  "Start the tournament from today? Results are kept, matchday 1 opens today.",
    admin_start_success:  "✅ Tournament started",
    admin_start_no_matches: "Run the draw first",
    admin_redraw_button:  "Redraw",
    admin_redraw_confirm: "WARNING: Redraw deletes all submitted results! Continue?",
    admin_redraw_confirm2: "Are you sure? This action cannot be undone.",
    admin_redraw_success: "✅ Redraw completed",
    admin_redraw_keep_button: "Redraw (keep results)",
    admin_redraw_keep_confirm: "The schedule will be rebuilt and new player(s) added. Submitted results are kept. Continue?",
    admin_redraw_keep_success: "✅ Done. Results kept: ",
    admin_reopen_button: "Reopen auto-resolved rounds",
    admin_reopen_confirm: "The tournament restarts from today: only the first rounds are open, the rest locked. Auto 0:0 rounds will be replayed. Manually entered results are kept. Continue?",
    admin_reopen_success: "✅ Auto-rounds reopened: ",
    admin_remove_player:  "Remove",
    admin_confirm_remove: "Remove this player?",
    admin_player_removed: "✅ Player removed",
    admin_rejected_title:    "REJECTED RESULTS",
    admin_set_result_title:  "Set result",
    admin_set_result:        "Set result",
    admin_reset_match:       "Reset",
    admin_match_resolved:    "✅ Result updated",
    admin_fix_title:                  "FIX CONFIRMED RESULT",
    admin_fix_match_id_placeholder:   "Match ID",
    admin_fix_submit:                 "Fix",
    admin_fix_success:                "✅ Result fixed",
    admin_fix_match_id_required:      "Match ID is required",
    player_matches:       "MATCHES",
    back:                 "Back",
    no_username:          "No username",
  },
};

// ============================================================
//  I18N — DOM YANGILASH
// ============================================================

function applyTranslations() {
  const t = APP.t;
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    if (t[key] !== undefined && typeof t[key] === "string") {
      el.textContent = t[key];
    }
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    if (t[key] !== undefined && typeof t[key] === "string") {
      el.placeholder = t[key];
    }
  });
  document.getElementById("header-lang").textContent = APP.lang.toUpperCase();
}

// HTML'dagi [data-icon="name"] elementlarni premium SVG ikon bilan to'ldiradi
function applyIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach(el => {
    const name = el.dataset.icon;
    const svg = ICON.get(name);
    if (svg) el.innerHTML = svg;
  });
}

function setLanguage(lang) {
  APP.lang = lang;
  APP.t    = TEXTS[lang] || TEXTS["uz"];
  applyTranslations();
}

function cycleLanguage() {
  const order = ["uz", "ru", "en"];
  const next  = order[(order.indexOf(APP.lang) + 1) % order.length];
  setLanguage(next);

  // data-i18n bilan belgilanmagan, JS orqali to'ldiriladigan qismlarni
  // (masalan Rules ro'yxati, Rating jadvali, Admin panel) ham yangilash
  // uchun joriy faol bo'limni qayta yuklaymiz.
  const activeSection = document.querySelector(".section.active");
  const sectionName = activeSection?.id?.replace("section-", "");
  SECTION_LOADERS[sectionName]?.();
}

// ============================================================
//  NAVIGATION
// ============================================================

const SECTION_LOADERS = {
  home:    () => loadHome(),
  rating:  () => loadRating(),
  profile: () => loadProfile(),
  prizes:  () => loadPrizes(),
};

function navigateTo(sectionName) {
  // Sectionlarni almashtirish
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.getElementById(`section-${sectionName}`)?.classList.add("active");

  // Nav tugmalarini yangilash
  document.querySelectorAll(".nav-item").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.section === sectionName);
  });

  // Ma'lumotlarni yuklash
  SECTION_LOADERS[sectionName]?.();
}

// ============================================================
//  TOAST
// ============================================================

let _toastTimer = null;

function showToast(msg) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => toast.classList.remove("show"), 2800);
}

// ============================================================
//  LOADING SCREEN
// ============================================================

function hideLoadingScreen() {
  const screen = document.getElementById("loading-screen");
  const appEl  = document.getElementById("app");
  setTimeout(() => {
    screen.style.opacity = "0";
    screen.style.transition = "opacity 0.35s";
    setTimeout(() => {
      screen.style.display = "none";
      appEl.classList.remove("hidden");
    }, 350);
  }, 1200); // loading bar animatsiyasi tugashini kutish
}

// ============================================================
//  INIT
// ============================================================

// Telegram yuqori paneli balandligini CSS o'zgaruvchisiga yozadi (--safe-top).
// contentSafeAreaInset — kontent uchun xavfsiz zona (X/⋮ tugmalari ostidan).
// safeAreaInset — qurilma tizim paneli (notch va h.k.). Ikkalasini qo'shamiz.
function applySafeArea(tg) {
  let top = 0;
  try {
    const content = tg.contentSafeAreaInset?.top || 0;
    const device  = tg.safeAreaInset?.top || 0;
    top = content + device;
  } catch (_) {
    top = 0;
  }
  // Hech qiymat kelmasa (eski Telegram klientlari) — zaxira sifatida kichik bo'sh joy
  document.documentElement.style.setProperty("--safe-top", top + "px");
}

async function init() {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    APP.currentUser = tg.initDataUnsafe?.user || null;

    // Telegram yuqori paneli (X, ⋮ tugmalari) ostidan kontent o'tib ketmasligi uchun
    // safe area qiymatini CSS o'zgaruvchisiga yozamiz. Qurilmaga qarab dinamik.
    applySafeArea(tg);
    // Qiymat keyinroq o'zgarsa (panel kengaysa) — qayta qo'llaymiz
    if (typeof tg.onEvent === "function") {
      tg.onEvent("safeAreaChanged", () => applySafeArea(tg));
      tg.onEvent("contentSafeAreaChanged", () => applySafeArea(tg));
      tg.onEvent("viewportChanged", () => applySafeArea(tg));
    }

    // Telegram dan tilni olish (foydalanuvchi DB'da saqlangan tilga mos kelishi kerak)
    const tgLang = (tg.initDataUnsafe?.user?.language_code || "uz").toLowerCase();
    const lang   = ["uz", "ru", "en"].includes(tgLang) ? tgLang : "uz";
    setLanguage(lang);
  } else {
    // Browser dev mode
    APP.currentUser = { id: 0, first_name: "Dev" };
    setLanguage("uz");
  }

  bindEvents();
  applyIcons();           // Premium SVG ikonlarni joylashtirish (navigatsiya va h.k.)
  hideLoadingScreen();

  // Majburiy kanal a'zoligini tekshiramiz — a'zo bo'lmasa asosiy ilova ochilmaydi
  const subscribed = await checkChannelMembership();
  if (!subscribed) {
    showSubscribeGate();
    return;
  }

  navigateTo("home");
}

// ============================================================
//  MAJBURIY KANAL A'ZOLIGI
// ============================================================

// Backend orqali a'zolikni tekshiradi. Xato bo'lsa — true (bloklamaymiz).
async function checkChannelMembership() {
  try {
    const data = await apiFetch("/membership/check");
    APP.channelInfo = { url: data.channel_url, username: data.channel_username };
    return !!data.subscribed;
  } catch (e) {
    // Tekshiruv ishlamasa foydalanuvchini bloklamaymiz
    return true;
  }
}

// "Kanalga a'zo bo'ling" ekranini ko'rsatadi (asosiy ilova o'rniga)
function showSubscribeGate() {
  const t = APP.t;
  const info = APP.channelInfo || {};
  const url = info.url || "https://t.me/efootball_liga_turnir";

  const host = document.querySelector("main") || document.body;
  // Barcha bo'limlarni yashiramiz (active'ni olib tashlaymiz — navigateTo bilan bir xil tizim)
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  // Pastki navigatsiyani ham yashiramiz (gate paytida kerak emas)
  document.querySelector(".bottom-nav")?.classList.add("hidden");

  let gate = document.getElementById("subscribe-gate");
  if (!gate) {
    gate = document.createElement("div");
    gate.id = "subscribe-gate";
    host.appendChild(gate);
  }
  gate.classList.remove("hidden");
  gate.innerHTML = `
    <div class="subscribe-box">
      <div class="subscribe-icon">${ICON.get("megaphone", 40)}</div>
      <div class="subscribe-text">${escHtml(t.subscribe_required || "Botdan foydalanish uchun avval kanalimizga a'zo bo'ling:")}</div>
      <a class="subscribe-link-btn" href="${escHtml(url)}" target="_blank">${escHtml(t.subscribe_button || "📢 Kanalga a'zo bo'lish")}</a>
      <button class="subscribe-check-btn" id="btn-subscribe-check">${escHtml(t.subscribe_check_button || "✅ A'zo bo'ldim, tekshirish")}</button>
    </div>
  `;

  document.getElementById("btn-subscribe-check").addEventListener("click", async () => {
    const ok = await checkChannelMembership();
    if (ok) {
      hideSubscribeGate();
      navigateTo("home");
    } else {
      showToast(t.subscribe_not_yet || "❌ Siz hali kanalga a'zo bo'lmadingiz.");
    }
  });
}

// Gate'ni yopadi va asosiy interfeysni qaytaradi
function hideSubscribeGate() {
  const gate = document.getElementById("subscribe-gate");
  if (gate) gate.classList.add("hidden");
  document.querySelector(".bottom-nav")?.classList.remove("hidden");
}

// ============================================================
//  EVENT BINDINGS
// ============================================================

function bindEvents() {
  // Til almashtirish (header)
  document.getElementById("header-lang")
    .addEventListener("click", cycleLanguage);

  // Bottom nav
  document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => navigateTo(btn.dataset.section));
  });

  // Register tugmasi
  document.getElementById("btn-register")
    .addEventListener("click", registerToLeague);

  // Nickname modal
  document.getElementById("btn-nickname-cancel")
    .addEventListener("click", closeNicknameModal);
  document.getElementById("btn-nickname-save")
    .addEventListener("click", saveNickname);

  // Natija modal
  document.getElementById("btn-result-cancel")
    .addEventListener("click", closeResultModal);
  document.getElementById("btn-result-submit")
    .addEventListener("click", submitMatchResult);

  // Admin: rad etilgan natijani belgilash modali
  document.getElementById("btn-admin-resolve-cancel")
    .addEventListener("click", closeAdminResolveModal);
  document.getElementById("btn-admin-resolve-submit")
    .addEventListener("click", submitAdminSetResult);

  // Admin: tasdiqlangan natijani tuzatish formasi
  document.getElementById("btn-admin-fix-submit")
    .addEventListener("click", submitAdminFixConfirmed);

  // Modal tashqarisiga bosish — yopish
  document.getElementById("modal-nickname").addEventListener("click", e => {
    if (e.target === e.currentTarget) closeNicknameModal();
  });
  document.getElementById("modal-result").addEventListener("click", e => {
    if (e.target === e.currentTarget) closeResultModal();
  });
  document.getElementById("modal-admin-resolve").addEventListener("click", e => {
    if (e.target === e.currentTarget) closeAdminResolveModal();
  });

  // Boshqa o'yinchi profili — ortga tugmasi
  document.getElementById("btn-player-back")
    .addEventListener("click", closePlayerModal);
}

// ============================================================
//  START
// ============================================================

document.addEventListener("DOMContentLoaded", init);
