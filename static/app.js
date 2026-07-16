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
  // Chempionlar ligasi — yulduzli to'p (starball)
  ucl:     '<circle cx="12" cy="12" r="9"/><path d="m12 5.6 1 2.1 2.3.3-1.7 1.6.4 2.3-2-1.1-2 1.1.4-2.3L8.7 8l2.3-.3 1-2.1Z"/><path d="m5.6 13.4 1.9 1.4-.7 2.2"/><path d="m18.4 13.4-1.9 1.4.7 2.2"/><path d="M9.4 20.6 12 19l2.6 1.6"/>',
  // Rejim kartalari (premium belgilar)
  star:    '<path d="m12 3 2.7 5.6 6.1.8-4.5 4.2 1.1 6L12 16.7 6.6 19.6l1.1-6L3.2 9.4l6.1-.8L12 3Z"/>',
  shield:  '<path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6l-7-3Z"/><path d="M12 3v18"/>',
  swords:  '<path d="M4 4l7 7"/><path d="M4 4h3.5"/><path d="M4 4v3.5"/><path d="M20 4l-7 7"/><path d="M20 4h-3.5"/><path d="M20 4v3.5"/><path d="m8.5 14.5-3 3"/><path d="m5 17 2 2"/><path d="m15.5 14.5 3 3"/><path d="m19 17-2 2"/>',
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
  chatOpened:       new Set(),  // 💬 bosilgan match'lar (Natija tugmasi ochilishi uchun)
  adminResolveMatchId: null,  // Admin: rad etilgan natijani belgilash uchun
  ratingTab:        "league",  // Reyting bo'limidagi tab: "league" yoki "top_scorers"
  lang:             "uz",   // Joriy til
  t:                {},     // Aktiv tarjimalar
  chatMatchId:      null,   // WebApp chat: ochiq match id
  chatPoll:         null,   // WebApp chat: polling interval handle
  unread:           { total: 0, by_match: {} },  // O'qilmagan chat xabarlari (rozetka)
  seasons:          { league: 1, wc: 1 },  // Joriy mavsum raqamlari (liga/WC — hero kartalarda)
  adminContact:     { url: "", username: "" },  // Bosh admin bilan bog'lanish (katta hisob skrinshot)
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
      "O'yin **8 daqiqa** davom etadi.",
      "Ikkitalik himoya yoqish **mumkin emas**.",
      "O'yinchilar holati **\"Excellent\"** bo'lishi kerak.",
      "Extra time va penalti **yo'q**.",
      "Bir o'yinda to'pni tepib yuborish (очистить) soni **5 ta**. Undan oshsa video isbot bilan adminga murojaat qiling.",
      "Dedline har kuni tungi soat **23:30** da.",
      "Agar raqib javob bermasa yoki hisobni noto'g'ri kiritsa — **rasm yoki video bilan adminga murojaat qiling**.",
    ],
    div_rules_list: [
      "Har kuni **17:00–19:00** (Toshkent) oralig'ida ro'yxatdan o'tiladi.",
      "Ro'yxat yopilgach bot ishtirokchilarni **qur'a** orqali juftlaydi.",
      "Raqibingiz **profil** bo'limida va telegram xabarida ko'rinadi.",
      "O'yin natijasini **23:30** gacha kiritib, raqib tasdiqlashi kerak.",
      "Belgilangan vaqtgacha o'ynalmagan o'yin **0:0 durang** bo'ladi.",
      "Ishtirokchilar toq bo'lsa, bittasiga **avtomatik g'alaba** beriladi.",
      "G'alaba **+15**, durang **+10**, mag'lubiyat **\u221210** achko.",
      "Ko'p achko to'plagan ishtirokchi **reyting**da yuqoriga ko'tariladi.",
    ],
    rules_detail: [
      "📢 Bot a'zo bo'lishni so'ragan kanalda yangiliklar joriy qilinadi.",
      "",
      "Batafsil: Botni haqiqiy futbol formatiga asta-sekin o'tkazib boramiz. Ishtirokchilar soni oshsa, ligalar soni 5 taga oshiriladi va Chempionlar ligasi ham qo'shiladi. Milliy ligadagi 1-o'rindan 6-o'ringacha bo'lgan klublar Chempionlar ligasida qatnashish imkoniyatiga ega bo'lishadi.",
      "",
      "🏆 Sovrinlar masalasida homiylarga mutanosib ravishda pul ham beriladi.",
    ],
    rules_label_channel: "E'LON",
    rules_label_prize:   "SOVRIN",
    rules_label_detail:  "BATAFSIL",
    // Rating
    rating_title: "REYTING JADVALI",
    wc_mode_groups:                   "Guruhlar",
    wc_mode_bracket:                  "Setka",
    wc_playoff_my_title:              "PLAY-OFF O'YINLARIM",
    wc_playoff_locked:                "Yopiq",
    wc_playoff_waiting_opp:           "Raqib kutilmoqda",
    wc_playoff_draw_err:              "Durang bo'lmaydi — g'olib aniq bo'lsin",
    wc_playoff_draw_hint:             "Durang bo'lmaydi — g'olib aniq bo'lsin (penalti/qo'shimcha vaqt).",
    wc_playoff_not_started:           "Play-off hali boshlanmagan",
    wc_bracket_title:                 "PLAY-OFF SETKASI",
    th_group:                         "Guruh",
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
    chat_first_hint:  "Avval raqib bilan kelishing",
    me_vs_opponent:   "Men vs Raqib",
    matchday_locked:  "Bu tur hali ochilmagan. Har kuni soat 23:30 da yangi tur ochiladi.",
    matchday_locked_short: "Tur hali ochilmagan",
    opp_write_button: "Raqib chatiga yozish",
    opp_no_contact:   "Raqib bilan bog'lanib bo'lmaydi",
    webchat_open:        "Chatni ochish",
    webchat_opponent:    "Raqib",
    webchat_loading:     "Yuklanmoqda...",
    webchat_placeholder: "Xabar yozing...",
    webchat_empty:       "Hali xabar yo'q. Birinchi bo'lib yozing!",
    webchat_closed:      "Chat yopilgan",
    webchat_send_failed: "Xabar yuborilmadi",
    webchat_online:      "online",
    webchat_offline:     "oflayn",
    webchat_typing:      "yozmoqda",
    webchat_last_seen:   "oxirgi marta",
    webchat_just_now:    "hozirgina",
    webchat_min_ago:     "daqiqa oldin",
    webchat_hour_ago:    "soat oldin",
    webchat_day_ago:     "kun oldin",
    result_submitted: "✅ Natija yuborildi",
    result_admin_pending: "✅ Natija yuborildi. Katta hisob (5 dan ortiq) — bosh adminga isbot uchun SKRINSHOT yuboring. Admin tasdiqlagach hisobga o'tadi.",
    big_score_title:      "Katta hisob kiritildi",
    big_score_body:       "Natija yuborildi ✅\n\nKatta hisob (5 goldan ortiq) bosh admin tasdig'ini talab qiladi. Isbot uchun adminga o'yin SKRINSHOTINI yuboring — admin tasdiqlagach natija hisobga o'tadi va reytingga sanaladi.",
    big_score_contact:    "Adminga yozish",
    close:                "Yopish",
    result_confirmed: "✅ Tasdiqlandi",
    confirm_result_title: "Natijani tasdiqlaysizmi?",
    confirm_claims: "shu natijani da'vo qilyapti:",
    confirm_warning: "Faqat haqiqatan o'ynagan va natija to'g'ri bo'lsa tasdiqlang. Bunday o'yin bo'lmagan bo'lsa — rad eting.",
    confirm_yes: "Ha, o'ynadik va to'g'ri",
    confirm_no: "Yo'q, bunday o'yin bo'lmagan",
    opponent: "Raqib",
    result_rejected:  "❌ Rad etildi",
    // Match statuses
    status_pending:   "KUTILMOQDA",
    status_awaiting:  "TASDIQ",
    status_admin_pending: "ADMIN TASDIG'I",
    status_confirmed: "TASDIQLANDI",
    status_rejected:  "RAD ETILDI",
    // Register
    registered_ok:      "✅ Ro'yxatdan o'tdingiz!",
    already_registered: "Siz allaqachon ro'yxatdansiz",
    league_full_err:    "Liga to'liq",
    club_taken:          "Bu klub allaqachon band qilingan",
    // Prizes
    prizes_title:       "SOVRINLAR",
    wc_trophy_name:     "Jahon Chempionati Kubogi",
    wc_trophy_desc:     "Play-off g'olibi — jahon chempioni",
    wc_scorer_name:     "Jahon Chempionati To'purari",
    wc_scorer_desc:     "Eng ko'p gol urgan o'yinchi",
    wc_scorer_goals:    "gol",
    wc_champion_pending: "Hali aniqlanmagan",
    golden_boot:        "Oltin Butsa",
    golden_boot_desc:   "Eng ko'p gol urgan o'yinchi",
    golden_ball:        "Oltin To'p",
    golden_ball_desc:   "Turnir g'olibi",
    league_trophy:      "Liga Kubogi",
    league_trophy_desc: "Liga chempioni",
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
    admin_resolve_open_button: "Ochiq turlarni darrov tasdiqlash",
    admin_resolve_open_confirm: "Hozir ochiq turlardagi barcha o'yinlar darrov tasdiqlanadi (o'ynalmaganlar 0:0). Davom etasizmi?",
    admin_resolve_open_success: "✅ Tasdiqlangan o'yinlar: ",
    admin_undo_resolve_button: "Bugungi ochiq turlarni qayta ochish",
    admin_undo_resolve_confirm: "Bugun ochiq, lekin deadline o'tmagan turlardagi avtomatik 0:0 tasdiqlar bekor qilinadi (o'yinchilar bugun o'ynaydi). Tasdiqlangan eski turlar va qo'lda natijalar saqlanadi. Davom etasizmi?",
    admin_undo_resolve_success: "✅ Qayta ochilgan turlar: ",
    entry_wait_short: "Kuting",
    entry_wait_hint: "Hisob kiritish tur ochilgandan 1 soat 45 daqiqa keyin ochiladi",
    entry_too_early: "Hisob kiritish hali erta. Tur ochilgandan 1 soat 45 daqiqa o'tishi kerak.",
    entry_near_deadline: "Deadline yaqin (01:00). Oxirgi 15 daqiqada hisob kiritib bo'lmaydi.",
    entry_deadline_hint: "Deadline yaqin — hisob kiritish yopiq",
    reject_near_deadline: "Deadline yaqin (01:00). Endi rad etib bo'lmaydi — o'yin avtomatik tasdiqlanadi.",
    admin_remove_player:  "Chiqarish",
    admin_confirm_remove: "Bu o'yinchini chiqarishni tasdiqlaysizmi?",
    admin_player_removed: "✅ O'yinchi chiqarildi",
    admin_rejected_title:    "RAD ETILGAN NATIJALAR",
    admin_pending_title:     "ADMIN TASDIG'I (KATTA HISOB)",
    admin_pending_empty:     "Kutayotgan katta hisob yo'q",
    admin_pending_confirm:   "Tasdiqlash",
    admin_pending_reject:    "Rad etish",
    my_prizes_title:       "SOVRINLARIM",
    season_label:          "Mavsum",
    season_title:          "LIGA MAVSUMI",
    season_current:        "Joriy liga mavsumi",
    season_finalize_btn:   "Liga mavsumini yakunlash",
    season_finalize_hint:  "Liga sovrinlari (oltin to'p/butsa, liga kubogi) hisoblanadi, liga mavsumi oshadi",
    season_finalize_confirm: "Liga mavsumini yakunlaysizmi? Liga sovrinlari hisoblanib saqlanadi va liga mavsumi oshadi. Bu amalni ortga qaytarib bo'lmaydi.",
    season_finalized:      "Liga mavsumi yakunlandi",
    season_already_finalized: "Bu mavsum allaqachon yakunlangan",
    wc_season_title:       "WC MAVSUMI",
    wc_season_current:     "Joriy WC mavsumi",
    wc_season_finalize_btn: "WC mavsumini yakunlash",
    wc_season_finalize_hint: "WC kubogi (play-off chempioni) saqlanadi, WC mavsumi oshadi",
    wc_season_finalize_confirm: "WC mavsumini yakunlaysizmi? Play-off chempioni saqlanadi va WC mavsumi oshadi. Bu amalni ortga qaytarib bo'lmaydi.",
    wc_season_finalized:   "WC mavsumi yakunlandi",
    admin_set_result_title:  "Natijani belgilash",
    admin_set_result:        "Natija",
    admin_reset_match:       "Qayta tiklash",
    admin_match_resolved:    "✅ Natija belgilandi",
    admin_fix_title:                  "TASDIQLANGAN NATIJANI TUZATISH",
    admin_fix_match_id_placeholder:   "Match ID",
    admin_fix_submit:                 "Tuzatish",
    admin_fix_is_playoff:             "Play-off o'yini",
    admin_manage_title:               "ADMIN TAYINLASH",
    admin_assign_league_label:        "Ligalar:",
    admin_new_id_placeholder:         "Telegram ID",
    admin_add_btn:                    "Admin qo'shish",
    admin_no_admins:                  "Tayinlangan admin yo'q",
    admin_remove_role:                "O'chirish",
    admin_id_invalid:                 "Telegram ID ni kiriting",
    admin_added:                      "✅ Admin qo'shildi",
    admin_already:                    "Bu odam allaqachon admin",
    admin_is_super:                   "Bu odam allaqachon bosh admin",
    admin_removed:                    "✅ Admin o'chirildi",
    admin_remove_confirm:             "Bu adminni o'chirasizmi?",
    admin_fix_invalid:                "Match ID va natijani to'g'ri kiriting",
    admin_fix_done:                   "✅ Natija tuzatildi",
    admin_reset_btn:                  "Natijani bekor qilish",
    admin_reset_confirm:              "Bu o'yin natijasini bekor qilasizmi? O'yin qayta — : — bo'ladi.",
    admin_reset_done:                 "✅ Natija bekor qilindi",
    admin_already_pending:            "Bu o'yinda natija yo'q",
    admin_match_not_found:            "Match topilmadi",
    admin_wrong_status:               "Bu match tasdiqlanmagan",
    wc_admin_players_title:           "WC ISHTIROKCHILAR",
    wc_admin_schedules_title:         "O'YIN JADVALLARI",
    wc_admin_start_today_btn:         "Bugundan start berish",
    wc_admin_playoff_title:           "PLAY-OFF",
    wc_admin_playoff_start_btn:       "Play-off boshlash",
    wc_admin_playoff_hint:            "32 jamoa: 12 g'olib + 12 ikkinchi + 8 eng yaxshi 3-o'rin",
    wc_admin_playoff_ready:           "✅ 32 jamoa tayyor — boshlash mumkin",
    wc_admin_playoff_notready:        "⏳ Barcha guruhlar hali tugamagan",
    wc_admin_playoff_already:         "✅ Play-off allaqachon boshlangan",
    wc_admin_playoff_confirm:         "Play-off boshlansinmi? 32 jamoa saralanadi va setka tuziladi. Bu amalni ortga qaytarib bo'lmaydi.",
    wc_admin_start_today_hint:        "Bugun 1-2 tur ochiq, ertaga oxirgi tur (23:30)",
    wc_admin_start_today_confirm:     "Barcha guruhlarga bugundan start berilsinmi? Bugun 1-2 tur ochiq, ertaga oxirgi tur ochiladi.",
    wc_admin_start_today_none:        "O'yinli guruh topilmadi",
    wc_admin_fix_schedules_btn:       "Yo'qolgan jadvallarni yaratish",
    wc_admin_fix_schedules_hint:      "To'lgan, lekin o'yinlari yo'q guruhlar uchun",
    wc_admin_fix_schedules_confirm:   "To'lgan, lekin o'yinsiz guruhlar uchun jadval yaratilsinmi?",
    wc_admin_fix_schedules_none:      "✅ Hamma jadval joyida",
    wc_admin_remove_confirm:          "Bu o'yinchini WC ro'yxatidan chiqarasizmi?",
    wc_admin_removed:                 "✅ O'yinchi chiqarildi",
    wc_admin_not_registered:          "O'yinchi ro'yxatda yo'q",
    wc_admin_group_started:           "Guruh boshlangan — chiqarib bo'lmaydi",
    admin_fix_success:                "✅ Natija tuzatildi",
    admin_fix_match_id_required:      "Match ID kiritilmadi",
    player_matches:       "O'YINLARI",
    back:                 "Ortga",
    no_username:          "Username yo'q",
    // Mode select (kirish rejimi)
    mode_select_title:    "REJIMNI TANLANG",
    mode_leagues:         "Ligalar",
    mode_worldcup:        "Jahon Chempionati",
    worldcup_soon:        "Jahon Chempionati tez orada ishga tushadi!",
    // World Cup — home/reyting
    wc_open:              "OCHIQ — RO'YXAT DAVOM ETMOQDA",
    wc_playoff_stage:     "PLAY-OFF BOSQICHI",
    wc_group_full_badge:  "TO'LGAN — RO'YXAT YOPILGAN",
    wc_group:             "{g} guruh",
    wc_teams:             "Jamoalar",
    wc_choose_group:      "GURUH TANLASH",
    wc_teams_in_group:    "GURUHDAGI JAMOALAR",
    wc_select_team:       "Avval jamoa tanlang",
    wc_registered_label:  "Ro'yxatdan o'tgansiz",
    wc_already_in:        "Siz World Cup'da allaqachon ro'yxatdansiz",
    wc_registered_ok:     "✅ World Cup'ga ro'yxatdan o'tdingiz!",
    wc_group_full_err:    "Bu guruh to'lgan",
    wc_team_taken:        "Bu jamoa allaqachon band qilingan",
    wc_invalid:           "Noto'g'ri tanlov",
    wc_not_registered:    "Siz hali World Cup'ga ro'yxatdan o'tmagansiz",
    wc_no_matches:        "Hali o'yinlar yo'q",
    awaiting_short:       "Kutilmoqda",
    awaiting_hint:        "Raqib tasdiqlashini kuting",
    confirm_short:        "Tasdiqlash",
    loading:              "Yuklanmoqda...",
    confirmed_ok:         "✅ Natija tasdiqlandi",
    rejected_ok:          "❌ Natija rad etildi",
    already_submitted:    "Natija allaqachon kiritilgan",
    not_participant:      "Siz bu o'yin ishtirokchisi emassiz",
    wrong_status:         "Bu o'yin holati o'zgargan",
    not_opponent:         "Siz bu natijani tasdiqlay olmaysiz",
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
      "Матч длится **8 минут**.",
      "Двойной отбор (dual press) включать **запрещено**.",
      "Состояние игроков должно быть **\"Excellent\"**.",
      "Дополнительное время и пенальти **отсутствуют**.",
      "За матч разрешено не более **5 выносов** мяча (очистить). Если больше — обратитесь к админу с видеодоказательством.",
      "Дедлайн каждый день в **23:30** ночи.",
      "Если соперник не отвечает или вводит неверный счёт — **обратитесь к админу со скриншотом или видео**.",
    ],
    div_rules_list: [
      "Каждый день регистрация с **17:00 до 19:00** (Ташкент).",
      "После закрытия регистрации бот проводит **жеребьёвку** пар.",
      "Соперник виден в разделе **профиль** и в сообщении telegram.",
      "Результат нужно внести до **23:30**, соперник подтверждает.",
      "Несыгранный вовремя матч засчитывается как **ничья 0:0**.",
      "При нечётном числе участников одному даётся **автопобеда**.",
      "Победа **+15**, ничья **+10**, поражение **\u221210** очков.",
      "Набравший больше очков поднимается выше в **рейтинге**.",
    ],
    rules_detail: [
      "📢 Новости публикуются в канале, на который требуется подписка.",
      "",
      "Подробно: Бот постепенно переводим в формат настоящего футбола. При росте числа участников количество лиг увеличится до 5, а также добавится Лига чемпионов. Клубы с 1-го по 6-е место в национальной лиге получат право участвовать в Лиге чемпионов.",
      "",
      "🏆 По призам спонсорам также выплачиваются денежные средства пропорционально.",
    ],
    rules_label_channel: "ОБЪЯВЛЕНИЕ",
    rules_label_prize:   "ПРИЗЫ",
    rules_label_detail:  "ПОДРОБНО",
    rating_title: "ТАБЛИЦА РЕЙТИНГА",
    wc_mode_groups:                   "Группы",
    wc_mode_bracket:                  "Сетка",
    wc_playoff_my_title:              "МОИ ИГРЫ ПЛЕЙ-ОФФ",
    wc_playoff_locked:                "Закрыто",
    wc_playoff_waiting_opp:           "Ожидание соперника",
    wc_playoff_draw_err:              "Ничья невозможна — нужен победитель",
    wc_playoff_draw_hint:             "Ничья невозможна — победитель обязателен (пенальти/доп. время).",
    wc_playoff_not_started:           "Плей-офф ещё не начался",
    wc_bracket_title:                 "СЕТКА ПЛЕЙ-ОФФ",
    th_group:                         "Группа",
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
    chat_first_hint:  "Сначала договоритесь с соперником",
    me_vs_opponent:   "Я против соперника",
    matchday_locked:  "Этот тур ещё не открыт. Новый тур открывается каждый день в 23:30.",
    matchday_locked_short: "Тур ещё не открыт",
    opp_write_button: "Написать сопернику",
    opp_no_contact:   "Не удаётся связаться с соперником",
    webchat_open:        "Открыть чат",
    webchat_opponent:    "Соперник",
    webchat_loading:     "Загрузка...",
    webchat_placeholder: "Напишите сообщение...",
    webchat_empty:       "Сообщений пока нет. Напишите первым!",
    webchat_closed:      "Чат закрыт",
    webchat_send_failed: "Сообщение не отправлено",
    webchat_online:      "в сети",
    webchat_offline:     "офлайн",
    webchat_typing:      "печатает",
    webchat_last_seen:   "был(а)",
    webchat_just_now:    "только что",
    webchat_min_ago:     "мин. назад",
    webchat_hour_ago:    "ч. назад",
    webchat_day_ago:     "дн. назад",
    result_submitted: "✅ Результат отправлен",
    result_admin_pending: "✅ Результат отправлен. Крупный счёт (более 5) — отправьте главному админу СКРИНШОТ как доказательство. После подтверждения админом результат будет засчитан.",
    big_score_title:      "Крупный счёт",
    big_score_body:       "Результат отправлен ✅\n\nКрупный счёт (более 5 голов) требует подтверждения главного админа. Отправьте админу СКРИНШОТ матча как доказательство — после подтверждения результат будет засчитан в рейтинг.",
    big_score_contact:    "Написать админу",
    close:                "Закрыть",
    result_confirmed: "✅ Подтверждено",
    confirm_result_title: "Подтвердить результат?",
    confirm_claims: "заявляет этот результат:",
    confirm_warning: "Подтверждайте только если игра действительно состоялась и счёт верный. Если такой игры не было — отклоните.",
    confirm_yes: "Да, мы играли, всё верно",
    confirm_no: "Нет, такой игры не было",
    opponent: "Соперник",
    result_rejected:  "❌ Отклонено",
    status_pending:   "ОЖИДАНИЕ",
    status_awaiting:  "ПОДТВЕРДИТЬ",
    status_admin_pending: "ПОДТВ. АДМИНА",
    status_confirmed: "ПОДТВЕРЖДЁН",
    status_rejected:  "ОТКЛОНЁН",
    registered_ok:      "✅ Вы зарегистрированы!",
    already_registered: "Вы уже зарегистрированы",
    league_full_err:    "Лига заполнена",
    club_taken:          "Этот клуб уже занят",
    prizes_title:       "ПРИЗЫ",
    wc_trophy_name:     "Кубок Чемпионата Мира",
    wc_trophy_desc:     "Победитель плей-офф — чемпион мира",
    wc_scorer_name:     "Лучший бомбардир Чемпионата Мира",
    wc_scorer_desc:     "Игрок, забивший больше всех голов",
    wc_scorer_goals:    "гол.",
    wc_champion_pending: "Ещё не определён",
    golden_boot:        "Золотая Бутса",
    golden_boot_desc:   "Лучший бомбардир турнира",
    golden_ball:        "Золотой Мяч",
    golden_ball_desc:   "Победитель турнира",
    league_trophy:      "Кубок Лиги",
    league_trophy_desc: "Чемпион лиги",
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
    admin_resolve_open_button: "Сразу подтвердить открытые туры",
    admin_resolve_open_confirm: "Все игры в открытых турах будут сразу подтверждены (несыгранные 0:0). Продолжить?",
    admin_resolve_open_success: "✅ Подтверждено игр: ",
    admin_undo_resolve_button: "Заново открыть сегодняшние туры",
    admin_undo_resolve_confirm: "Авто-подтверждения 0:0 в сегодняшних открытых турах (дедлайн не прошёл) будут отменены (игроки играют сегодня). Подтверждённые старые туры и ручные результаты сохраняются. Продолжить?",
    admin_undo_resolve_success: "✅ Заново открыто туров: ",
    entry_wait_short: "Ждите",
    entry_wait_hint: "Ввод счёта откроется через 1 час 45 минут после открытия тура",
    entry_too_early: "Вводить счёт ещё рано. Должно пройти 1 час 45 минут после открытия тура.",
    entry_near_deadline: "Дедлайн близко (01:00). В последние 15 минут счёт вводить нельзя.",
    entry_deadline_hint: "Дедлайн близко — ввод счёта закрыт",
    reject_near_deadline: "Дедлайн близко (01:00). Отклонять уже нельзя — игра подтвердится автоматически.",
    admin_remove_player:  "Удалить",
    admin_confirm_remove: "Удалить этого игрока?",
    admin_player_removed: "✅ Игрок удалён",
    admin_rejected_title:    "ОТКЛОНЁННЫЕ РЕЗУЛЬТАТЫ",
    admin_pending_title:     "ПОДТВ. АДМИНА (КРУПНЫЙ СЧЁТ)",
    admin_pending_empty:     "Нет ожидающих крупных счетов",
    admin_pending_confirm:   "Подтвердить",
    admin_pending_reject:    "Отклонить",
    my_prizes_title:       "МОИ ПРИЗЫ",
    season_label:          "Сезон",
    season_title:          "СЕЗОН ЛИГИ",
    season_current:        "Текущий сезон лиги",
    season_finalize_btn:   "Завершить сезон лиги",
    season_finalize_hint:  "Призы лиги (золотой мяч/бутса, кубок лиги) подсчитываются, сезон лиги растёт",
    season_finalize_confirm: "Завершить сезон лиги? Призы лиги будут подсчитаны и сохранены, сезон лиги вырастет. Это необратимо.",
    season_finalized:      "Сезон лиги завершён",
    season_already_finalized: "Этот сезон уже завершён",
    wc_season_title:       "СЕЗОН ЧМ",
    wc_season_current:     "Текущий сезон ЧМ",
    wc_season_finalize_btn: "Завершить сезон ЧМ",
    wc_season_finalize_hint: "Кубок ЧМ (чемпион плей-офф) сохраняется, сезон ЧМ растёт",
    wc_season_finalize_confirm: "Завершить сезон ЧМ? Чемпион плей-офф будет сохранён, сезон ЧМ вырастет. Это необратимо.",
    wc_season_finalized:   "Сезон ЧМ завершён",
    admin_set_result_title:  "Указать результат",
    admin_set_result:        "Результат",
    admin_reset_match:       "Сбросить",
    admin_match_resolved:    "✅ Результат обновлён",
    admin_fix_title:                  "ИСПРАВИТЬ ПОДТВЕРЖДЁННЫЙ РЕЗУЛЬТАТ",
    admin_fix_match_id_placeholder:   "ID матча",
    admin_fix_submit:                 "Исправить",
    admin_fix_is_playoff:             "Матч плей-офф",
    admin_manage_title:               "НАЗНАЧЕНИЕ АДМИНА",
    admin_assign_league_label:        "Лиги:",
    admin_new_id_placeholder:         "Telegram ID",
    admin_add_btn:                    "Добавить админа",
    admin_no_admins:                  "Нет назначенных админов",
    admin_remove_role:                "Удалить",
    admin_id_invalid:                 "Введите Telegram ID",
    admin_added:                      "✅ Админ добавлен",
    admin_already:                    "Этот человек уже админ",
    admin_is_super:                   "Этот человек уже главный админ",
    admin_removed:                    "✅ Админ удалён",
    admin_remove_confirm:             "Удалить этого админа?",
    admin_fix_invalid:                "Введите Match ID и результат правильно",
    admin_fix_done:                   "✅ Результат исправлен",
    admin_reset_btn:                  "Отменить результат",
    admin_reset_confirm:              "Отменить результат этого матча? Матч снова станет — : —.",
    admin_reset_done:                 "✅ Результат отменён",
    admin_already_pending:            "В этом матче нет результата",
    admin_match_not_found:            "Матч не найден",
    admin_wrong_status:               "Этот матч не подтверждён",
    wc_admin_players_title:           "УЧАСТНИКИ ЧМ",
    wc_admin_schedules_title:         "РАСПИСАНИЕ ИГР",
    wc_admin_start_today_btn:         "Старт с сегодня",
    wc_admin_playoff_title:           "ПЛЕЙ-ОФФ",
    wc_admin_playoff_start_btn:       "Начать плей-офф",
    wc_admin_playoff_hint:            "32 команды: 12 победителей + 12 вторых + 8 лучших третьих",
    wc_admin_playoff_ready:           "✅ 32 команды готовы — можно начинать",
    wc_admin_playoff_notready:        "⏳ Не все группы завершены",
    wc_admin_playoff_already:         "✅ Плей-офф уже начат",
    wc_admin_playoff_confirm:         "Начать плей-офф? 32 команды отберутся и составится сетка. Это действие необратимо.",
    wc_admin_start_today_hint:        "Сегодня туры 1-2 открыты, завтра последний (23:30)",
    wc_admin_start_today_confirm:     "Дать старт всем группам с сегодня? Сегодня туры 1-2 открыты, завтра последний.",
    wc_admin_start_today_none:        "Группы с играми не найдены",
    wc_admin_fix_schedules_btn:       "Создать недостающие расписания",
    wc_admin_fix_schedules_hint:      "Для заполненных групп без игр",
    wc_admin_fix_schedules_confirm:   "Создать расписание для заполненных групп без игр?",
    wc_admin_fix_schedules_none:      "✅ Все расписания на месте",
    wc_admin_remove_confirm:          "Исключить этого игрока из списка ЧМ?",
    wc_admin_removed:                 "✅ Игрок исключён",
    wc_admin_not_registered:          "Игрок не в списке",
    wc_admin_group_started:           "Группа началась — нельзя исключить",
    admin_fix_success:                "✅ Результат исправлен",
    admin_fix_match_id_required:      "Введите ID матча",
    player_matches:       "МАТЧИ",
    back:                 "Назад",
    no_username:          "Нет username",
    // Mode select (kirish rejimi)
    mode_select_title:    "ВЫБЕРИТЕ РЕЖИМ",
    mode_leagues:         "Лиги",
    mode_worldcup:        "Чемпионат мира",
    worldcup_soon:        "Чемпионат мира скоро запустится!",
    // World Cup — home/reyting
    wc_open:              "ОТКРЫТА — РЕГИСТРАЦИЯ ИДЁТ",
    wc_playoff_stage:     "СТАДИЯ ПЛЕЙ-ОФФ",
    wc_group_full_badge:  "ЗАПОЛНЕНА — РЕГИСТРАЦИЯ ЗАКРЫТА",
    wc_group:             "Группа {g}",
    wc_teams:             "Команды",
    wc_choose_group:      "ВЫБОР ГРУППЫ",
    wc_teams_in_group:    "КОМАНДЫ ГРУППЫ",
    wc_select_team:       "Сначала выберите команду",
    wc_registered_label:  "Вы зарегистрированы",
    wc_already_in:        "Вы уже зарегистрированы в Чемпионате мира",
    wc_registered_ok:     "✅ Вы зарегистрировались в Чемпионате мира!",
    wc_group_full_err:    "Эта группа заполнена",
    wc_team_taken:        "Эта команда уже занята",
    wc_invalid:           "Неверный выбор",
    wc_not_registered:    "Вы ещё не зарегистрированы в Чемпионате мира",
    wc_no_matches:        "Пока нет игр",
    awaiting_short:       "Ожидание",
    awaiting_hint:        "Ждите подтверждения соперника",
    confirm_short:        "Подтвердить",
    loading:              "Загрузка...",
    confirmed_ok:         "✅ Результат подтверждён",
    rejected_ok:          "❌ Результат отклонён",
    already_submitted:    "Результат уже введён",
    not_participant:      "Вы не участник этой игры",
    wrong_status:         "Статус этой игры изменился",
    not_opponent:         "Вы не можете подтвердить этот результат",
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
      "A match lasts **8 minutes**.",
      "Dual press (double-team defending) is **not allowed**.",
      "Player condition must be **\"Excellent\"**.",
      "No extra time and **no penalties**.",
      "A maximum of **5 ball clearances** (kicking the ball away) per match. If exceeded, contact an admin with video proof.",
      "Deadline every day at **23:30** at night.",
      "If your opponent doesn't respond or enters the wrong score, **contact an admin with a screenshot or video**.",
    ],
    div_rules_list: [
      "Registration is open daily from **17:00 to 19:00** (Tashkent).",
      "After registration closes, the bot **pairs** players by draw.",
      "Your opponent appears in the **profile** tab and a telegram message.",
      "Submit the result by **23:30**; the opponent must confirm it.",
      "A match not played in time is scored as a **0:0 draw**.",
      "With an odd number of players, one gets an **automatic win**.",
      "Win **+15**, draw **+10**, loss **\u221210** points.",
      "Players with more points rise higher in the **rating**.",
    ],
    rules_detail: [
      "📢 News is published in the channel you're required to join.",
      "",
      "Details: We're gradually moving the bot toward a real football format. As the number of participants grows, the number of leagues will increase to 5 and a Champions League will be added. Clubs finishing 1st to 6th in the national league qualify for the Champions League.",
      "",
      "🏆 Regarding prizes, sponsors are also paid proportionally in cash.",
    ],
    rules_label_channel: "ANNOUNCEMENT",
    rules_label_prize:   "PRIZES",
    rules_label_detail:  "DETAILS",
    rating_title: "STANDINGS",
    wc_mode_groups:                   "Groups",
    wc_mode_bracket:                  "Bracket",
    wc_playoff_my_title:              "MY PLAY-OFF MATCHES",
    wc_playoff_locked:                "Locked",
    wc_playoff_waiting_opp:           "Waiting for opponent",
    wc_playoff_draw_err:              "No draw — there must be a winner",
    wc_playoff_draw_hint:             "No draw — a winner is required (penalties/extra time).",
    wc_playoff_not_started:           "Play-off hasn't started yet",
    wc_bracket_title:                 "PLAY-OFF BRACKET",
    th_group:                         "Group",
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
    chat_first_hint:  "First agree with your opponent",
    me_vs_opponent:   "Me vs Opponent",
    matchday_locked:  "This matchday is not open yet. A new matchday opens every day at 23:30.",
    matchday_locked_short: "Matchday not open yet",
    opp_write_button: "Message opponent",
    opp_no_contact:   "Can't contact this opponent",
    webchat_open:        "Open chat",
    webchat_opponent:    "Opponent",
    webchat_loading:     "Loading...",
    webchat_placeholder: "Type a message...",
    webchat_empty:       "No messages yet. Be the first to write!",
    webchat_closed:      "Chat closed",
    webchat_send_failed: "Message not sent",
    webchat_online:      "online",
    webchat_offline:     "offline",
    webchat_typing:      "typing",
    webchat_last_seen:   "last seen",
    webchat_just_now:    "just now",
    webchat_min_ago:     "min ago",
    webchat_hour_ago:    "h ago",
    webchat_day_ago:     "d ago",
    result_submitted: "✅ Result submitted",
    result_admin_pending: "✅ Result submitted. Big score (over 5) — send a SCREENSHOT to the head admin as proof. It counts once the admin confirms.",
    big_score_title:      "Big score",
    big_score_body:       "Result submitted ✅\n\nA big score (over 5 goals) requires head admin approval. Send the admin a SCREENSHOT of the match as proof — once confirmed, the result counts and is added to the rating.",
    big_score_contact:    "Message admin",
    close:                "Close",
    result_confirmed: "✅ Confirmed",
    confirm_result_title: "Confirm the result?",
    confirm_claims: "claims this result:",
    confirm_warning: "Only confirm if the match was actually played and the score is correct. If no such match happened — reject it.",
    confirm_yes: "Yes, we played, it's correct",
    confirm_no: "No, this match didn't happen",
    opponent: "Opponent",
    result_rejected:  "❌ Rejected",
    status_pending:   "PENDING",
    status_awaiting:  "CONFIRM",
    status_admin_pending: "ADMIN REVIEW",
    status_confirmed: "CONFIRMED",
    status_rejected:  "REJECTED",
    registered_ok:      "✅ You are registered!",
    already_registered: "You are already registered",
    league_full_err:    "League is full",
    club_taken:          "This club is already taken",
    prizes_title:       "PRIZES",
    wc_trophy_name:     "World Cup Trophy",
    wc_trophy_desc:     "Play-off winner — world champion",
    wc_scorer_name:     "World Cup Top Scorer",
    wc_scorer_desc:     "Player with the most goals",
    wc_scorer_goals:    "goals",
    wc_champion_pending: "Not determined yet",
    golden_boot:        "Golden Boot",
    golden_boot_desc:   "Top scorer of the tournament",
    golden_ball:        "Golden Ball",
    golden_ball_desc:   "Tournament winner",
    league_trophy:      "League Trophy",
    league_trophy_desc: "League champion",
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
    admin_resolve_open_button: "Confirm open rounds now",
    admin_resolve_open_confirm: "All matches in currently open rounds will be confirmed immediately (unplayed as 0:0). Continue?",
    admin_resolve_open_success: "✅ Matches confirmed: ",
    admin_undo_resolve_button: "Reopen today's open rounds",
    admin_undo_resolve_confirm: "Auto 0:0 confirmations in today's open rounds (deadline not passed) will be undone (players play today). Confirmed older rounds and manual results are kept. Continue?",
    admin_undo_resolve_success: "✅ Rounds reopened: ",
    entry_wait_short: "Wait",
    entry_wait_hint: "Score entry opens 1 hour 45 minutes after the round opens",
    entry_too_early: "Too early to enter the score. 1 hour 45 minutes must pass after the round opens.",
    entry_near_deadline: "Deadline is near (01:00). Score entry is closed in the last 15 minutes.",
    entry_deadline_hint: "Deadline near — score entry closed",
    reject_near_deadline: "Deadline is near (01:00). You can no longer reject — the match will be auto-confirmed.",
    admin_remove_player:  "Remove",
    admin_confirm_remove: "Remove this player?",
    admin_player_removed: "✅ Player removed",
    admin_rejected_title:    "REJECTED RESULTS",
    admin_pending_title:     "ADMIN REVIEW (BIG SCORE)",
    admin_pending_empty:     "No big scores awaiting review",
    admin_pending_confirm:   "Confirm",
    admin_pending_reject:    "Reject",
    my_prizes_title:       "MY PRIZES",
    season_label:          "Season",
    season_title:          "LEAGUE SEASON",
    season_current:        "Current league season",
    season_finalize_btn:   "Finalize league season",
    season_finalize_hint:  "League prizes (golden ball/boot, league cup) are calculated, league season increases",
    season_finalize_confirm: "Finalize the league season? League prizes will be calculated and saved, league season increases. This cannot be undone.",
    season_finalized:      "League season finalized",
    season_already_finalized: "This season is already finalized",
    wc_season_title:       "WC SEASON",
    wc_season_current:     "Current WC season",
    wc_season_finalize_btn: "Finalize WC season",
    wc_season_finalize_hint: "WC cup (play-off champion) is saved, WC season increases",
    wc_season_finalize_confirm: "Finalize the WC season? The play-off champion will be saved, WC season increases. This cannot be undone.",
    wc_season_finalized:   "WC season finalized",
    admin_set_result_title:  "Set result",
    admin_set_result:        "Set result",
    admin_reset_match:       "Reset",
    admin_match_resolved:    "✅ Result updated",
    admin_fix_title:                  "FIX CONFIRMED RESULT",
    admin_fix_match_id_placeholder:   "Match ID",
    admin_fix_submit:                 "Fix",
    admin_fix_is_playoff:             "Play-off match",
    admin_manage_title:               "MANAGE ADMINS",
    admin_assign_league_label:        "Leagues:",
    admin_new_id_placeholder:         "Telegram ID",
    admin_add_btn:                    "Add admin",
    admin_no_admins:                  "No admins assigned",
    admin_remove_role:                "Remove",
    admin_id_invalid:                 "Enter Telegram ID",
    admin_added:                      "✅ Admin added",
    admin_already:                    "This person is already an admin",
    admin_is_super:                   "This person is already a super admin",
    admin_removed:                    "✅ Admin removed",
    admin_remove_confirm:             "Remove this admin?",
    admin_fix_invalid:                "Enter Match ID and score correctly",
    admin_fix_done:                   "✅ Result fixed",
    admin_reset_btn:                  "Reset result",
    admin_reset_confirm:              "Reset this match result? The match will become — : — again.",
    admin_reset_done:                 "✅ Result reset",
    admin_already_pending:            "This match has no result",
    admin_match_not_found:            "Match not found",
    admin_wrong_status:               "This match is not confirmed",
    wc_admin_players_title:           "WC PARTICIPANTS",
    wc_admin_schedules_title:         "MATCH SCHEDULES",
    wc_admin_start_today_btn:         "Start from today",
    wc_admin_playoff_title:           "PLAY-OFF",
    wc_admin_playoff_start_btn:       "Start play-off",
    wc_admin_playoff_hint:            "32 teams: 12 winners + 12 runners-up + 8 best third-place",
    wc_admin_playoff_ready:           "✅ 32 teams ready — you can start",
    wc_admin_playoff_notready:        "⏳ Not all groups finished yet",
    wc_admin_playoff_already:         "✅ Play-off already started",
    wc_admin_playoff_confirm:         "Start play-off? 32 teams will be seeded and the bracket built. This cannot be undone.",
    wc_admin_start_today_hint:        "Today rounds 1-2 open, tomorrow the last (23:30)",
    wc_admin_start_today_confirm:     "Start all groups from today? Today rounds 1-2 open, tomorrow the last.",
    wc_admin_start_today_none:        "No groups with matches found",
    wc_admin_fix_schedules_btn:       "Create missing schedules",
    wc_admin_fix_schedules_hint:      "For full groups without matches",
    wc_admin_fix_schedules_confirm:   "Create schedules for full groups without matches?",
    wc_admin_fix_schedules_none:      "✅ All schedules are in place",
    wc_admin_remove_confirm:          "Remove this player from the WC list?",
    wc_admin_removed:                 "✅ Player removed",
    wc_admin_not_registered:          "Player not in list",
    wc_admin_group_started:           "Group started — cannot remove",
    admin_fix_success:                "✅ Result fixed",
    admin_fix_match_id_required:      "Match ID is required",
    player_matches:       "MATCHES",
    back:                 "Back",
    no_username:          "No username",
    // Mode select (kirish rejimi)
    mode_select_title:    "CHOOSE MODE",
    mode_leagues:         "Leagues",
    mode_worldcup:        "World Cup",
    worldcup_soon:        "World Cup is launching soon!",
    // World Cup — home/reyting
    wc_open:              "OPEN — REGISTRATION ONGOING",
    wc_playoff_stage:     "PLAY-OFF STAGE",
    wc_group_full_badge:  "FULL — REGISTRATION CLOSED",
    wc_group:             "Group {g}",
    wc_teams:             "Teams",
    wc_choose_group:      "CHOOSE GROUP",
    wc_teams_in_group:    "TEAMS IN GROUP",
    wc_select_team:       "Select a team first",
    wc_registered_label:  "You are registered",
    wc_already_in:        "You are already registered in the World Cup",
    wc_registered_ok:     "✅ You registered for the World Cup!",
    wc_group_full_err:    "This group is full",
    wc_team_taken:        "This team is already taken",
    wc_invalid:           "Invalid selection",
    wc_not_registered:    "You are not registered in the World Cup yet",
    wc_no_matches:        "No matches yet",
    awaiting_short:       "Awaiting",
    awaiting_hint:        "Waiting for opponent to confirm",
    confirm_short:        "Confirm",
    loading:              "Loading...",
    confirmed_ok:         "✅ Result confirmed",
    rejected_ok:          "❌ Result rejected",
    already_submitted:    "Result already submitted",
    not_participant:      "You are not a participant in this match",
    wrong_status:         "This match status has changed",
    not_opponent:         "You cannot confirm this result",
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

  // World Cup ekrani ochiq bo'lsa, uni ham yangi tilga qayta chizamiz
  const wcRoot = document.getElementById("worldcup-root");
  if (wcRoot && !wcRoot.classList.contains("hidden") && typeof renderWorldCup === "function") {
    renderWorldCup();
  }
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

  // Profil rozetkasini har sahifada yangilab turamiz (umumiy o'qilmagan soni)
  if (typeof refreshUnreadBadge === "function") refreshUnreadBadge();

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
  let content = 0, device = 0;
  try {
    content = tg.contentSafeAreaInset?.top || 0;
    device  = tg.safeAreaInset?.top || 0;
  } catch (_) {}
  // contentSafeAreaInset odatda device insetni O'Z ICHIGA OLADI — shuning uchun
  // ikkalasini QO'SHMAYMIZ (aks holda ikki barobar bo'sh joy chiqadi), kattasini olamiz.
  let top = Math.max(content, device);

  // Fullscreen rejimda Telegram tugmalari (X/⋮) ekran ustida suzadi.
  const isFullscreen = (() => { try { return !!tg.isFullscreen; } catch (_) { return false; } })();

  if (top < 1) {
    // Telegram qiymat bermasa: fullscreen'da tugmalar (X/⋮) status bar ostida,
    // shuning uchun o'rtacha zaxira; oddiy rejimda kichik.
    top = isFullscreen ? 70 : 20;
  }
  // Fullscreen'da Telegram qiymat bersa ham, ba'zan tugmalar uchun kam bo'ladi —
  // kamida 70px kafolatlaymiz (tugmalar header bilan ustma-ust tushmasligi uchun).
  if (isFullscreen && top < 70) {
    top = 70;
  }
  document.documentElement.style.setProperty("--safe-top", top + "px");
  APP._safeAreaDebug = { content, device, isFullscreen, applied: top };
}

