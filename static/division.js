// ============================================================
//  division.js — Divizion (3-tab) ekrani
//  Alohida ekran (cl.js/worldcup.js naqshi). Mavjud kodga TEGMAYDI.
//  Sahifalar: Asosiy | Reyting | Profil | Sovrinlar
//
//  Bog'liqliklar (global): APP, apiFetch (api.js), escHtml (api.js), showToast,
//  hideModeSelect, showModeSelect.
//  Backend: /div/status, /div/register, /div/rating,
//           /div/match/submit-result, /div/match/confirm, /div/chat/{id}
// ============================================================

const DIV = {
  section: "home",   // home | rating | profile | prizes | admin | player
  status: null,      // /div/status javobi
  rating: [],
  adminMatches: [],  // admin panel ro'yxati
  adminDay: null,    // null = bugun, "all" = barcha kunlar
  adminFixId: "",    // "Match ID orqali tuzatish" formasidagi ID
  adminFixInfo: null,// o'sha ID bo'yicha o'yin ma'lumoti | "notfound" | null
  player: null,      // ochilgan ishtirokchi profili (/div/player/{id}/profile)
  playerBackTo: "rating",  // profildan ortga qaysi bo'limga qaytamiz
  calendar: null,    // /div/calendar javobi {month, today, days[]}
  calMonth: null,    // ko'rilayotgan oy "YYYY-MM" (null = joriy)
  ratingTab: "points",  // "points" (ball) | "scorers" (to'p urarlar)
  playerCalMonth: null, // boshqa ishtirokchi profilidagi kalendar oyi
  scorers: [],
  unread: { total: 0, by_match: {} }, // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka)
};

// ---- Kirish nuqtasi ----
function showDivision() {
  if (typeof hideModeSelect === "function") hideModeSelect();
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));

  let root = document.getElementById("div-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "div-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  DIV.section = "home";
  void divLoadStatus();
}

function exitDivision() {
  if (typeof closeWebChat === "function") closeWebChat();
  const root = document.getElementById("div-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function divNavigate(section) {
  DIV.section = section;
  renderDivision();
  // 2026-07-19: har sahifada o'qilmagan rozetkani yangilab turamiz (liga naqshi)
  void divRefreshUnreadBadge();
  if (section === "rating") {
    if (DIV.ratingTab === "scorers") void divLoadScorers();
    else void divLoadRating();
  }
  if (section === "home" || section === "profile") void divLoadStatus();
  if (section === "profile") void divLoadCalendar(DIV.calMonth);   // ro'yxat kalendari
  if (section === "admin") void divLoadAdminMatches();
}

async function divLoadStatus() {
  try {
    DIV.status = await apiFetch("/div/status");
  } catch (_) { DIV.status = null; }
  // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka) — liga loadMyMatches naqshi
  try {
    DIV.unread = await apiFetch("/div/matches/unread");
  } catch (_) {
    DIV.unread = { total: 0, by_match: {} };
  }
  renderDivision();
}

// 2026-07-19: Divizion o'qilmagan soni — "Asosiy" nav tugmasidagi qizil rozetka
// (Divizion chati bugungi o'yin kartasida — Asosiy sahifada joylashgan).
async function divRefreshUnreadBadge() {
  try {
    DIV.unread = await apiFetch("/div/matches/unread");
  } catch (_) {
    DIV.unread = { total: 0, by_match: {} };
  }
  divUpdateNavBadge();
}

function divUpdateNavBadge() {
  if (typeof setNavBadge !== "function") return;
  setNavBadge(
    document.querySelector('#div-root .wc-nav-item[data-div-tab="home"]'),
    (DIV.unread && DIV.unread.total) || 0
  );
}

async function divLoadScorers() {
  try {
    const d = await apiFetch("/div/scorers");
    DIV.scorers = d.scorers || [];
    DIV.ratingMeId = d.me_id;
  } catch (_) { DIV.scorers = []; }
  renderDivision();
}

async function divLoadRating() {
  try {
    const d = await apiFetch("/div/rating");
    DIV.rating = d.rating || [];
    DIV.ratingMeId = d.me_id;
  } catch (_) { DIV.rating = []; }
  renderDivision();
}

// ---- RENDER ----
function renderDivision() {
  const root = document.getElementById("div-root");
  if (!root) return;

  let body = "";
  if (DIV.section === "home") body = divRenderHome();
  else if (DIV.section === "rating") body = divRenderRating();
  else if (DIV.section === "profile") body = divRenderProfile();
  else if (DIV.section === "admin") body = divRenderAdmin();
  else if (DIV.section === "player") body = divRenderPlayer();
  else body = divRenderPrizes();

  const adminNav = DIV.status?.is_admin ? `
      <button class="wc-nav-item ${DIV.section === "admin" ? "active" : ""}" data-div-tab="admin">
        <span class="nav-icon" data-icon="clipboard"></span>
        <span class="nav-label">Admin</span>
      </button>` : "";

  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="div-back-btn">←</button>
      <div class="wc-header-title">Divizion</div>
    </div>
    <div class="wc-body" style="padding-bottom:90px;">${body}</div>
    <nav class="wc-nav">
      <button class="wc-nav-item ${DIV.section === "home" ? "active" : ""}" data-div-tab="home">
        <span class="nav-icon" data-icon="home"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_home) || "Asosiy"}</span>
      </button>
      <button class="wc-nav-item ${DIV.section === "rating" ? "active" : ""}" data-div-tab="rating">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_rating) || "Reyting"}</span>
      </button>
      <button class="wc-nav-item ${DIV.section === "profile" ? "active" : ""}" data-div-tab="profile">
        <span class="nav-icon" data-icon="user"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_profile) || "Profil"}</span>
      </button>
      <button class="wc-nav-item ${DIV.section === "prizes" ? "active" : ""}" data-div-tab="prizes">
        <span class="nav-icon" data-icon="gift"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_prizes) || "Sovrinlar"}</span>
      </button>${adminNav}
    </nav>
  `;

  if (typeof applyIcons === "function") applyIcons(root);
  // 2026-07-19: nav har renderda qayta quriladi — rozetkani qayta qo'yamiz
  divUpdateNavBadge();
  document.getElementById("div-back-btn").addEventListener("click", exitDivision);
  root.querySelectorAll("[data-div-tab]").forEach(b =>
    b.addEventListener("click", () => divNavigate(b.dataset.divTab)));
  divBindSectionEvents(root);
}


// ---- ASOSIY: ro'yxat oynasi + bugungi ro'yxat ----
function divRuleText(r) {
  // Liga/WC bilan bir xil: **so'z** → cyan qalin (XSS uchun avval escHtml)
  return escHtml(r).replace(/\*\*([^*]+)\*\*/g, '<strong class="rule-hl">$1</strong>');
}

function divRulesCard() {
  const rules = (APP.t && APP.t.div_rules_list) || [];
  const items = rules.map(r => `<li>${divRuleText(r)}</li>`).join("");
  return `
    <div class="card card--flat">
      <div class="card-header">
        <span class="card-header-icon" data-icon="clipboard"></span>
        <span class="card-header-text">${DT("div_rules_title")}</span>
      </div>
      <ul class="rules-list">${items}</ul>
    </div>`;
}

// Dumaloq avatar (telegram rasmi, bo'lmasa ism harfi). size — px.
function divAvatarHtml(userId, name, size = 52, photoUrl = null) {
  const initial = (name || "?").charAt(0).toUpperCase();
  const fbStyle = `width:${size}px;height:${size}px;border-radius:50%;align-items:center;` +
    `justify-content:center;font-size:${Math.round(size * 0.42)}px;font-weight:800;flex:none;` +
    `background:linear-gradient(140deg,#7c5cff,#31d0aa);color:#fff`;
  const src = photoUrl ? escHtml(photoUrl) : (userId ? `${API_BASE}/players/${userId}/photo` : null);
  if (!src) return `<div style="display:flex;${fbStyle}">${escHtml(initial)}</div>`;
  return `<img src="${src}" alt=""
      style="width:${size}px;height:${size}px;border-radius:50%;object-fit:cover;flex:none"
      onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"
    ><div style="display:none;${fbStyle}">${escHtml(initial)}</div>`;
}

