/**
 * app.js — eFootball Turnir WebApp
 * Init, til tizimi (UZ/RU/EN), navigatsiya, toast, eventlar.
 * api.js bilan birga ishlaydi — u APP global ob'ektidan foydalanadi.
 */

// ============================================================
//  GLOBAL STATE
// ============================================================

const APP = {
  currentUser:     null,   // Telegram foydalanuvchisi
  leagues:         [],     // /leagues javobi
  selectedLeagueId: null,  // Tanlangan liga
  profileData:     null,   // /profile javobi
  activeMatchId:   null,   // Natija kiritish uchun
  lang:            "uz",   // Joriy til
  t:               {},     // Aktiv tarjimalar
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
    register:        "Ro'yxatdan o'tish",
    choose_league:   "LIGA TANLASH",
    open:            "OCHIQ",
    full:            "TO'LIQ",
    league_open:     "OCHIQ — RO'YXAT DAVOM ETMOQDA",
    league_full:     "TO'LIQ",
    rules:           "Qoidalar",
    rules_list: [
      "Har bir o'yinchi boshqa barcha o'yinchilar bilan 2 marta o'ynaydi (uy va mehmonda).",
      "G'alaba uchun 3 ball, durang uchun 1 ball, mag'lubiyat uchun 0 ball.",
      "Natijani o'yin tugagach 24 soat ichida kiritish shart.",
      "Raqib natijani tasdiqlashi yoki rad etishi mumkin.",
      "Rad etilgan natija admin ko'rib chiqadi.",
    ],
    // Rating
    rating_title: "REYTING JADVALI",
    th_player: "O'yinchi",
    th_pts: "B",
    th_w:   "G",
    th_d:   "D",
    th_l:   "M",
    th_gd:  "GF",
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
    // Prizes
    prizes_title:       "SOVRINLAR",
    golden_boot:        "Oltin Butsa",
    golden_boot_desc:   "Eng ko'p gol urgan o'yinchi",
    golden_ball:        "Oltin To'p",
    golden_ball_desc:   "Turnir g'olibi",
    by_league:          "LIGA BO'YICHA",
    goals:              "gol",
  },

  ru: {
    nav_home:    "Главная",
    nav_rating:  "Рейтинг",
    nav_profile: "Профиль",
    nav_prizes:  "Призы",
    players:         "Игроки",
    max_players:     "Максимум",
    matchday:        "Тур",
    register:        "Зарегистрироваться",
    choose_league:   "ВЫБОР ЛИГИ",
    open:            "ОТКРЫТА",
    full:            "ЗАПОЛНЕНА",
    league_open:     "ОТКРЫТА — РЕГИСТРАЦИЯ ИДЁТ",
    league_full:     "ЗАПОЛНЕНА",
    rules:           "Правила",
    rules_list: [
      "Каждый игрок играет с каждым дважды (дома и в гостях).",
      "За победу 3 очка, за ничью 1, за поражение 0.",
      "Результат нужно внести в течение 24 часов после игры.",
      "Соперник может подтвердить или отклонить результат.",
      "Отклонённый результат рассматривает администратор.",
    ],
    rating_title: "ТАБЛИЦА РЕЙТИНГА",
    th_player: "Игрок",
    th_pts: "О",
    th_w:   "П",
    th_d:   "Н",
    th_l:   "П",
    th_gd:  "ЗГ",
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
    prizes_title:       "ПРИЗЫ",
    golden_boot:        "Золотая Бутса",
    golden_boot_desc:   "Лучший бомбардир турнира",
    golden_ball:        "Золотой Мяч",
    golden_ball_desc:   "Победитель турнира",
    by_league:          "ПО ЛИГЕ",
    goals:              "голов",
  },

  en: {
    nav_home:    "Home",
    nav_rating:  "Rating",
    nav_profile: "Profile",
    nav_prizes:  "Prizes",
    players:         "Players",
    max_players:     "Max",
    matchday:        "Round",
    register:        "Register",
    choose_league:   "CHOOSE LEAGUE",
    open:            "OPEN",
    full:            "FULL",
    league_open:     "OPEN — REGISTRATION ONGOING",
    league_full:     "FULL",
    rules:           "Rules",
    rules_list: [
      "Every player plays against every other player twice (home & away).",
      "Win = 3 pts, Draw = 1 pt, Loss = 0 pts.",
      "Results must be submitted within 24 hours after the match.",
      "The opponent can confirm or reject the result.",
      "Rejected results are reviewed by the admin.",
    ],
    rating_title: "STANDINGS",
    th_player: "Player",
    th_pts: "Pts",
    th_w:   "W",
    th_d:   "D",
    th_l:   "L",
    th_gd:  "GF",
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
    prizes_title:       "PRIZES",
    golden_boot:        "Golden Boot",
    golden_boot_desc:   "Top scorer of the tournament",
    golden_ball:        "Golden Ball",
    golden_ball_desc:   "Tournament winner",
    by_league:          "BY LEAGUE",
    goals:              "goals",
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
  document.getElementById("header-lang").textContent = APP.lang.toUpperCase();
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

function init() {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    APP.currentUser = tg.initDataUnsafe?.user || null;

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
  hideLoadingScreen();
  navigateTo("home");
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
  document.getElementById("btn-edit-nickname")
    .addEventListener("click", openNicknameModal);
  document.getElementById("btn-nickname-cancel")
    .addEventListener("click", closeNicknameModal);
  document.getElementById("btn-nickname-save")
    .addEventListener("click", saveNickname);

  // Natija modal
  document.getElementById("btn-result-cancel")
    .addEventListener("click", closeResultModal);
  document.getElementById("btn-result-submit")
    .addEventListener("click", submitMatchResult);

  // Modal tashqarisiga bosish — yopish
  document.getElementById("modal-nickname").addEventListener("click", e => {
    if (e.target === e.currentTarget) closeNicknameModal();
  });
  document.getElementById("modal-result").addEventListener("click", e => {
    if (e.target === e.currentTarget) closeResultModal();
  });
}

// ============================================================
//  START
// ============================================================

document.addEventListener("DOMContentLoaded", init);
