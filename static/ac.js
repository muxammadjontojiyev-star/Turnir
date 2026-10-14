// ============================================================
//  ac.js — Osiyo Chempionlar ligasi (OChL) rejimi
//  Alohida ekran (worldcup.js naqshi). Mavjud liga/WC kodiga TEGMAYDI.
//  Rejim tanlash -> showAsianChampionsLeague() shu yerda.
//
//  Bog'liqliklar (global): APP, apiFetch (api.js), escHtml (app.js),
//  showToast, hideModeSelect, showModeSelect.
//  Backend: GET /ac/qualifiers, /ac/groups, /ac/rating/{n}, /ac/matches/my,
//           POST /ac/match/submit-result, /ac/match/confirm
// ============================================================

// Yangi format (2026-08): guruh yo'q — yagona liga bosqichi.
const AC_ROUNDS = 8;    // Liga bosqichi turlari (backend: ac_core.AC_ROUNDS)
const AC_TOTAL  = 32;   // Ishtirokchilar soni (backend: ac_qualification.AC_TOTAL)
const AC_LEAGUE_GROUP = 1;  // Yagona reyting guruh raqami (backend: ac_core.AC_LEAGUE_GROUP)
// Reyting chegaralari (backend: ac_playin.AC_SEED_COUNT / AC_QUALIFY_TOTAL):
const AC_SEED_COUNT = 8;      // top-8 to'g'ridan setkaga (8/9 orasida YASHIL chiziq)
const AC_QUALIFY_TOTAL = 24;  // 9-24 pley-in (24/25 orasida QIZIL chiziq)

const AC = {
  section: "home",     // home | rating | profile | prizes
  groups: null,        // /ac/groups javobi
  qualifiers: null,    // /ac/qualifiers javobi (qur'agacha ko'rsatish uchun)
  ratingTab: "groups",  // Reyting tabi: "groups" | "scorers"
  scorers: null,
  ratingAll: null,
  viewPlayer: null,     // Reytingdan ochilgan ishtirokchi (ac_player.js)
  rating: [],
  myMatches: [],
  meParticipant: false,
  state: null,         // /ac/matches/my → tur holati (started, current_matchday)
  profile: null,       // /ac/profile javobi
  unread: { total: 0, by_match: {} }, // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka)
};

// ---- Klub logosi (api.js: LEAGUE_CLUBS — qoida 26, DRY) ----
function acClubLogo(clubName) {
  if (!clubName || typeof LEAGUE_CLUBS === "undefined") return null;
  for (const clubs of Object.values(LEAGUE_CLUBS)) {
    const found = clubs.find(c => c.name === clubName);
    if (found) return found.logo;
  }
  return null;
}

// Klub logosi <img> (topilmasa — ⚽ fallback, qoida 40)
function acClubBadge(clubName, size = 24) {
  const logo = acClubLogo(clubName);
  if (!logo) return `<span class="ac-club-fallback" style="width:${size}px;height:${size}px">${ICON.get("shield", Math.round(size * 0.8))}</span>`;
  return `<img class="ac-club-logo" src="${escHtml(logo)}" alt="${escHtml(clubName)}" `
       + `title="${escHtml(clubName)}" style="width:${size}px;height:${size}px" `
       + `onerror="this.style.visibility='hidden'" />`;
}

// ---- Kirish nuqtasi ----
function showAsianChampionsLeague() {
  if (typeof hideModeSelect === "function") hideModeSelect();
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));

  let root = document.getElementById("ac-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "ac-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  AC.section = "home";
  void acLoadThenRender();
  // 2026-07-20: rejimga kirishdayoq rozetkani yuklaymiz — Profilga kirmasdan ham ko'rinsin
  void acRefreshUnreadBadge();
}