// Asosiy sahifadagi qur'a/o'yin bloki: RAQIB (bosiladi) — hisob — MEN
// 2026-07-16: karta foni — division-bg.jpg (stadion rasmi); ustidagi barcha
// elementlar (o'yinchilar, hisob, tugmalar, holat yozuvlari) SHISHA uslubida.
function divTodayMatchCard() {
  const s = DIV.status;
  const m = s && s.my_match;
  if (!m) return "";
  if (m.is_bye) {
    return `<div class="card div-match-hero">
      <div class="div-glass div-match-note" style="border-color:rgba(245,197,66,.5)">${DT("div_bye_note")}</div>
    </div>`;
  }
  const opp = m.opponent || {};
  const p1IsMe = (m.player1_id === s.me_id);
  // 2026-07-19: QAT'IY TARTIB — ikkala telefonda ham bir xil ko'rinishi uchun
  // chapda DOIM player1, o'ngda DOIM player2 (nisbiy "raqib/men" emas).
  // Hisob ham doim score1 : score2 (bazadagi tartib) — adashish yo'qoladi.
  const p1 = { id: m.player1_id, name: m.player1_name, username: m.player1_username, isMe: p1IsMe };
  const p2 = { id: m.player2_id, name: m.player2_name, username: m.player2_username, isMe: !p1IsMe };

  const score1 = (m.score1 !== null && m.score1 !== undefined) ? m.score1 : "—";
  const score2 = (m.score1 !== null && m.score1 !== undefined) ? m.score2 : "—";

  let actions = "";
  if (m.status === "pending") {
    actions = `<button class="btn btn--primary btn--glow" id="div-btn-open-result" style="width:100%;margin-top:10px">${DT("div_submit_result")}</button>`;
  } else if (m.status === "awaiting_confirmation") {
    actions = (m.submitted_by !== s.me_id)
      ? `<div style="display:flex;gap:8px;margin-top:10px">
           <button class="btn btn--primary" id="div-btn-confirm" style="flex:1">${DT("div_confirm")}</button>
           <button class="btn btn--ghost" id="div-btn-reject" style="flex:1">${DT("div_reject")}</button>
         </div>`
      : `<div class="div-glass div-match-note">${DT("div_wait_opponent")}</div>`;
  } else if (m.status === "admin_pending") {
    actions = `<div class="div-glass div-match-note">${DT("div_wait_admin")}</div>`;
  } else if (m.status === "confirmed") {
    actions = `<div class="div-glass div-match-note">${DT("div_result_confirmed")}</div>`;
  }

  return `
    <div class="card div-match-hero">
      <div class="div-glass div-match-chip">${DT("div_today_match")}</div>
      <div style="display:flex;align-items:stretch;justify-content:space-between;gap:8px">
        ${[p1, p2].map(p => `
        <div class="div-vs-player div-glass div-match-side" ${p.isMe ? "" : 'id="div-opp-profile-open"'} style="flex:1">
          ${divAvatarHtml(p.id, p.name, 56, p.isMe ? (APP.currentUser && APP.currentUser.photo_url) : null)}
          <div style="font-size:14px;font-weight:800;text-align:center">${escHtml(p.name || "—")}</div>
          ${p.username
            ? `<div style="font-size:11.5px;${p.isMe ? "opacity:.85" : "color:var(--cyan)"}">@${escHtml(p.username)}</div>`
            : ""}
        </div>`).join(`<div class="div-glass div-match-score">${score1} : ${score2}</div>`)}
      </div>
      <button class="btn btn--ghost" id="div-btn-opponent" style="width:100%;margin-top:12px;position:relative">${DT("div_contact_opponent")}${
        (() => {
          // 2026-07-19: shu o'yindagi o'qilmagan xabarlar — tugma ustida qizil rozetka
          const c = (DIV.unread && DIV.unread.by_match && DIV.unread.by_match[m.id]) || 0;
          return c > 0 ? `<span class="chat-badge" style="top:-7px;right:-4px">${c > 9 ? "9+" : c}</span>` : "";
        })()
      }</button>
      ${actions}
    </div>`;
}

// 2026-07-21: Mavsum chizig'i — hero fon rasmi USTIDA, matn TEPASIDA.
// Uchta raqam: mavsum boshlanganiga necha kun bo'ldi | tugashiga qolgan kun |
// nechinchi mavsum. Orqasi shisha uslubida (.div-glass — boshqa rejimlardagidek).
// Ma'lumot: /div/status → season {number, day_index, days_left} (division_season.py).
// 2026-07-21: tarjima yordamchisi — APP.t dan kalitni oladi; til yuklanmagan
// yoki kalit yo'q bo'lsa DIV_TEXTS.uz dagi o'zbekcha matn zaxira sifatida ishlatiladi
// (texts_division.js). Shu tufayli har chaqiruvda uzun fallback yozish shart emas.
function DT(key) {
  if (APP && APP.t && APP.t[key] !== undefined) return APP.t[key];
  if (typeof DIV_TEXTS !== "undefined" && DIV_TEXTS.uz[key] !== undefined) return DIV_TEXTS.uz[key];
  return "";
}

function divSeasonStrip() {
  const se = (DIV.status && DIV.status.season) || null;
  if (!se) return "";                       // ma'lumot yo'q — chiziq ko'rsatilmaydi
  const t = APP.t || {};
  const cell = (value, label) => `
    <div class="div-season-cell div-glass">
      <div class="div-season-num">${value}</div>
      <div class="div-season-label">${escHtml(label)}</div>
    </div>`;
  return `
    <div class="div-season-strip">
      ${cell(se.day_index, DT("div_season_elapsed"))}
      ${cell(se.days_left, DT("div_season_left"))}
      ${cell(se.number, (APP.t && APP.t.season) || "Mavsum")}
    </div>`;
}

function divRenderHome() {
  const s = DIV.status;
  if (!s) return `<div class="card">${DT("div_load_failed")}</div>`;
  const win = s.window || {};

  // OYNA OCHIQ (17:00–19:00): ro'yxat tugmasi + bugungi ishtirokchilar ro'yxati
  if (win.open) {
    let regBlock;
    if (s.me_registered) {
      regBlock = `<div class="card" style="border-color:rgba(49,208,170,.5)">${DT("div_reg_done")}</div>`;
    } else {
      regBlock = `
        <div class="card">
          <b>${DT("div_reg_open_title")}</b>
          <div style="font-size:12.5px;opacity:.75;margin:4px 0 10px">${DT("div_now")}: ${escHtml(win.now || "")}. ${DT("div_reg_open_hint")}</div>
          <button class="btn btn--primary" id="div-btn-register" style="width:100%">${DT("div_reg_button")}</button>
        </div>`;
    }
    const regs = s.registrations || [];
    const list = regs.length
      ? regs.map((r, i) => `
          <div class="match-item">
            <b>${i + 1}. ${escHtml(r.nickname || DT("div_participant"))}</b>
            ${r.username ? `<span style="font-size:12px;opacity:.7">@${escHtml(r.username)}</span>` : ""}
          </div>`).join("")
      : `<div style="font-size:13px;opacity:.7">${DT("div_reg_empty")}</div>`;
    return `${regBlock}
      <div class="card"><b>${DT("div_reg_today_list")} (${regs.length})</b><div style="margin-top:8px">${list}</div></div>`;
  }

  // OYNA YOPIQ: bugungi o'yin (natija kiritish) + qoidalar. Ro'yxat ko'rsatilmaydi.
  // 2026-07-16: "Ro'yxat yopiq..." yozuvi endi fon rasmi (division-bg.jpg,
  // xiralashtirilmagan) USTIDA turadi; qoidalar kartasi fon rasmi OSTIDA.
  const todayCard = divTodayMatchCard();
  const noMatchHint = (!s.my_match)
    ? `<div class="div-hero">
         ${divSeasonStrip()}
         <div class="div-hero-text">${DT("div_reg_closed")}<br>${DT("div_now")}: ${escHtml(win.now || "")}.</div>
       </div>`
    : "";
  return `${todayCard}${noMatchHint}${divRulesCard()}`;
}