async function init() {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();

    // Fullscreen rejim — Telegram yuqori panelini (X/⋮ sarlavha) yashiradi, ilova
    // butun ekranni egallaydi (Bot API 8.0+). Eski klientlarda funksiya yo'q — xavfsiz.
    try {
      if (typeof tg.requestFullscreen === "function") {
        tg.requestFullscreen();
      }
    } catch (_) {}

    APP.currentUser = tg.initDataUnsafe?.user || null;

    // Fullscreen'da Telegram tugmalari (X/⋮) ekran ustida suzadi — kontent ular
    // ostidan boshlanishi uchun safe area qiymatini CSS o'zgaruvchisiga yozamiz.
    applySafeArea(tg);
    // Viewport barqarorlashgach qayta qo'llaymiz (fullscreen/expand qiymatni o'zgartiradi)
    setTimeout(() => applySafeArea(tg), 300);
    setTimeout(() => applySafeArea(tg), 800);
    // Qiymat keyinroq o'zgarsa (panel/fullscreen) — qayta qo'llaymiz
    if (typeof tg.onEvent === "function") {
      tg.onEvent("safeAreaChanged", () => applySafeArea(tg));
      tg.onEvent("contentSafeAreaChanged", () => applySafeArea(tg));
      tg.onEvent("viewportChanged", () => applySafeArea(tg));
      tg.onEvent("fullscreenChanged", () => applySafeArea(tg));
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
  bindScoreInputClear();  // Score kataklariga fokus berilganda 0 ni bo'shatadi
  applyIcons();           // Premium SVG ikonlarni joylashtirish (navigatsiya va h.k.)

  hideLoadingScreen();

  // Majburiy kanal a'zoligini tekshiramiz — a'zo bo'lmasa asosiy ilova ochilmaydi
  const subscribed = await checkChannelMembership();
  if (!subscribed) {
    showSubscribeGate();
    return;
  }

  showModeSelect();

  // Kubok yulduzchalari (2026-07-16) — bir marta yuklanadi, barcha rejimlar
  // reyting/profil renderlari APP.prizeStars'dan o'qiydi (bloklamaydi)
  void loadPrizeStars();

  // Mavsum yakuni tabrigi — bir martalik oyna (bloklamaydi, xato bo'lsa jim davom etadi)
  checkSeasonCelebration();
}

// ============================================================
//  MAJBURIY KANAL A'ZOLIGI
// ============================================================

// Backend orqali a'zolikni tekshiradi. Xato bo'lsa — true (bloklamaymiz).
async function checkChannelMembership() {
  try {
    const data = await apiFetch("/membership/check");
    APP.channelInfo = { url: data.channel_url, username: data.channel_username };
    APP.adminContact = { url: data.admin_contact_url, username: data.admin_contact_username };
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
      showModeSelect();
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
//  MODE SELECT — kirish rejimini tanlash (Liga / World Cup)
// ============================================================

// Tab 1 da ko'rsatiladigan 5 liga logosi (mavjud images/ fayllaridan).
const MODE_LEAGUE_LOGOS = [
  "images/laliga-logo.png",
  "images/premier-logo.png",
  "images/bundesliga-logo.png",
  "images/seriea-logo.png",
  "images/ligue1-logo.png",
];

// Tab 2 da ko'rsatiladigan davlat bayroqlari (emoji — yuklash kerak emas).
const MODE_WORLDCUP_FLAGS = ["🇧🇷", "🇦🇷", "🇫🇷", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "🇪🇸", "🇩🇪", "🇵🇹", "🇺🇿"];

// Loading/kanal tekshiruvidan keyin chiqadigan rejim tanlash ekrani.
// Tab 1 (ligalar) -> mavjud ilova (home). Tab 2 (World Cup) -> hozircha placeholder.
function showModeSelect() {
  const t = APP.t;
  const host = document.querySelector("main") || document.body;

  // Barcha bo'limlarni yashiramiz va pastki navigatsiyani ham (tanlovgacha kerak emas)
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  // Ligalar rejimidagi "Ortga" tugmasi rejim tanlash ekranida ko'rinmasin
  document.getElementById("league-back-btn")?.classList.add("hidden");

  let screen = document.getElementById("mode-select");
  if (!screen) {
    screen = document.createElement("div");
    screen.id = "mode-select";
    host.appendChild(screen);
  }
  screen.classList.remove("hidden");

  screen.innerHTML = `
    <div class="mode-select-title">${escHtml(t.mode_select_title || "REJIMNI TANLANG")}</div>
    <div class="mode-cards">
      <div class="mode-card mode-card--leagues mode-card--photo" id="mode-card-leagues">
        <img class="mode-banner" src="leagues-banner.jpg?v=1" alt=""
             onerror="this.style.display='none'">
        <div class="mode-banner-label">${escHtml(t.mode_leagues || "Ligalar")}</div>
      </div>
      <div class="mode-card mode-card--worldcup mode-card--photo" id="mode-card-worldcup">
        <img class="mode-banner" src="worldcup-banner-card.jpg?v=1" alt=""
             onerror="this.style.display='none'">
        <div class="mode-banner-label">${escHtml(t.mode_worldcup || "Jahon Chempionati")}</div>
      </div>
      <div class="mode-card mode-card--cl mode-card--photo" id="mode-card-cl">
        <img class="mode-banner" src="cl-banner.jpg?v=6" alt="${escHtml(t.mode_cl || "Chempionlar ligasi")}"
             onerror="this.style.display='none'">
      </div>
      <div class="mode-card mode-card--division mode-card--photo" id="mode-card-division">
        <img class="mode-banner" src="division-banner.jpg?v=6" alt=""
             onerror="this.style.display='none'">
        <div class="mode-banner-label">${escHtml(t.mode_division || "Divizion")}</div>
      </div>
    </div>
  `;

  document.getElementById("mode-card-leagues")
    .addEventListener("click", enterLeagueMode);
  document.getElementById("mode-card-worldcup")
    .addEventListener("click", enterWorldCupMode);
  document.getElementById("mode-card-cl")
    .addEventListener("click", enterChampionsLeagueMode);
  document.getElementById("mode-card-division")
    .addEventListener("click", enterDivisionMode);
}

// Rejim ekranini yashiradi (tanlangach asosiy interfeysga o'tish uchun)
function hideModeSelect() {
  const screen = document.getElementById("mode-select");
  if (screen) screen.classList.add("hidden");
}

// Tab 1: mavjud liga ilovasiga kirish
function enterLeagueMode() {
  hideModeSelect();
  document.querySelector(".bottom-nav")?.classList.remove("hidden");
  // "Ortga" tugmasi (rejim tanlashga qaytish) — faqat Ligalar rejimida ko'rinadi
  const backBtn = document.getElementById("league-back-btn");
  if (backBtn) {
    backBtn.classList.remove("hidden");
    if (!backBtn._bound) {           // bir marta bog'lanadi (takror listener yo'q)
      backBtn._bound = true;
      backBtn.addEventListener("click", exitLeagueMode);
    }
  }
  navigateTo("home");
}

// Ligalar rejimini yopib, rejim tanlashga qaytaradi (exitWorldCup naqshi)
function exitLeagueMode() {
  showModeSelect();   // bo'limlar, bottom-nav va "Ortga" tugmasi ichida yashiriladi
}

// Tab 2: World Cup — hozircha placeholder (2-bosqichda to'ldiriladi)
// Tab 2: World Cup rejimini ochadi (worldcup.js)
function enterWorldCupMode() {
  if (typeof showWorldCup === "function") {
    showWorldCup();
  } else {
    showToast(APP.t.worldcup_soon || "Jahon Chempionati tez orada ishga tushadi!");
  }
}

// Tab 3: Chempionlar ligasi rejimini ochadi (cl.js)
function enterChampionsLeagueMode() {
  if (typeof showChampionsLeague === "function") {
    showChampionsLeague();
  } else {
    showToast("Chempionlar ligasi tez orada ishga tushadi!");
  }
}

// Tab 4: Divizion rejimini ochadi (division.js)
function enterDivisionMode() {
  if (typeof showDivision === "function") {
    showDivision();
  } else {
    showToast("Divizion tez orada ishga tushadi!");
  }
}

// ============================================================
//  EVENT BINDINGS
// ============================================================

// Score kataklari (.score-input): fokus berilganda qiymat "0" bo'lsa bo'shatadi,
// shunda foydalanuvchi ustiga yozish o'rniga to'g'ridan-to'g'ri raqam kiritadi.
// Bo'sh qoldirilsa, fokus ketganda yana "0" ga qaytadi. Document darajasida —
// barcha hozirgi va keyin yaratiladigan score-input'larga ishlaydi.
function bindScoreInputClear() {
  document.addEventListener("focusin", (e) => {
    const el = e.target;
    if (el && el.classList && el.classList.contains("score-input")) {
      if (el.value === "0") el.value = "";
    }
  });
  document.addEventListener("focusout", (e) => {
    const el = e.target;
    if (el && el.classList && el.classList.contains("score-input")) {
      if (el.value.trim() === "") el.value = "0";
    }
  });
}

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

  // Hisob input'lari: dastlab "0" tursin, lekin raqam yozilganda 0 avtomatik o'chsin
  // (03 yoki 30 bo'lib qolmasligi uchun). Bo'sh qolsa — 0 qaytadi.
  ["input-score1", "input-score2"].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    // Maydonga bosilganda 0 bo'lsa tozalaymiz (yangi raqam toza kiritilsin)
    el.addEventListener("focus", () => {
      if (el.value === "0") el.value = "";
    });
    // Yozilganda boshidagi keraksiz nollarni olib tashlaymiz: "03" -> "3", "30" -> "30"
    el.addEventListener("input", () => {
      let v = el.value.replace(/[^0-9]/g, "");      // faqat raqam
      if (v.length > 1) v = v.replace(/^0+/, "");    // boshidagi 0(lar)ni olib tashlaymiz
      if (v === "") v = "";
      // Maksimal 2 xona (99 gacha)
      if (v.length > 2) v = v.slice(0, 2);
      el.value = v;
    });
    // Maydondan chiqilganda bo'sh bo'lsa — 0 qaytadi
    el.addEventListener("blur", () => {
      if (el.value === "") el.value = "0";
    });
  });

  // Natija tasdiqlash modal (yolg'on natija oldini olish)
  document.getElementById("btn-confirm-yes")
    .addEventListener("click", () => {
      const id = APP._confirmMatchId;
      closeConfirmModal();
      if (id) confirmMatchResult(id, "confirm");
    });
  document.getElementById("btn-confirm-no")
    .addEventListener("click", () => {
      const id = APP._confirmMatchId;
      closeConfirmModal();
      if (id) confirmMatchResult(id, "reject");
    });
  document.getElementById("btn-confirm-cancel")
    .addEventListener("click", closeConfirmModal);

  // Admin: rad etilgan natijani belgilash modali
  document.getElementById("btn-admin-resolve-cancel")
    .addEventListener("click", closeAdminResolveModal);
  document.getElementById("btn-admin-resolve-submit")
    .addEventListener("click", submitAdminSetResult);

  // Admin: tasdiqlangan natijani tuzatish formasi
  document.getElementById("btn-admin-fix-submit")
    .addEventListener("click", submitAdminFixConfirmed);

  // Admin: natijani bekor qilish (2026-07-16) — o'yin pending holatiga qaytadi
  document.getElementById("btn-admin-cancel-result")
    ?.addEventListener("click", submitAdminCancelResult);

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