function exitAsianChampionsLeague() {
  const root = document.getElementById("ac-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function acNavigate(section) {
  AC.section = section;
  renderAsianChampionsLeague();
  // 2026-07-19: har sahifada o'qilmagan rozetkani yangilab turamiz (liga naqshi)
  void acRefreshUnreadBadge();
  // 2026-07-20: pir-pirash tuzatildi — navigate allaqachon render qildi; fetch'dan
  // keyin faqat ma'lumot O'ZGARGAN bo'lsa qayta chizamiz (onlyIfChanged=true)
  if (section === "rating") void (AC.ratingTab === "scorers" ? acLoadScorers(true) : acLoadRating(true));
  if (section === "profile") void acLoadProfile();
  if (section === "prizes") void acLoadProfileForPrizes();
  if (section === "admin") void acLoadAdminData();
}

// 2026-07-19: OChL o'qilmagan soni — Profil nav tugmasidagi qizil rozetka (liga naqshi)
async function acRefreshUnreadBadge() {
  try {
    AC.unread = await apiFetch("/ac/matches/unread");
  } catch (_) {
    AC.unread = { total: 0, by_match: {} };
  }
  acUpdateNavBadge();
}

function acUpdateNavBadge() {
  if (typeof setNavBadge !== "function") return;
  setNavBadge(
    document.querySelector('#ac-root .wc-nav-item[data-ac-tab="profile"]'),
    (AC.unread && AC.unread.total) || 0
  );
}

// Admin sahifasi uchun groups + state kerak (panel matnlari uchun)
async function acLoadAdminData() {
  try { AC.groups = await apiFetch("/ac/groups"); } catch (_) {}
  try { AC.state = (await apiFetch("/ac/state")); } catch (_) {}
  renderAsianChampionsLeague();
}

// Sovrinlar uchun user_id kerak — profil bir marta yuklanadi
async function acLoadProfileForPrizes() {
  if (!AC.profile) {
    try { AC.profile = await apiFetch("/ac/profile"); } catch (_) { AC.profile = null; }
    renderAsianChampionsLeague();
  } else {
    void acBindPrizes();
  }
}

async function acLoadThenRender() {
  if (typeof acCheckAdmin === "function") { try { await acCheckAdmin(); } catch (_) {} }
  try {
    AC.groups = await apiFetch("/ac/groups");
    AC.meParticipant = !!AC.groups.me_participant;
  } catch (_) { AC.groups = null; }
  try {
    AC.qualifiers = await apiFetch("/ac/qualifiers");
  } catch (_) { AC.qualifiers = null; }
  renderAsianChampionsLeague();
}

async function acLoadRating(onlyIfChanged = false) {
  const prev = JSON.stringify(AC.ratingAll || []);
  try {
    // 2026-07-23: yulduzchalar reyting bilan birga yangilanadi — yangi berilgan
    // kubok (ac_cup) darhol ko'rinadi (ilgari faqat ilova ochilganда yuklanardi,
    // shuning uchun yangi kubok egasining ★ chiqmasди).
    const [d] = await Promise.all([
      apiFetch("/ac/rating-all"),
      (typeof loadPrizeStars === "function") ? loadPrizeStars() : Promise.resolve(),
    ]);
    AC.ratingAll = d.groups || [];
    AC.rating = [];
    for (const g of AC.ratingAll) {
      g.rating.forEach((p, i) => AC.rating.push({ ...p, _group: g.group_number, _pos: i + 1 }));
    }
  } catch (_) { AC.ratingAll = []; AC.rating = []; }
  // 2026-07-20: pir-pirash tuzatildi — sahifa allaqachon chizilgan bo'lsa va
  // ma'lumot o'zgarmagan bo'lsa, ikkinchi (keraksiz) to'liq renderni o'tkazib yuboramiz
  if (onlyIfChanged && JSON.stringify(AC.ratingAll || []) === prev) return;
  renderAsianChampionsLeague();
}

async function acLoadMatches() {
  // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka) — liga loadMyMatches naqshi
  try {
    AC.unread = await apiFetch("/ac/matches/unread");
  } catch (_) {
    AC.unread = { total: 0, by_match: {} };
  }
  acUpdateNavBadge();
  try {
    const d = await apiFetch("/ac/matches/my");
    AC.myMatches = d.matches || [];
    AC._myId = d.me_id ?? null;
    AC.state = d.state || null;
  } catch (_) { AC.myMatches = []; AC._myId = null; AC.state = null; }
  renderAsianChampionsLeague();
}

// ---- RENDER ----
function renderAsianChampionsLeague() {
  const root = document.getElementById("ac-root");
  if (!root) return;

  let body = "";
  if (AC.section === "home") body = acRenderHome();
  else if (AC.section === "rating") body = acRenderRating();
  else if (AC.section === "prizes") body = acRenderPrizes();
  else if (AC.section === "player") body = acRenderPlayer();
  else if (AC.section === "admin") body = `<div id="ac-admin-page"></div>`;
  else body = acRenderProfile();

  // 2026-07-22: Admin tab — bosh admin YOKI tayinlangan OChL admin (isCl) ko'radi
  const adminTab = (typeof AC_ADMIN !== "undefined" && (AC_ADMIN.isSuper || AC_ADMIN.isCl)) ? `
      <button class="wc-nav-item ${AC.section === "admin" ? "active" : ""}" data-ac-tab="admin">
        <span class="nav-icon" data-icon="shield"></span>
        <span class="nav-label">${ACT("ac_nav_admin")}</span>
      </button>` : "";

  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="ac-back-btn">←</button>
      <div class="wc-header-title ac-title">${ICON.get("trophy", 20)} <span>${ACT("ac_title")}</span></div>
    </div>
    <div class="wc-body" style="padding-bottom:90px;">${body}</div>
    <nav class="wc-nav">
      <button class="wc-nav-item ${AC.section === "home" ? "active" : ""}" data-ac-tab="home">
        <span class="nav-icon" data-icon="home"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_home) || "Asosiy"}</span>
      </button>
      <button class="wc-nav-item ${AC.section === "rating" ? "active" : ""}" data-ac-tab="rating">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_rating) || "Reyting"}</span>
      </button>
      <button class="wc-nav-item ${AC.section === "profile" ? "active" : ""}" data-ac-tab="profile">
        <span class="nav-icon" data-icon="user"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_profile) || "Profil"}</span>
      </button>
      <button class="wc-nav-item ${AC.section === "prizes" ? "active" : ""}" data-ac-tab="prizes">
        <span class="nav-icon" data-icon="gift"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_prizes) || "Sovrinlar"}</span>
      </button>${adminTab}
    </nav>
  `;

  if (typeof applyIcons === "function") applyIcons(root);
  // 2026-07-19: nav har renderda qayta quriladi — rozetkani qayta qo'yamiz
  acUpdateNavBadge();
  // 2026-07-20: play-off bloklari (boshlanmagan bo'lsa bo'sh qoladi)
  if (AC.section === "rating" && typeof acpoLoadBracket === "function") void acpoLoadBracket();
  if (AC.section === "profile" && typeof acpoLoadMyMatches === "function") void acpoLoadMyMatches();
  document.getElementById("ac-back-btn").addEventListener("click", exitAsianChampionsLeague);
  root.querySelectorAll("[data-ac-tab]").forEach(b =>
    b.addEventListener("click", () => acNavigate(b.dataset.acTab)));
  acBindSectionEvents(root);
  if (AC.section === "player") acBindPlayer(root);
  if (AC.section === "profile") acBindProfile(root);
  if (AC.section === "prizes") void acBindPrizes();
  if (AC.section === "admin") void acRenderAdminPage();
}


// ---- HOME ----  → ac_home.js (qoida 21: fayl 300 qatordan oshmasin)

// ---- SCORERS (to'purarlar) ----
async function acLoadScorers(onlyIfChanged = false) {
  const prev = JSON.stringify(AC.scorers || []);
  try {
    const d = await apiFetch("/ac/scorers");
    AC.scorers = d.scorers || [];
  } catch (_) { AC.scorers = []; }
  // 2026-07-20: pir-pirash tuzatildi (acLoadRating bilan bir xil mantiq)
  if (onlyIfChanged && JSON.stringify(AC.scorers || []) === prev) return;
  renderAsianChampionsLeague();
}

function acRenderScorers() {
  const rows = AC.scorers;
  if (rows === null) return `<div class="wc-loading-row">${ACT("ac_loading")}</div>`;
  if (!rows.length) return `<div class="wc-loading-row">${ACT("ac_no_goals")}</div>`;

  const body = rows.map((p, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><div class="ac-rating-player" data-ac-player="${p.user_id}">
        ${acClubBadge(p.club_name, 22)}
        <span class="ac-rating-user">${escHtml(p.username ? "@" + p.username : (p.nickname || ""))}${prizeStarsHtml(p)}</span>
      </div></td>
      <td>${p.played}</td>
      <td><b>${p.goals}</b></td>
    </tr>`).join("");

  return `
    <table class="rating-table">
      <thead><tr><th>#</th><th>${ACT("ac_player_col")}</th><th>${ACT("ac_played_col")}</th><th>${ACT("ac_col_goals")}</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

// ---- RATING ----
function acRenderRating() {
  const tabs = `
    <div class="ac-rating-tabs">
      <button class="tab-btn${AC.ratingTab === "groups" ? " active" : ""}" data-ac-rtab="groups">${ACT("ac_tab_groups")}</button>
      <button class="tab-btn${AC.ratingTab === "scorers" ? " active" : ""}" data-ac-rtab="scorers">${ACT("ac_tab_scorers")}</button>
      <button class="tab-btn${AC.ratingTab === "bracket" ? " active" : ""}" data-ac-rtab="bracket">${ACT("ac_tab_bracket")}</button>
    </div>`;
  if (AC.ratingTab === "scorers") return `${tabs}<div class="card card--table">${acRenderScorers()}</div>`;
  // 2026-07-21: Setka — WC kabi ALOHIDA tab (ac_playoff.js acpoLoadBracket to'ldiradi)
  if (AC.ratingTab === "bracket")
    return `${tabs}<div id="ac-po-bracket-box"><div class="wc-loading-row">Yuklanmoqda…</div></div>`;

  // Barcha guruhlar ketma-ket (Guruh 1 → jadval, Guruh 2 → jadval ...)
  const groups = AC.ratingAll;
  if (groups === null || groups === undefined) return `${tabs}<div class="wc-loading-row">${ACT("ac_loading")}</div>`;
  if (!groups.length) return `${tabs}<div class="card">${ACT("ac_no_groups")}</div>`;

  // Yangi format: yagona umumiy reyting (bitta "guruh"). Guruh sarlavhasi ko'rsatilmaydi.
  // 8/9 orasida YASHIL chiziq (top-8 to'g'ridan setkaga), 24/25 orasida QIZIL chiziq
  // (9-24 pley-in; 24 dan pastda OChL tugaydi) — qoida #17: konstantalar yuqorida.
  const blocks = groups.map(g => {
    const rows = g.rating.map((p, i) => {
      const pos = i + 1;
      const cut = pos === AC_SEED_COUNT ? " ac-cut-green"
                : pos === AC_QUALIFY_TOTAL ? " ac-cut-red" : "";
      return `
      <tr class="ac-rating-row${cut}">
        <td class="rank-${i + 1}">${i + 1}</td>
        <td><div class="ac-rating-player" data-ac-player="${p.user_id}">${acClubBadge(p.club_name, 22)}<span class="ac-rating-user">${escHtml(p.username ? "@" + p.username : (p.nickname || ""))}${prizeStarsHtml(p)}</span></div></td>
        <td>${p.played}</td><td>${p.goal_difference > 0 ? "+" : ""}${p.goal_difference}</td>
        <td><b>${p.points}</b></td>
      </tr>`;
    }).join("");
    return `
      <div class="card card--table" style="margin-bottom:14px">
        <table class="rating-table">
          <thead><tr><th>#</th><th>${ACT("ac_player_col")}</th><th>${ACT("ac_played_col")}</th><th>GF</th><th>${ACT("ac_col_points")}</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }).join("");

  return `${tabs}${blocks}`;
}