// ---- REYTING: umumiy achko jadvali (+15/+10/-10) ----
function divRenderRating() {
  const list = DIV.rating || [];
  const meId = DIV.ratingMeId;
  const myIndex = list.findIndex(p => p.user_id === meId);
  const myRank = myIndex >= 0 ? myIndex + 1 : null;

  // 4) "SIZNING O'RNINGIZ" qatori — bosilsa jadval o'sha qatorga suriladi
  const myRankCard = myRank
    ? `<div class="card div-myrank" id="div-myrank-card">
         <div>
           <div style="font-size:12px;opacity:.65">${DT("div_my_rank")}</div>
           <div style="font-size:26px;font-weight:800" class="neon-cyan">${myRank}</div>
         </div>
         <div style="text-align:right">
           <div style="font-size:12px;opacity:.65">${DT("div_points")}</div>
           <div style="font-size:20px;font-weight:800">${list[myIndex].rating ?? 1500}</div>
         </div>
         <div class="div-myrank-hint">${DT("div_show")}</div>
       </div>`
    : `<div class="card" style="font-size:13px;opacity:.75">${DT("div_not_rated")}</div>`;

  const rows = list.map((p, i) => {
    const isMe = meId && p.user_id === meId;
    // Ism o'rniga USERNAME (username yo'q bo'lsa — ism), bosilsa profil ochiladi
    const label = p.username ? "@" + p.username : (p.nickname || "—");
    // Umumiy ball (1500 + achkolar) — profildagi ball bilan bir xil
    const ball = (p.rating !== undefined && p.rating !== null) ? p.rating : 1500;
    return `
      <tr class="${isMe ? "is-me" : ""} div-rating-row" id="${isMe ? "div-my-rating-row" : ""}"
          data-uid="${p.user_id}" style="cursor:pointer">
        <td class="rank-${i + 1}">${i + 1}</td>
        <td class="div-rating-user">${escHtml(label)}${prizeStarsHtml(p)}</td>
        <td>${p.played}</td>
        <td><b class="neon-cyan">${ball}</b></td>
      </tr>`;
  }).join("");

  // Tab tanlash: Achko reytingi | To'p urarlar
  const tabs = `
    <div class="div-rating-tabs">
      <button class="tab-btn ${DIV.ratingTab !== "scorers" ? "active" : ""}" data-div-rtab="points">${DT("div_tab_rating")}</button>
      <button class="tab-btn ${DIV.ratingTab === "scorers" ? "active" : ""}" data-div-rtab="scorers">${DT("div_tab_scorers")}</button>
    </div>`;

  if (DIV.ratingTab === "scorers") return tabs + divRenderScorers();

  // 1) Sarlavha to'liq ko'rinishi uchun alohida kartada (jadval ustida, kesilmaydi)
  return `
    ${tabs}
    ${myRankCard}
    <div class="card div-rating-legend">${DT("div_legend")}</div>
    <div class="card card--table">
      <table class="rating-table">
        <thead><tr><th>#</th><th>${DT("div_col_player")}</th><th>${DT("div_col_played")}</th><th>${DT("div_points")}</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4">${DT("div_no_results")}</td></tr>`}</tbody>
      </table>
    </div>`;
}

// To'p urarlar: eng ko'p gol urganlar (o'z hisobidagi gollar yig'indisi)
function divRenderScorers() {
  const list = DIV.scorers || [];
  const meId = DIV.ratingMeId;

  if (!list.length) {
    return `<div class="card" style="opacity:.75;font-size:13px">${DT("div_no_goals")}</div>`;
  }

  const rows = list.map((p, i) => {
    const isMe = meId && p.user_id === meId;
    const label = p.username ? "@" + p.username : (p.nickname || "—");
    return `
      <tr class="${isMe ? "is-me" : ""} div-rating-row" data-uid="${p.user_id}" style="cursor:pointer">
        <td class="rank-${i + 1}">${i + 1}</td>
        <td class="div-rating-user">${escHtml(label)}${prizeStarsHtml(p)}</td>
        <td>${p.played}</td>
        <td><b class="neon-cyan">${p.goals_for}</b></td>
      </tr>`;
  }).join("");

  // Mening o'rnim (to'p urarlar bo'yicha)
  const myIdx = list.findIndex(p => p.user_id === meId);
  const myCard = myIdx >= 0
    ? `<div class="card div-myrank" id="div-myscorer-card">
         <div>
           <div style="font-size:12px;opacity:.65">${DT("div_my_rank")}</div>
           <div style="font-size:26px;font-weight:800" class="neon-cyan">${myIdx + 1}</div>
         </div>
         <div style="text-align:right">
           <div style="font-size:12px;opacity:.65">${DT("div_col_goals")}</div>
           <div style="font-size:20px;font-weight:800">${list[myIdx].goals_for}</div>
         </div>
         <div class="div-myrank-hint">${DT("div_show")}</div>
       </div>`
    : "";

  return `
    ${myCard}
    <div class="card div-rating-legend">${DT("div_scorers_legend")}</div>
    <div class="card card--table">
      <table class="rating-table">
        <thead><tr><th>#</th><th>${DT("div_col_player")}</th><th>${DT("div_col_played")}</th><th>${DT("div_col_goals")}</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

// ---- PROFIL: liga uslubida (statistika + o'yinlar tarixi + raqib) ----
function divStatusLabelShort(st) {
  return ({ pending: "KUTILMOQDA", awaiting_confirmation: "TASDIQ KUTILMOQDA",
            admin_pending: "ADMIN TASDIG'I", confirmed: "TASDIQLANDI" })[st] || st;
}

// ---- RO'YXAT KALENDARI (profil) ----
async function divLoadCalendar(month) {
  const q = month ? `?month=${encodeURIComponent(month)}` : "";
  try {
    DIV.calendar = await apiFetch(`/div/calendar${q}`);
    DIV.calMonth = DIV.calendar.month;
  } catch (e) {
    DIV.calendar = null;
    showToast("Kalendar yuklanmadi: " + e.message);
  }
  renderDivision();
}

// "YYYY-MM" ga n oy qo'shadi (n manfiy bo'lishi mumkin)
function divShiftMonth(ym, n) {
  const [y, m] = ym.split("-").map(Number);
  const d = new Date(y, m - 1 + n, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

const DIV_MONTH_NAMES = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
  "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"];

// Kalendar HTML — o'z profilim va boshqa ishtirokchi profili uchun BIR XIL (DRY).
// 2026-07-17: O'yin tarixi qatorida achko o'zgarishi belgisi (DRY — o'z profil
// va boshqa ishtirokchi profili). myScore — qaralayotgan o'yinchi nuqtai nazaridan.
function divHistDeltaBadge(status, hasScore, myScore, oppScore) {
  if (status !== "confirmed" || !hasScore) return "";
  if (myScore > oppScore) return `<span class="div-hist-delta">+15</span>`;
  if (myScore === oppScore) return `<span class="div-hist-delta div-hist-delta--draw">+10</span>`;
  return `<span class="div-hist-delta div-hist-delta--loss">−10</span>`;
}

// mode: "me" (o'z profilim, /div/calendar) | "player" (boshqa ishtirokchi)
function divCalendarHtml(cal, mode = "me") {
  if (!cal) {
    return `<div class="section-label">RO'YXAT KALENDARI</div>
      <div class="card" style="opacity:.7;font-size:13px">${DT("div_loading")}</div>`;
  }

  const [year, month] = cal.month.split("-").map(Number);
  const marked = new Set(cal.days || []);       // ro'yxatdan o'tilgan kunlar
  const banned = new Set(cal.banned || []);     // 2026-07-17: ban kunlari (qizil)
  const today = cal.today;

  const first = new Date(year, month - 1, 1);
  const offset = (first.getDay() + 6) % 7;      // Dushanba = 0
  const daysInMonth = new Date(year, month, 0).getDate();

  const wd = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    .map(d => `<div class="div-cal-wd">${d}</div>`).join("");

  let cells = "";
  for (let i = 0; i < offset; i++) cells += `<div class="div-cal-cell div-cal-cell--empty"></div>`;
  for (let d = 1; d <= daysInMonth; d++) {
    const iso = `${cal.month}-${String(d).padStart(2, "0")}`;
    const cls = ["div-cal-cell"];
    if (marked.has(iso)) cls.push("div-cal-cell--on");   // yashil = ro'yxatdan o'tgan
    if (banned.has(iso)) cls.push("div-cal-cell--ban");  // qizil = ban kuni (ustuvor)
    if (iso === today) cls.push("div-cal-cell--today");
    cells += `<div class="${cls.join(" ")}">${d}</div>`;
  }

  const count = (cal.days || []).length;
  const banLegend = banned.size
    ? `<span class="div-cal-dot div-cal-dot--ban" style="margin-left:10px"></span> ${DT("div_cal_ban")}`
    : "";
  const navAttr = (mode === "player") ? "data-div-pcal" : "data-div-cal";
  return `
    <div class="section-label">RO'YXAT KALENDARI</div>
    <div class="card div-cal-card">
      <div class="div-cal-head">
        <button class="div-cal-nav" ${navAttr}="prev">‹</button>
        <div class="div-cal-title">${DIV_MONTH_NAMES[month - 1]} ${year}</div>
        <button class="div-cal-nav" ${navAttr}="next">›</button>
      </div>
      <div class="div-cal-grid">${wd}${cells}</div>
      <div class="div-cal-legend">
        <span class="div-cal-dot div-cal-dot--on"></span> Ro'yxatdan o'tilgan kun${banLegend}
        <b style="margin-left:auto">${count} kun</b>
      </div>
    </div>`;
}

function divRenderProfile() {
  const s = DIV.status;
  if (!s) return `<div class="card">Ma'lumot yuklanmadi.</div>`;

  const st = s.stats || { wins: 0, draws: 0, losses: 0, win_rate: 0 };

  // 1) MENING profil kartam (liga uslubi): rasm + ism + username
  const myInitial = (s.me_nickname || "?").charAt(0).toUpperCase();
  const myPhoto = (APP.currentUser && APP.currentUser.photo_url)
    ? `<img src="${escHtml(APP.currentUser.photo_url)}" alt=""
           style="width:56px;height:56px;border-radius:50%;object-fit:cover"
           onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
       <div style="display:none;width:56px;height:56px;border-radius:50%;
           align-items:center;justify-content:center;font-size:24px;font-weight:800;
           background:linear-gradient(140deg,#7c5cff,#31d0aa);color:#fff">${escHtml(myInitial)}</div>`
    : `<div style="width:56px;height:56px;border-radius:50%;display:flex;
           align-items:center;justify-content:center;font-size:24px;font-weight:800;
           background:linear-gradient(140deg,#7c5cff,#31d0aa);color:#fff">${escHtml(myInitial)}</div>`;

  // Umumiy ball: 1500 (boshlang'ich) + o'yin achkolari (+15/+10/-10)
  const rating = (st.rating !== undefined && st.rating !== null) ? st.rating : 1500;

  const meCard = `
    <div class="card">
      <div style="display:flex;align-items:center;gap:12px">
        ${myPhoto}
        <div style="min-width:0;flex:1">
          <div style="font-size:18px;font-weight:800;overflow:hidden;text-overflow:ellipsis">${escHtml(s.me_nickname || "—")}</div>
          ${s.me_username ? `<div style="font-size:12.5px;opacity:.7">@${escHtml(s.me_username)}${prizeStarsHtml({ user_id: s.me_user_id, telegram_id: APP.currentUser?.id, username: s.me_username })}</div>` : ""}
        </div>
        <div class="div-ball" title="${DT("div_start_rating_hint")}">
          <div class="div-ball-value">${rating}</div>
          <div class="div-ball-label">BALL</div>
        </div>
      </div>
    </div>`;

  // 2) STATISTIKA — o'rin o'rniga G'alaba foizi
  const statsGrid = `
    <div class="section-label">STATISTIKA</div>
    <div class="stats-grid">
      <div class="stat-card stat-card--primary">
        <span class="stat-card-value neon-cyan">${st.win_rate}%</span>
        <span class="stat-card-label">G'alaba foizi</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-cyan">${st.wins}</span>
        <span class="stat-card-label">${DT("div_wins")}</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value">${st.draws}</span>
        <span class="stat-card-label">${DT("div_draws")}</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-red">${st.losses}</span>
        <span class="stat-card-label">${DT("div_losses")}</span>
      </div>
    </div>`;

  // 3) O'YIN TARIXI — raqib useri bilan, bosilsa raqib profili ochiladi
  const hist = s.history || [];
  const histRows = hist.map((h, i) => {
    if (h.is_bye) {
      return `<div class="match-item">
        <span style="opacity:.55;font-size:11px;min-width:34px">#${h.id}</span>
        <b style="flex:1;text-align:center">${DT("div_auto_win")}</b>
        <span class="status-badge status--confirmed">+15</span>
      </div>`;
    }
    const hasScore = (h.my_score !== null && h.my_score !== undefined);
    const score = hasScore ? `${h.opp_score} : ${h.my_score}` : "— : —";
    // 2026-07-17: har bir tasdiqlangan o'yinda achko o'zgarishi (hammaga ko'rinadi):
    // g'alaba +15 (yashil), durang +10 (moviy), mag'lubiyat −10 (qizil)
    const winBadge = divHistDeltaBadge(h.status, hasScore, h.my_score, h.opp_score);
    const canOpen = !!h.opp_user_id;
    // Ism o'rniga USERNAME (yo'q bo'lsa — ism), bosilsa raqib profili ochiladi
    const label = h.opp_username ? "@" + h.opp_username : (h.opp_name || "Raqib");
    const dataAttrs = canOpen
      ? `class="match-item div-history-opp" style="cursor:pointer"
         data-opp-id="${h.opp_user_id}"
         data-opp-name="${escHtml(h.opp_name || "")}"
         data-opp-username="${escHtml(h.opp_username || "")}"`
      : `class="match-item"`;
    return `<div ${dataAttrs}>
      <span style="opacity:.55;font-size:11px;min-width:34px">#${h.id}</span>
      <b style="flex:1;min-width:0;color:${h.opp_username ? "var(--cyan)" : "inherit"};overflow:hidden;text-overflow:ellipsis">${escHtml(label)}</b>
      <span style="font-weight:800;margin:0 8px">${score}</span>
      <span class="status-badge status--${h.status === "confirmed" ? "confirmed" : "awaiting"}" style="font-size:10px">${divStatusLabelShort(h.status)}</span>${winBadge}
    </div>`;
  }).join("");
  const historyBlock = `
    <div class="section-label">O'YIN TARIXI</div>
    ${hist.length ? `<div class="card">${histRows}</div>`
                  : `<div class="card" style="opacity:.7;font-size:13px">${DT("div_no_matches")}</div>`}`;

  return meCard + statsGrid + divCalendarHtml(DIV.calendar, "me") + historyBlock;
}

// Liga uslubidagi raqib VS-oynasi: "Chatni ochish" (webapp chat) + "Raqib chatiga yozish" (t.me)
function divOpenOpponentModal() {
  const s = DIV.status;
  const m = s?.my_match;
  if (!m || m.is_bye) return;
  const opp = m.opponent || {};
  const t = APP.t || {};

  let modal = document.getElementById("modal-div-opponent");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-div-opponent";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  // Bot chati doim mavjud (bye bo'lmasa) — foydalanuvchi so'roviga ko'ra
  const webChatBtn = `<button class="opp-chat-btn opp-webchat-btn" id="div-opp-webchat">${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}</button>`;
  const tgBtn = (opp.username || opp.telegram_id)
    ? `<button class="opp-chat-btn" id="div-opp-tg">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;

  const myName = (m.player1_id === s.me_id) ? m.player1_name : m.player2_name;
  const myUsername = (m.player1_id === s.me_id) ? m.player1_username : m.player2_username;
  const myUserId = s.me_id;
  // Telegram rasm (bo'lmasa — ism harfi). Liga bilan bir xil /players/{id}/photo.
  const avatarHtml = (userId, name) => {
    const initial = (name || "?").charAt(0).toUpperCase();
    const fallback = `<div class="div-vs-avatar-fallback">${escHtml(initial)}</div>`;
    if (!userId) return fallback;
    return `<img class="div-vs-avatar" src="${API_BASE}/players/${userId}/photo" alt=""
              onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
            <div class="div-vs-avatar-fallback" style="display:none">${escHtml(initial)}</div>`;
  };
  const side = (userId, name, username) => `
    <div class="opp-side">
      <div class="div-vs-avatar-wrap">${avatarHtml(userId, name)}</div>
      <div class="opp-club">${escHtml(name || "—")}</div>
      <div class="opp-user">${username ? "@" + escHtml(username) : "—"}</div>
    </div>`;

  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="div-opp-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">
        ${side(myUserId, myName, myUsername)}
        <div class="opp-vs-sep">VS</div>
        ${side(opp.user_id, opp.nickname, opp.username)}
      </div>
      ${webChatBtn}
      ${tgBtn}
    </div>`;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  document.getElementById("div-opp-close").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });

  document.getElementById("div-opp-webchat")?.addEventListener("click", () => {
    modal.classList.add("hidden");
    // Liga webchat modalining o'zi — faqat Divizion API prefiksi bilan (DRY)
    openWebChat(m.id, opp.nickname || DT("div_opponent"), "/div/matches");
  });
  document.getElementById("div-opp-tg")?.addEventListener("click", () => {
    const tg = window.Telegram?.WebApp;
    if (opp.username) {
      const link = `https://t.me/${String(opp.username).replace(/^@/, "")}`;
      if (tg?.openTelegramLink) { try { tg.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); } }
      else window.open(link, "_blank");
    } else if (opp.telegram_id) {
      const link = `tg://user?id=${opp.telegram_id}`;
      if (tg?.openLink) { try { tg.openLink(link); } catch (_) { window.open(link, "_blank"); } }
      else window.open(link, "_blank");
    }
  });
}