// ---- MATCHES ----
function acRenderMatches() {
  if (!AC.meParticipant) {
    return `<div class="card">${ACT("ac_not_participant")}</div>`;
  }
  const ms = AC.myMatches || [];
  if (!ms.length) {
    return `<div class="wc-loading-row">${ACT("ac_no_matches")}</div>`;
  }
  return `<div class="matches-list">${ms.map(acRenderMatchItem).join("")}</div>`;
}

// Bitta o'yin kartasi (worldcup_matches.js — wcRenderMatchItem naqshi, qoida 10)
function acRenderMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  // 2026-07-19: o'qilmagan chat rozetka — RAQIB logosi ustida (liga naqshi)
  const unreadCount = (AC.unread && AC.unread.by_match && AC.unread.by_match[m.id]) || 0;
  const unreadBadge = unreadCount > 0
    ? `<span class="chat-badge">${unreadCount > 9 ? "9+" : unreadCount}</span>`
    : "";
  const iAmPlayer1 = acIsMe(m.player1_id);
  const center = `
    <span class="ac-mc-logo match-badge-wrap">${acClubBadge(m.player1_club, 26)}${iAmPlayer1 ? "" : unreadBadge}</span>
    <span class="match-score">${score}</span>
    <span class="ac-mc-logo match-badge-wrap">${acClubBadge(m.player2_club, 26)}${iAmPlayer1 ? unreadBadge : ""}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "pending" && !(AC.state?.started && m.matchday === AC.state.current_matchday)) {
    statusText = "YOPIQ";
  }
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "admin_pending")         { statusCls = "status--awaiting"; statusText = "ADMIN TASDIG'I"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  const st = AC.state || {};
  const isOpenRound = !!st.started && m.matchday === st.current_matchday;

  let action = "";
  if (m.status === "pending") {
    if (!isOpenRound) {
      action = `<span class="ac-locked" title="${ACT("ac_round_locked")}">${ICON.get("lock", 16)}</span>`;
    } else {
      // 2026-10-11: soddalashtirildi — "Natija" darhol, yonida 💬 (VS-oyna: xona ID / bot chati / Telegram)
      action = `<button class="match-action-btn" data-ac-result="${m.id}">${ACT("ac_result")}</button>`
        + `<button class="match-action-btn match-chat-btn" data-ac-chat="${m.id}" title="${ACT("ac_agree_first")}">${ICON.get("chat", 18)}</button>`;
    }
  } else if (m.status === "awaiting_confirmation") {
    action = (m.submitted_by && !acIsMe(m.submitted_by))
      ? `<button class="match-action-btn" data-ac-confirm="${m.id}">${ICON.get("check", 16)}</button>`
      : `<span class="match-waiting">${ACT("ac_pending")}</span>`;
  }

  const reject = (m.status === "awaiting_confirmation" && m.submitted_by && !acIsMe(m.submitted_by))
    ? `<div class="ac-score-row"><button class="btn" data-ac-reject="${m.id}">${ICON.get("cross", 15)} ${ACT("ac_reject")}</button></div>` : "";

  // Uy/mehmon: player1 — uy egasi (ac_matches yozilish tartibi)
  const isHome = acIsMe(m.player1_id);
  const venue = isHome
    ? `<span class="ac-venue ac-venue--home">UY</span>`
    : `<span class="ac-venue ac-venue--away">MEHMON</span>`;

  // 2026-07-16: Yopiq (hali ochilmagan) turda VS/chat oynasi ochilmaydi
  // (liga is_locked naqshi). O'ynalgan/o'tgan o'yinlar — ochiq (tarix).
  const canOpenVs = isOpenRound || m.status !== "pending";
  const centerCls = canOpenVs ? "match-center match-center--clickable" : "match-center";
  const centerAttr = canOpenVs ? `data-ac-open-match="${m.id}"` : "";

  return `
    <div class="ac-match-wrap">
      <div class="ac-match-head">
        <span class="ac-match-round">${m.matchday}-tur</span><span class="ac-match-id">#${m.id}</span>
        ${venue}
        ${m.status === "pending" && isOpenRound ? "" : `<span class="match-status ${statusCls}">${statusText}</span>`}
      </div>
      <div class="ac-match-body">
        <div class="${centerCls}" ${centerAttr}>${center}</div>
        ${action}
      </div>
      ${reject}
    </div>`;
}

function acIsMe(userId) {
  // me_id backend'dan keladi (/ac/matches/my) — taxmin qilinmaydi
  return AC._myId !== null && AC._myId !== undefined && userId === AC._myId;
}

function acStatusLabel(s) {
  return ({ pending: ACT("ac_pending"), awaiting_confirmation: ACT("ac_awaiting"),
            confirmed: ACT("ac_confirmed"), admin_pending: ACT("ac_admin_pending") })[s] || s;
}

// ---- Eventlar ----
function acBindSectionEvents(root) {
  // Event delegation: bitta listener butun ac-root uchun (qayta render'da yo'qolmaydi).
  if (!root._acDelegated) {
    root._acDelegated = true;
    root.addEventListener("click", (e) => acHandleClick(e, root));
  }

}

// Barcha OChL bosishlarini bitta joyda ushlaydi (delegation — qayta render'ga chidamli)
function acHandleClick(e, root) {
  const hit = (sel) => e.target.closest(sel);
  let ac;

  if ((ac = hit("[data-ac-result]"))) {
    acOpenResultModal(Number(ac.dataset.acResult)); return;
  }
  if ((ac = hit("[data-ac-chat]"))) {
    acOpenChatThenResult(Number(ac.dataset.acChat)); return;
  }
  if ((ac = hit("[data-ac-open-match]"))) {
    acOpenChatThenResult(Number(ac.dataset.acOpenMatch)); return;
  }
  if ((ac = hit("[data-ac-confirm]"))) {
    acConfirmMatch(ac.dataset.acConfirm, true); return;
  }
  if ((ac = hit("[data-ac-reject]"))) {
    acConfirmMatch(ac.dataset.acReject, false); return;
  }
  if ((ac = hit("[data-ac-player]"))) {
    acOpenPlayerModal(Number(ac.dataset.acPlayer)); return;
  }
  if ((ac = hit("[data-ac-rtab]"))) {
    AC.ratingTab = ac.dataset.acRtab;
    renderAsianChampionsLeague();
    if (AC.ratingTab === "scorers") void acLoadScorers();
    else if (AC.ratingTab === "bracket") { /* 2026-07-21: acpoLoadBracket render hookida chaqiriladi */ }
    else void acLoadRating();
    return;
  }
}

async function acConfirmMatch(id, accept) {
  try {
    await apiFetch(`/ac/match/confirm?match_id=${id}&accept=${accept}`, { method: "POST" });
    showToast(accept ? ACT("ac_toast_confirmed") : ACT("ac_toast_rejected"));
    await acLoadMatches();
  } catch (e) {
    showToast(ACT("ac_error") + e.message);
  }
}

// ============================================================
//  NATIJA KIRITISH — liga #modal-result modalidan foydalanadi (qoida #26 DRY).
//  Submit esa OChL endpointiga yo'naltiriladi (AC._resultMatchId flag orqali).
// ============================================================
// 💬 bosilganda: raqib VS-oynasi ochiladi VA shu o'yin uchun "Natija" tugmasi
// ochiladi (liga oqimi bilan bir xil: avval kelishuv, keyin natija).
function acOpenChatThenResult(matchId) {
  if (!AC.chatOpened) AC.chatOpened = new Set();
  AC.chatOpened.add(matchId);
  acOpenOpponentModal(matchId);   // VS-oyna: "Chatni ochish" / "Raqib chatiga yozish"
  renderAsianChampionsLeague();        // 💬 → Natija tugmasiga almashadi
}

function acOpenResultModal(matchId) {
  const m = (AC.myMatches || []).find(x => String(x.id) === String(matchId));
  if (!m) { showToast(ACT("ac_match_404")); return; }
  const modal = document.getElementById("modal-result");
  if (!modal) { showToast(ACT("ac_modal_404")); return; }

  AC._resultMatchId = matchId;         // submitMatchResult() shu flagni tekshiradi

  // #modal-result #section-profile ichida — OChL rejimida u sektsiya .active emas
  // (display:none). Modalni body'ga ko'chiramiz, aks holda ko'rinmaydi.
  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  // Logolar: chap = player1_club, o'ng = player2_club
  const setLogo = (id, club) => {
    const ac = document.getElementById(id);
    if (!ac) return;
    const logo = acClubLogo(club);
    if (logo) { ac.src = logo; ac.alt = club || ""; ac.style.display = ""; }
    else { ac.removeAttribute("src"); ac.style.display = "none"; }
  };
  setLogo("result-logo1", m.player1_club);
  setLogo("result-logo2", m.player2_club);

  const s1 = document.getElementById("input-score1");
  const s2 = document.getElementById("input-score2");
  if (s1) s1.value = "0";
  if (s2) s2.value = "0";

  modal.classList.remove("hidden");
}

// Modaldagi "Yuborish" bosilganda OChL o'yiniga natija yuboradi
async function acSubmitResultFromModal() {
  const id = AC._resultMatchId;
  const s1 = Number(document.getElementById("input-score1").value || 0);
  const s2 = Number(document.getElementById("input-score2").value || 0);
  try {
    const res = await apiFetch(`/ac/match/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`,
                   { method: "POST" });
    document.getElementById("modal-result").classList.add("hidden");
    AC._resultMatchId = null;
    // 2026-10-13: katta hisob — skrinshotni shu rejim adminiga yuborish oynasi
    if (typeof isBigScoreResponse === "function" && isBigScoreResponse(res)) openBigScoreModal("ac");
    else showToast(ACT("ac_toast_result_sent"));
    await acLoadMatches();
  } catch (e) {
    const msg = { matchday_locked: ACT("ac_round_locked"),
                  match_not_found: ACT("ac_match_404") }[e.message] || e.message;
    showToast(ACT("ac_error") + msg);
  }
}