// Liga uslubidagi natija kiritish modali (score-input-row markup)
function divOpenResultModal() {
  const s = DIV.status;
  const m = s?.my_match;
  if (!m || m.is_bye || m.status !== "pending") return;
  const t = APP.t || {};
  // 2026-07-19: QAT'IY TARTIB — bugungi o'yin kartasi bilan bir xil:
  // chapda DOIM player1, o'ngda DOIM player2. Katakcha yonida RASM,
  // rasm OSTIDA username. Tartib: Rasm-katakcha : katakcha-Rasm.
  const p1IsMe = (m.player1_id === s.me_id);
  const p1 = { id: m.player1_id, name: m.player1_name, username: m.player1_username, isMe: p1IsMe };
  const p2 = { id: m.player2_id, name: m.player2_name, username: m.player2_username, isMe: !p1IsMe };
  const sideCol = (p) => `
    <div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0">
      ${divAvatarHtml(p.id, p.name, 44, p.isMe ? (APP.currentUser && APP.currentUser.photo_url) : null)}
      <div style="font-size:11px;max-width:74px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;${p.isMe ? "opacity:.85" : "color:var(--cyan)"}">
        ${p.username ? "@" + escHtml(p.username) : escHtml(p.name || "—")}
      </div>
    </div>`;

  let modal = document.getElementById("modal-div-result");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-div-result";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">${escHtml(t.submit_result || "Natija kiritish")}</div>
      <div class="score-input-row">
        <div class="score-input-group">
          <div class="score-logo-input">
            ${sideCol(p1)}
            <input id="div-input-score1" class="score-input" type="number" min="0" max="99" value="0" />
          </div>
        </div>
        <span class="score-separator">:</span>
        <div class="score-input-group">
          <div class="score-logo-input">
            <input id="div-input-score2" class="score-input" type="number" min="0" max="99" value="0" />
            ${sideCol(p2)}
          </div>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn--ghost" id="div-result-cancel">${escHtml(t.cancel || "Bekor")}</button>
        <button class="btn btn--primary btn--glow" id="div-result-submit">${escHtml(t.submit || "Yuborish")}</button>
      </div>
    </div>`;
  modal.classList.remove("hidden");

  const close = () => modal.classList.add("hidden");
  document.getElementById("div-result-cancel").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
  document.getElementById("div-result-submit").addEventListener("click", async (e) => {
    const s1 = Number(document.getElementById("div-input-score1").value || 0);
    const s2 = Number(document.getElementById("div-input-score2").value || 0);
    // 2026-07-19: modal endi QAT'IY player1:player2 tartibida — chap katakcha
    // score1, o'ng katakcha score2. Almashtirish (swap) KERAK EMAS.
    e.target.disabled = true;
    try {
      await apiFetch(`/div/match/submit-result?match_id=${m.id}&score1=${s1}&score2=${s2}`, { method: "POST" });
      close();
      showToast(DT("div_toast_result_sent"));
      await divLoadStatus();
    } catch (err) {
      e.target.disabled = false;
      showToast(DT("div_toast_error") + err.message);
    }
  });
}

// ---- SOVRINLAR: hozircha bo'sh (rasm keyin qo'shiladi) ----
function divRenderPrizes() {
  return `<div class="card" style="text-align:center;padding:26px 16px">
    <div style="font-size:34px">🎁</div>
    <div style="font-weight:700;margin-top:6px">Divizion sovrinlari</div>
    <div style="font-size:13px;opacity:.7;margin-top:4px">Tez orada e'lon qilinadi.</div>
  </div>`;
}

// ---- ISHTIROKCHI PROFILI (to'liq sahifa, liga uslubi) ----
async function divOpenPlayerProfile(userId) {
  if (!userId) return;
  // O'zimga bosilsa — o'z profilim bo'limiga o'tamiz
  if (DIV.status && userId === DIV.status.me_id) {
    divNavigate("profile");
    return;
  }
  DIV.playerBackTo = (DIV.section === "player") ? DIV.playerBackTo : DIV.section;
  DIV.player = null;
  DIV.playerCalMonth = null;   // yangi profil -> joriy oydan boshlaymiz
  DIV.section = "player";
  renderDivision();  // yuklanmoqda holati (qoida #40)
  await divLoadPlayer(userId);
}

async function divLoadPlayer(userId, month) {
  const q = month ? `?month=${encodeURIComponent(month)}` : "";
  try {
    DIV.player = await apiFetch(`/div/player/${userId}/profile${q}`);
    DIV.playerCalMonth = DIV.player?.calendar?.month || null;
  } catch (e) {
    showToast(DT("div_toast_profile_err") + e.message);
    if (!DIV.player) DIV.section = DIV.playerBackTo;
  }
  renderDivision();
}

function divRenderPlayer() {
  const data = DIV.player;
  const back = `<button class="back-btn" id="div-player-back">
      <span class="back-btn-arrow" data-icon="back"></span><span>Ortga</span>
    </button>`;
  if (!data) {
    return `${back}<div class="card" style="text-align:center;opacity:.7">${DT("div_loading")}</div>`;
  }

  const st = data.stats || { wins: 0, draws: 0, losses: 0, win_rate: 0 };
  const initial = (data.nickname || "?").charAt(0).toUpperCase();
  const photo = `<img src="${API_BASE}/players/${data.user_id}/photo" alt=""
        style="width:56px;height:56px;border-radius:50%;object-fit:cover;flex:none"
        onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"
      ><div style="display:none;width:56px;height:56px;border-radius:50%;flex:none;
        align-items:center;justify-content:center;font-size:24px;font-weight:800;
        background:linear-gradient(140deg,#7c5cff,#31d0aa);color:#fff">${escHtml(initial)}</div>`;

  // Umumiy ball (1500 + achkolar) — o'z profilim bilan bir xil ko'rinish
  const rating = (st.rating !== undefined && st.rating !== null) ? st.rating : 1500;

  const tgBtn = data.username
    ? `<button class="btn btn--ghost" id="div-player-tg" style="width:100%;margin-top:12px">${DT("div_open_telegram")}</button>`
    : "";

  const headCard = `
    <div class="card">
      <div style="display:flex;align-items:center;gap:12px">
        ${photo}
        <div style="min-width:0;flex:1">
          <div style="font-size:19px;font-weight:800;overflow:hidden;text-overflow:ellipsis">${escHtml(data.nickname || "—")}</div>
          ${data.username ? `<div style="font-size:13px;color:var(--cyan)">@${escHtml(data.username)}${prizeStarsHtml({ user_id: data.user_id, username: data.username })}</div>` : ""}
        </div>
        <div class="div-ball" title="${DT("div_start_rating_hint")}">
          <div class="div-ball-value">${rating}</div>
          <div class="div-ball-label">BALL</div>
        </div>
      </div>
      ${tgBtn}
    </div>`;

  const statsGrid = `
    <div class="section-label">STATISTIKA</div>
    <div class="stats-grid">
      <div class="stat-card stat-card--primary"><span class="stat-card-value neon-cyan">${st.win_rate}%</span><span class="stat-card-label">G'alaba foizi</span></div>
      <div class="stat-card"><span class="stat-card-value neon-cyan">${st.wins}</span><span class="stat-card-label">${DT("div_wins")}</span></div>
      <div class="stat-card"><span class="stat-card-value">${st.draws}</span><span class="stat-card-label">${DT("div_draws")}</span></div>
      <div class="stat-card"><span class="stat-card-value neon-red">${st.losses}</span><span class="stat-card-label">${DT("div_losses")}</span></div>
    </div>`;

  // Ro'yxat kalendari (o'z profilim bilan bir xil — DRY: divCalendarHtml)
  const calBlock = divCalendarHtml(data.calendar, "player");

  // O'yin tarixi — raqib @useriga bosilsa O'SHA raqib profili ochiladi
  const hist = (data.history || []).map((h, i) => {
    if (h.is_bye) {
      return `<div class="match-item">
        <span style="opacity:.55;font-size:11px;min-width:34px">#${h.id}</span>
        <b style="flex:1;text-align:center">${DT("div_auto_win_short")}</b>
        <span class="status-badge status--confirmed">+15</span></div>`;
    }
    const hasScore = (h.my_score !== null && h.my_score !== undefined);
    const score = hasScore ? `${h.my_score} : ${h.opp_score}` : "— : —";
    // 2026-07-17: bu o'yinchi kimdan achko olgani/yo'qotgani hammaga ko'rinadi
    const deltaBadge = divHistDeltaBadge(h.status, hasScore, h.my_score, h.opp_score);
    const label = h.opp_username ? "@" + h.opp_username : (h.opp_name || "Raqib");
    const canOpen = !!h.opp_user_id;
    const attrs = canOpen
      ? `class="match-item div-history-opp" style="cursor:pointer" data-opp-id="${h.opp_user_id}"`
      : `class="match-item"`;
    return `<div ${attrs}>
      <span style="opacity:.55;font-size:11px;min-width:34px">#${h.id}</span>
      <b style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;color:${h.opp_username ? "var(--cyan)" : "inherit"}">${escHtml(label)}</b>
      <span style="font-weight:800;margin:0 8px">${score}</span>
      <span class="status-badge status--${h.status === "confirmed" ? "confirmed" : "awaiting"}" style="font-size:10px">${divStatusLabelShort(h.status)}</span>${deltaBadge}
    </div>`;
  }).join("");

  const historyBlock = `
    <div class="section-label">O'YIN TARIXI</div>
    ${hist ? `<div class="card">${hist}</div>`
           : `<div class="card" style="opacity:.7;font-size:13px">${DT("div_no_matches")}</div>`}`;

  return back + headCard + statsGrid + calBlock + historyBlock;
}

// ---- Eventlar ----
function divBindSectionEvents(root) {
  root.querySelector("#div-btn-register")?.addEventListener("click", async (e) => {
    e.target.disabled = true; // ikki marta bosishdan himoya (qoida #38/#40)
    try {
      await apiFetch("/div/register", { method: "POST" });
      showToast(DT("div_toast_registered"));
      await divLoadStatus();
    } catch (err) {
      e.target.disabled = false;
      showToast(err.message === "window_closed"
        ? DT("div_toast_reg_closed")
        : err.message === "banned"
          ? DT("div_toast_banned")
          : DT("div_toast_error") + err.message);
    }
  });

  // Reyting tabi: Achko | To'p urarlar
  root.querySelectorAll("[data-div-rtab]").forEach(b =>
    b.addEventListener("click", () => {
      DIV.ratingTab = b.dataset.divRtab;
      renderDivision();
      if (DIV.ratingTab === "scorers") void divLoadScorers();
      else void divLoadRating();
    }));

  // To'p urarlar: "Sizning o'rningiz" -> qatorga scroll
  root.querySelector("#div-myscorer-card")?.addEventListener("click", () => {
    const row = root.querySelector("tr.is-me");
    if (!row) return;
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    row.classList.add("div-row-flash");
    setTimeout(() => row.classList.remove("div-row-flash"), 1600);
  });

  // Boshqa ishtirokchi profilidagi kalendar: oldingi/keyingi oy
  root.querySelectorAll("[data-div-pcal]").forEach(b =>
    b.addEventListener("click", () => {
      const cur = DIV.player?.calendar?.month;
      const uid = DIV.player?.user_id;
      if (!cur || !uid) return;
      const n = (b.dataset.divPcal === "prev") ? -1 : 1;
      void divLoadPlayer(uid, divShiftMonth(cur, n));
    }));

  // O'z profilim kalendari: oldingi/keyingi oy
  root.querySelectorAll("[data-div-cal]").forEach(b =>
    b.addEventListener("click", () => {
      const cur = DIV.calendar?.month;
      if (!cur) return;
      const n = (b.dataset.divCal === "prev") ? -1 : 1;
      void divLoadCalendar(divShiftMonth(cur, n));
    }));

  // Ishtirokchi profili sahifasi: ortga va Telegramda ochish
  root.querySelector("#div-player-back")?.addEventListener("click", () => {
    DIV.player = null;
    divNavigate(DIV.playerBackTo || "rating");
  });
  root.querySelector("#div-player-tg")?.addEventListener("click", () => {
    const u = DIV.player?.username;
    if (!u) return;
    const link = `https://t.me/${String(u).replace(/^@/, "")}`;
    const tg = window.Telegram?.WebApp;
    if (tg?.openTelegramLink) { try { tg.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); } }
    else window.open(link, "_blank");
  });

  root.querySelector("#div-btn-opponent")?.addEventListener("click", divOpenOpponentModal);
  root.querySelector("#div-btn-open-result")?.addEventListener("click", divOpenResultModal);

  // Asosiy sahifadagi raqib tomoni bosilsa — raqib profili
  root.querySelector("#div-opp-profile-open")?.addEventListener("click", () => {
    const opp = DIV.status?.my_match?.opponent;
    if (opp) divOpenPlayerProfile(opp.user_id);
  });

  // O'yin tarixidagi raqib qatori bosilsa — raqib profili
  root.querySelectorAll(".div-history-opp").forEach(el =>
    el.addEventListener("click", () => divOpenPlayerProfile(Number(el.dataset.oppId))));

  // Reyting qatori bosilsa — o'sha ishtirokchi profili
  root.querySelectorAll(".div-rating-row").forEach(el =>
    el.addEventListener("click", () => divOpenPlayerProfile(Number(el.dataset.uid))));

  // "Sizning o'rningiz" kartasi bosilsa — jadval o'z qatorimga suriladi va yonadi
  root.querySelector("#div-myrank-card")?.addEventListener("click", () => {
    const row = document.getElementById("div-my-rating-row");
    if (!row) return;
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    row.classList.add("div-row-flash");
    setTimeout(() => row.classList.remove("div-row-flash"), 1600);
  });

  // Raqib profili (qur'a oynasi rasm/user yoki tarixdagi raqib ustiga bosilganda)
  root.querySelectorAll("[data-div-opp-profile]").forEach(el => {
    const uid = Number(el.dataset.divOppProfile);
    if (!uid) return;
    el.addEventListener("click", () => divOpenPlayerProfile(uid));
  });

  const act = async (accept) => {
    const m = DIV.status?.my_match;
    if (!m) return;
    try {
      await apiFetch(`/div/match/confirm?match_id=${m.id}&accept=${accept}`, { method: "POST" });
      showToast(accept ? DT("div_toast_confirmed") : DT("div_toast_rejected"));
      await divLoadStatus();
    } catch (err) {
      showToast(DT("div_toast_error") + err.message);
    }
  };
  root.querySelector("#div-btn-confirm")?.addEventListener("click", () => act(true));
  root.querySelector("#div-btn-reject")?.addEventListener("click", () => act(false));

  // Admin panel eventlari
  // 2026-07-17: "Bugungi/Barcha kunlar" tablari olib tashlandi (o'rniga ban formasi)

  // KUNLIK BAN formasi — ishtirokchi tanlash + kun soni + tugma
  if (document.getElementById("div-ban-box")) {
    const banLabel = (o) =>
      `${o.username ? "@" + o.username : (o.nickname || "—")}${o.last_day ? " · " + o.last_day : ""}`;
    void reassignLoadList("/div/participants/all", "div-ban-box", banLabel);
    const banBtn = document.getElementById("div-btn-ban");
    banBtn?.addEventListener("click", () => void divAdminBanSubmit(banBtn));
  }

  // "MATCH ID ORQALI TUZATISH" formasi
  root.querySelector("#div-fix-match-id")?.addEventListener("input", (e) =>
    divAdminFixIdChanged(e.target.value));

  root.querySelector("#div-fix-submit")?.addEventListener("click", async (e) => {
    const info = DIV.adminFixInfo;
    if (!info || info === "notfound") return;
    const s1 = Number(document.getElementById("div-fix-score1").value || 0);
    const s2 = Number(document.getElementById("div-fix-score2").value || 0);
    e.target.disabled = true;
    try {
      await apiFetch(`/div/admin/match/set-result?match_id=${info.id}&score1=${s1}&score2=${s2}`,
                     { method: "POST" });
      showToast(`#${info.id} tuzatildi ✅`);
      DIV.adminFixId = "";
      DIV.adminFixInfo = null;
      await divLoadAdminMatches();
    } catch (err) {
      e.target.disabled = false;
      showToast(DT("div_toast_error") + err.message);
    }
  });

  root.querySelectorAll("[data-div-admin-edit]").forEach(b =>
    b.addEventListener("click", () => divAdminEdit(Number(b.dataset.divAdminEdit))));
  root.querySelectorAll("[data-div-admin-cancel]").forEach(b =>
    b.addEventListener("click", async () => {
      const id = Number(b.dataset.divAdminCancel);
      if (!confirm(DT("div_admin_cancel_ask"))) return;
      try {
        await apiFetch(`/div/admin/match/cancel?match_id=${id}`, { method: "POST" });
        showToast(DT("div_admin_cancelled"));
        await divLoadAdminMatches();
      } catch (err) { showToast(DT("div_toast_error") + err.message); }
    }));

  // Katta hisob (admin_pending) qarori — liga admin oqimi kabi
  const resolveBig = async (id, accept) => {
    try {
      await apiFetch(`/div/admin/match/resolve?match_id=${id}&accept=${accept}`, { method: "POST" });
      showToast(accept ? DT("div_admin_approved") : DT("div_admin_rejected"));
      await divLoadAdminMatches();
    } catch (err) { showToast(DT("div_toast_error") + err.message); }
  };
  root.querySelectorAll("[data-div-admin-approve]").forEach(b =>
    b.addEventListener("click", () => resolveBig(Number(b.dataset.divAdminApprove), true)));
  root.querySelectorAll("[data-div-admin-reject]").forEach(b =>
    b.addEventListener("click", () => resolveBig(Number(b.dataset.divAdminReject), false)));

  // Ishtirokchini almashtirish (2026-07-16) — api.js umumiy yordamchilari (DRY)
  if (document.getElementById("div-reassign-box")) {
    const divReassignLabel = (o) =>
      `${o.username ? "@" + o.username : (o.nickname || "—")}${o.last_day ? " · " + o.last_day : ""}`;
    void reassignLoadList("/div/participants/all", "div-reassign-box", divReassignLabel);
    const divReassignBtn = document.getElementById("div-btn-reassign");
    if (divReassignBtn) {
      divReassignBtn.addEventListener("click", () =>
        void reassignSubmit("/div/participant/reassign", "div-reassign-box",
          "div-reassign-new-tg", divReassignBtn, () => divLoadAdminMatches()));
    }
  }

  // 2026-07-22 (talab 2): admin tayinlash — faqat bosh admin (api.js DRY yordamchisi)
  if (document.getElementById("div-admin-roles-list")) {
    const addBtn = document.getElementById("div-btn-admin-add");
    if (addBtn) addBtn.addEventListener("click",
      () => void scopeAdminRoleAdd("division", "div-admin-new-id", "div-admin-roles-list"));
    void scopeAdminRolesLoad("division", "div-admin-roles-list");
  }
}

// ---- ADMIN PANEL (faqat bosh admin) ----
async function divLoadAdminMatches() {
  const q = DIV.adminDay === "all" ? "?day=all" : "";
  try {
    const d = await apiFetch(`/div/admin/matches${q}`);
    DIV.adminMatches = d.matches || [];
  } catch (_) { DIV.adminMatches = []; }
  renderDivision();
}

function divAdminStatusLabel(st) {
  return ({ pending: DT("div_status_pending"), awaiting_confirmation: DT("div_admin_pending"),
            confirmed: DT("div_admin_confirmed"), admin_pending: DT("div_admin_big_score") })[st] || st;
}

// Liga uslubidagi "TASDIQLANGAN NATIJANI TUZATISH" formasi (Match ID orqali)
function divAdminFixForm() {
  const info = DIV.adminFixInfo;   // ID yozilganda /div/admin/match/{id}/info dan keladi
  let preview = "";
  if (info === "notfound") {
    preview = `<div style="font-size:12px;color:var(--red-neon);margin:6px 0">${DT("div_admin_match_404")}</div>`;
  } else if (info) {
    const p1 = info.player1_username ? "@" + info.player1_username : (info.player1_name || "—");
    const p2 = info.is_bye ? DT("div_admin_bye")
      : (info.player2_username ? "@" + info.player2_username : (info.player2_name || "—"));
    const cur = (info.score1 !== null && info.score1 !== undefined) ? `${info.score1} : ${info.score2}` : "— : —";
    preview = `
      <div class="card" style="margin:8px 0;padding:10px 12px;font-size:13px">
        <div style="opacity:.65;font-size:11.5px">#${info.id} · ${escHtml(info.day)} · ${divAdminStatusLabel(info.status)}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:4px">
          <b style="min-width:0;overflow:hidden;text-overflow:ellipsis">${escHtml(p1)}</b>
          <span style="font-weight:800;white-space:nowrap">${cur}</span>
          <b style="min-width:0;overflow:hidden;text-overflow:ellipsis;text-align:right">${escHtml(p2)}</b>
        </div>
      </div>`;
  }
  const disabled = !info || info === "notfound" || info.is_bye;
  return `
    <div class="section-label">MATCH ID ORQALI TUZATISH</div>
    <div class="admin-fix-form">
      <input id="div-fix-match-id" class="modal-input" type="number" min="1"
             placeholder="${DT("div_admin_match_id")}" value="${DIV.adminFixId || ""}" />
      ${preview}
      <div class="score-input-row">
        <div class="score-input-group">
          <span class="score-input-label">P1</span>
          <input id="div-fix-score1" class="score-input" type="number" min="0" max="99" value="${info && info !== "notfound" && info.score1 != null ? info.score1 : 0}" />
        </div>
        <span class="score-separator">:</span>
        <div class="score-input-group">
          <span class="score-input-label">P2</span>
          <input id="div-fix-score2" class="score-input" type="number" min="0" max="99" value="${info && info !== "notfound" && info.score2 != null ? info.score2 : 0}" />
        </div>
      </div>
      <button class="btn btn--primary btn--glow" id="div-fix-submit" ${disabled ? "disabled" : ""}
              style="opacity:${disabled ? ".45" : "1"}">Tuzatish</button>
    </div>`;
}

// Match ID yozilganda o'yin ma'lumotini yuklaydi (350ms debounce, liga naqshi)
let _divFixTimer = null;
function divAdminFixIdChanged(raw) {
  clearTimeout(_divFixTimer);
  DIV.adminFixId = raw;
  const id = parseInt(raw, 10);
  if (!id || id <= 0) { DIV.adminFixInfo = null; renderDivision(); divFocusFixId(); return; }
  _divFixTimer = setTimeout(async () => {
    try {
      DIV.adminFixInfo = await apiFetch(`/div/admin/match/${id}/info`);
    } catch (_) {
      DIV.adminFixInfo = "notfound";
    }
    renderDivision();
    divFocusFixId();
  }, 350);
}

// Qayta render'dan keyin fokus ID maydonida qolsin (qoida #40)
function divFocusFixId() {
  const el = document.getElementById("div-fix-match-id");
  if (el && document.activeElement !== el) {
    el.focus();
    const v = el.value; el.value = ""; el.value = v;  // kursor oxiriga
  }
}

// 2026-07-16: Ishtirokchini almashtirish formasi (faqat bosh admin; backend
// super-admin bilan himoyalangan). Qur'a/juftlashga ta'sir qilmaydi.
function divAdminReassignForm() {
  // 2026-07-22: akkount almashtirish — backend super_admin talab qiladi,
  // shuning uchun tayinlangan div adminga ko'rsatilmaydi (403 chalkashligi bo'lmasin)
  if (!DIV.status?.is_super) return "";
  return `
    <div class="section-label">ISHTIROKCHINI ALMASHTIRISH</div>
    <div class="admin-fix-form" style="margin-bottom:12px">
      <div id="div-reassign-box" style="margin-bottom:6px"></div>
      <input id="div-reassign-new-tg" class="modal-input" type="number" inputmode="numeric"
             placeholder="${DT("div_admin_new_tg_id")}" style="margin-bottom:8px" />
      <button class="btn" id="div-btn-reassign">${DT("div_admin_switch_acc")}</button>
    </div>`;
}

// 2026-07-17: Admin ishtirokchiga kunlik ban beradi (tasdiq + POST /div/admin/ban)
async function divAdminBanSubmit(btn) {
  const sel = document.getElementById("div-ban-box-select");
  const uid = sel ? Number(sel.value || 0) : 0;
  const days = Math.floor(Number(document.getElementById("div-ban-days")?.value || 0));
  if (!uid) { showToast(DT("div_admin_ban_pick")); return; }
  if (!days || days < 1) { showToast(DT("div_admin_ban_days")); return; }
  const name = sel.options[sel.selectedIndex]?.text || "ishtirokchi";
  if (!confirm(`${name} ga ${days} kunlik BAN berilsinmi?\n\nU shu muddat davomida Divizion ro'yxatidan o'ta olmaydi va telegramiga xabar boradi.`)) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/div/admin/ban", {
      method: "POST",
      body: JSON.stringify({ user_id: uid, days }),
    });
    showToast(`🚫 Ban berildi: ${r.until_day} gacha (${days} kun)`);
    const inp = document.getElementById("div-ban-days");
    if (inp) inp.value = "";
  } catch (e) {
    const msg = {
      invalid_days: DT("div_admin_ban_bad"),
      user_not_found: "ishtirokchi topilmadi",
    }[e.message] || e.message;
    showToast(DT("div_toast_error") + msg);
  } finally {
    btn.disabled = false;
  }
}

// 2026-07-17: Kunlik ban formasi ("Bugungi/Barcha kunlar" tablari o'rniga).
// Admin ishtirokchini tanlab, istalgancha kunlik ban beradi (faqat bosh admin).
function divAdminBanForm() {
  // 2026-07-22: ban berish — backend super_admin talab qiladi (bosh admin ishi)
  if (!DIV.status?.is_super) return "";
  return `
    <div class="section-label">KUNLIK BAN BERISH</div>
    <div class="admin-fix-form">
      <div id="div-ban-box" style="margin-bottom:6px"></div>
      <input id="div-ban-days" class="modal-input" type="number" min="1" inputmode="numeric"
             placeholder="${DT("div_admin_ban_days_ph")}" style="margin-bottom:8px" />
      <button class="btn btn--danger" id="div-btn-ban">${DT("div_admin_ban_title")}</button>
      <div style="font-size:11.5px;opacity:.65">${DT("div_admin_ban_hint")}</div>
    </div>`;
}

// 2026-07-22 (talab 2): admin tayinlash formasi — faqat bosh admin.
// ChL bilan bir xil (api.js scopeAdminRoles* DRY yordamchilari, scope='division').
function divAdminRolesForm() {
  if (!DIV.status?.is_super) return "";
  return `
    <div class="section-label">ADMIN TAYINLASH</div>
    <div class="admin-fix-form" style="margin-bottom:12px">
      <input id="div-admin-new-id" class="modal-input" type="number" min="1"
             placeholder="Telegram ID" style="margin-bottom:8px" />
      <button class="btn btn--primary" id="div-btn-admin-add">Admin qo'shish</button>
      <div id="div-admin-roles-list" class="admin-players-list" style="margin-top:8px"></div>
    </div>`;
}

function divRenderAdmin() {
  const ms = DIV.adminMatches || [];
  if (!ms.length) {
    return divAdminFixForm() + divAdminReassignForm() + divAdminRolesForm() + divAdminBanForm()
      + `<div class="card">${DT("div_admin_no_matches")}</div>`;
  }
  return divAdminFixForm() + divAdminReassignForm() + divAdminRolesForm() + divAdminBanForm() +
    `<div class="card" style="font-size:12.5px;opacity:.75">${DT("div_admin_hint")}</div>` +
    ms.map(m => {
      const p2 = m.player2_id ? escHtml(m.player2_name || "") : `<i>${DT("div_admin_bye")}</i>`;
      const hasScore = (m.score1 !== null && m.score1 !== undefined);
      const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
      const isBye = !m.player2_id;

      let buttons = "";
      if (!isBye) {
        if (m.status === "admin_pending") {
          // Liga admin oqimi: katta hisob — tasdiqlash yoki rad etish
          buttons = `
            <button class="btn btn--primary" data-div-admin-approve="${m.id}" style="flex:1">${DT("div_confirm")}</button>
            <button class="btn btn--ghost" data-div-admin-reject="${m.id}" style="flex:1">${DT("div_reject")}</button>`;
        } else {
          buttons = `<button class="btn btn--primary" data-div-admin-edit="${m.id}" style="flex:1">${DT("div_admin_edit")}</button>`;
          if (hasScore || m.status !== "pending") {
            buttons += `<button class="btn btn--ghost" data-div-admin-cancel="${m.id}" style="flex:1">${DT("div_admin_cancel")}</button>`;
          }
        }
      }
      return `
        <div class="card">
          <div style="font-size:12px;opacity:.65">#${m.id}${DIV.adminDay === "all" ? " · " + escHtml(m.day) : ""} · ${divAdminStatusLabel(m.status)}</div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;gap:8px">
            <b style="min-width:0;overflow:hidden;text-overflow:ellipsis">${escHtml(m.player1_name || "")}</b>
            <span style="font-weight:800;white-space:nowrap">${score}</span>
            <b style="min-width:0;overflow:hidden;text-overflow:ellipsis;text-align:right">${p2}</b>
          </div>
          ${buttons ? `<div style="display:flex;gap:8px;margin-top:10px">${buttons}</div>` : ""}
        </div>`;
    }).join("");
}

// Admin: natijani o'rnatish/tuzatish modali (liga natija modali uslubida)
function divAdminEdit(matchId) {
  const m = (DIV.adminMatches || []).find(x => x.id === matchId);
  if (!m) return;
  let modal = document.getElementById("modal-div-admin-result");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-div-admin-result";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">${DT("div_admin_edit")}</div>
      <div style="display:flex;justify-content:space-between;font-size:12.5px;opacity:.75;margin-bottom:6px">
        <span>${escHtml(m.player1_name || "")}</span><span>${escHtml(m.player2_name || "")}</span>
      </div>
      <div class="score-input-row">
        <div class="score-input-group">
          <input id="div-admin-score1" class="score-input" type="number" min="0" max="99" value="${m.score1 ?? 0}" />
        </div>
        <span class="score-separator">:</span>
        <div class="score-input-group">
          <input id="div-admin-score2" class="score-input" type="number" min="0" max="99" value="${m.score2 ?? 0}" />
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn--ghost" id="div-admin-cancel-btn">Bekor</button>
        <button class="btn btn--primary btn--glow" id="div-admin-save-btn">Saqlash</button>
      </div>
    </div>`;
  modal.classList.remove("hidden");
  const close = () => modal.classList.add("hidden");
  document.getElementById("div-admin-cancel-btn").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
  document.getElementById("div-admin-save-btn").addEventListener("click", async (e) => {
    const s1 = Number(document.getElementById("div-admin-score1").value || 0);
    const s2 = Number(document.getElementById("div-admin-score2").value || 0);
    e.target.disabled = true;
    try {
      await apiFetch(`/div/admin/match/set-result?match_id=${matchId}&score1=${s1}&score2=${s2}`, { method: "POST" });
      close();
      showToast(DT("div_admin_saved"));
      await divLoadAdminMatches();
    } catch (err) {
      e.target.disabled = false;
      showToast(DT("div_toast_error") + err.message);
    }
  });
}
