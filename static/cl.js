// ============================================================
//  cl.js — Chempionlar ligasi (ChL) rejimi
//  Alohida ekran (worldcup.js naqshi). Mavjud liga/WC kodiga TEGMAYDI.
//  Rejim tanlash -> showChampionsLeague() shu yerda.
//
//  Bog'liqliklar (global): APP, apiFetch (api.js), escHtml (app.js),
//  showToast, hideModeSelect, showModeSelect.
//  Backend: GET /cl/qualifiers, /cl/groups, /cl/rating/{n}, /cl/matches/my,
//           POST /cl/match/submit-result, /cl/match/confirm
// ============================================================

const CL_GROUP_COUNT = 8;   // Guruhlar soni (backend: cl_core.CL_GROUPS)
const CL_GROUP_SIZE  = 4;   // Har guruhdagi ishtirokchi (backend: cl_core.CL_GROUP_SIZE)

const CL = {
  section: "home",     // home | rating | profile | prizes
  groups: null,        // /cl/groups javobi
  qualifiers: null,    // /cl/qualifiers javobi (qur'agacha ko'rsatish uchun)
  ratingTab: "groups",  // Reyting tabi: "groups" | "scorers"
  scorers: null,
  ratingAll: null,
  viewPlayer: null,     // Reytingdan ochilgan ishtirokchi (cl_player.js)
  ratingGroup: 1,      // Reytingda tanlangan guruh (1..8)
  homeGroup: 1,        // Asosiy sahifada tanlangan guruh (1..8)
  rating: [],
  myMatches: [],
  meParticipant: false,
  state: null,         // /cl/matches/my → tur holati (started, current_matchday)
  profile: null,       // /cl/profile javobi
  unread: { total: 0, by_match: {} }, // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka)
};

// ---- Klub logosi (api.js: LEAGUE_CLUBS — qoida 26, DRY) ----
function clClubLogo(clubName) {
  if (!clubName || typeof LEAGUE_CLUBS === "undefined") return null;
  for (const clubs of Object.values(LEAGUE_CLUBS)) {
    const found = clubs.find(c => c.name === clubName);
    if (found) return found.logo;
  }
  return null;
}

// Klub logosi <img> (topilmasa — ⚽ fallback, qoida 40)
function clClubBadge(clubName, size = 24) {
  const logo = clClubLogo(clubName);
  if (!logo) return `<span class="cl-club-fallback" style="width:${size}px;height:${size}px">${ICON.get("shield", Math.round(size * 0.8))}</span>`;
  return `<img class="cl-club-logo" src="${escHtml(logo)}" alt="${escHtml(clubName)}" `
       + `title="${escHtml(clubName)}" style="width:${size}px;height:${size}px" `
       + `onerror="this.style.visibility='hidden'" />`;
}

// ---- Kirish nuqtasi ----
function showChampionsLeague() {
  if (typeof hideModeSelect === "function") hideModeSelect();
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));

  let root = document.getElementById("cl-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "cl-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  CL.section = "home";
  void clLoadThenRender();
  // 2026-07-20: rejimga kirishdayoq rozetkani yuklaymiz — Profilga kirmasdan ham ko'rinsin
  void clRefreshUnreadBadge();
}

function exitChampionsLeague() {
  const root = document.getElementById("cl-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function clNavigate(section) {
  CL.section = section;
  renderChampionsLeague();
  // 2026-07-19: har sahifada o'qilmagan rozetkani yangilab turamiz (liga naqshi)
  void clRefreshUnreadBadge();
  // 2026-07-20: pir-pirash tuzatildi — navigate allaqachon render qildi; fetch'dan
  // keyin faqat ma'lumot O'ZGARGAN bo'lsa qayta chizamiz (onlyIfChanged=true)
  if (section === "rating") void (CL.ratingTab === "scorers" ? clLoadScorers(true) : clLoadRating(true));
  if (section === "profile") void clLoadProfile();
  if (section === "prizes") void clLoadProfileForPrizes();
  if (section === "admin") void clLoadAdminData();
}

// 2026-07-19: ChL o'qilmagan soni — Profil nav tugmasidagi qizil rozetka (liga naqshi)
async function clRefreshUnreadBadge() {
  try {
    CL.unread = await apiFetch("/cl/matches/unread");
  } catch (_) {
    CL.unread = { total: 0, by_match: {} };
  }
  clUpdateNavBadge();
}

function clUpdateNavBadge() {
  if (typeof setNavBadge !== "function") return;
  setNavBadge(
    document.querySelector('#cl-root .wc-nav-item[data-cl-tab="profile"]'),
    (CL.unread && CL.unread.total) || 0
  );
}

// Admin sahifasi uchun groups + state kerak (panel matnlari uchun)
async function clLoadAdminData() {
  try { CL.groups = await apiFetch("/cl/groups"); } catch (_) {}
  try { CL.state = (await apiFetch("/cl/state")); } catch (_) {}
  renderChampionsLeague();
}

// Sovrinlar uchun user_id kerak — profil bir marta yuklanadi
async function clLoadProfileForPrizes() {
  if (!CL.profile) {
    try { CL.profile = await apiFetch("/cl/profile"); } catch (_) { CL.profile = null; }
    renderChampionsLeague();
  } else {
    void clBindPrizes();
  }
}

async function clLoadThenRender() {
  if (typeof clCheckAdmin === "function") { try { await clCheckAdmin(); } catch (_) {} }
  try {
    CL.groups = await apiFetch("/cl/groups");
    CL.meParticipant = !!CL.groups.me_participant;
  } catch (_) { CL.groups = null; }
  try {
    CL.qualifiers = await apiFetch("/cl/qualifiers");
  } catch (_) { CL.qualifiers = null; }
  renderChampionsLeague();
}

async function clLoadRating(onlyIfChanged = false) {
  const prev = JSON.stringify(CL.ratingAll || []);
  try {
    const d = await apiFetch("/cl/rating-all");
    CL.ratingAll = d.groups || [];
    CL.rating = [];
    for (const g of CL.ratingAll) {
      g.rating.forEach((p, i) => CL.rating.push({ ...p, _group: g.group_number, _pos: i + 1 }));
    }
  } catch (_) { CL.ratingAll = []; CL.rating = []; }
  // 2026-07-20: pir-pirash tuzatildi — sahifa allaqachon chizilgan bo'lsa va
  // ma'lumot o'zgarmagan bo'lsa, ikkinchi (keraksiz) to'liq renderni o'tkazib yuboramiz
  if (onlyIfChanged && JSON.stringify(CL.ratingAll || []) === prev) return;
  renderChampionsLeague();
}

async function clLoadMatches() {
  // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka) — liga loadMyMatches naqshi
  try {
    CL.unread = await apiFetch("/cl/matches/unread");
  } catch (_) {
    CL.unread = { total: 0, by_match: {} };
  }
  clUpdateNavBadge();
  try {
    const d = await apiFetch("/cl/matches/my");
    CL.myMatches = d.matches || [];
    CL._myId = d.me_id ?? null;
    CL.state = d.state || null;
  } catch (_) { CL.myMatches = []; CL._myId = null; CL.state = null; }
  renderChampionsLeague();
}

// ---- RENDER ----
function renderChampionsLeague() {
  const root = document.getElementById("cl-root");
  if (!root) return;

  let body = "";
  if (CL.section === "home") body = clRenderHome();
  else if (CL.section === "rating") body = clRenderRating();
  else if (CL.section === "prizes") body = clRenderPrizes();
  else if (CL.section === "player") body = clRenderPlayer();
  else if (CL.section === "admin") body = `<div id="cl-admin-page"></div>`;
  else body = clRenderProfile();

  // 2026-07-22: Admin tab — bosh admin YOKI tayinlangan ChL admin (isCl) ko'radi
  const adminTab = (typeof CL_ADMIN !== "undefined" && (CL_ADMIN.isSuper || CL_ADMIN.isCl)) ? `
      <button class="wc-nav-item ${CL.section === "admin" ? "active" : ""}" data-cl-tab="admin">
        <span class="nav-icon" data-icon="shield"></span>
        <span class="nav-label">${CT("cl_nav_admin")}</span>
      </button>` : "";

  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="cl-back-btn">←</button>
      <div class="wc-header-title cl-title">${ICON.get("ucl", 20)} <span>${CT("cl_title")}</span></div>
    </div>
    <div class="wc-body" style="padding-bottom:90px;">${body}</div>
    <nav class="wc-nav">
      <button class="wc-nav-item ${CL.section === "home" ? "active" : ""}" data-cl-tab="home">
        <span class="nav-icon" data-icon="home"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_home) || "Asosiy"}</span>
      </button>
      <button class="wc-nav-item ${CL.section === "rating" ? "active" : ""}" data-cl-tab="rating">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_rating) || "Reyting"}</span>
      </button>
      <button class="wc-nav-item ${CL.section === "profile" ? "active" : ""}" data-cl-tab="profile">
        <span class="nav-icon" data-icon="user"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_profile) || "Profil"}</span>
      </button>
      <button class="wc-nav-item ${CL.section === "prizes" ? "active" : ""}" data-cl-tab="prizes">
        <span class="nav-icon" data-icon="gift"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_prizes) || "Sovrinlar"}</span>
      </button>${adminTab}
    </nav>
  `;

  if (typeof applyIcons === "function") applyIcons(root);
  // 2026-07-19: nav har renderda qayta quriladi — rozetkani qayta qo'yamiz
  clUpdateNavBadge();
  // 2026-07-20: play-off bloklari (boshlanmagan bo'lsa bo'sh qoladi)
  if (CL.section === "rating" && typeof clpoLoadBracket === "function") void clpoLoadBracket();
  if (CL.section === "profile" && typeof clpoLoadMyMatches === "function") void clpoLoadMyMatches();
  document.getElementById("cl-back-btn").addEventListener("click", exitChampionsLeague);
  root.querySelectorAll("[data-cl-tab]").forEach(b =>
    b.addEventListener("click", () => clNavigate(b.dataset.clTab)));
  clBindSectionEvents(root);
  if (CL.section === "player") clBindPlayer(root);
  if (CL.section === "profile") clBindProfile(root);
  if (CL.section === "prizes") void clBindPrizes();
  if (CL.section === "admin") void clRenderAdminPage();
}


// ---- HOME ----  → cl_home.js (qoida 21: fayl 300 qatordan oshmasin)

// ---- SCORERS (to'purarlar) ----
async function clLoadScorers(onlyIfChanged = false) {
  const prev = JSON.stringify(CL.scorers || []);
  try {
    const d = await apiFetch("/cl/scorers");
    CL.scorers = d.scorers || [];
  } catch (_) { CL.scorers = []; }
  // 2026-07-20: pir-pirash tuzatildi (clLoadRating bilan bir xil mantiq)
  if (onlyIfChanged && JSON.stringify(CL.scorers || []) === prev) return;
  renderChampionsLeague();
}

function clRenderScorers() {
  const rows = CL.scorers;
  if (rows === null) return `<div class="wc-loading-row">${CT("cl_loading")}</div>`;
  if (!rows.length) return `<div class="wc-loading-row">${CT("cl_no_goals")}</div>`;

  const body = rows.map((p, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><div class="cl-rating-player" data-cl-player="${p.user_id}">
        ${clClubBadge(p.club_name, 22)}
        <span class="cl-rating-user">${escHtml(p.username ? "@" + p.username : (p.nickname || ""))}${prizeStarsHtml(p)}</span>
      </div></td>
      <td>G${p.group_number}</td>
      <td>${p.played}</td>
      <td><b>${p.goals}</b></td>
    </tr>`).join("");

  return `
    <table class="rating-table">
      <thead><tr><th>#</th><th>${CT("cl_player_col")}</th><th>${CT("cl_col_group")}</th><th>${CT("cl_played_col")}</th><th>${CT("cl_col_goals")}</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

// ---- RATING ----
function clRenderRating() {
  const tabs = `
    <div class="cl-rating-tabs">
      <button class="tab-btn${CL.ratingTab === "groups" ? " active" : ""}" data-cl-rtab="groups">${CT("cl_tab_groups")}</button>
      <button class="tab-btn${CL.ratingTab === "scorers" ? " active" : ""}" data-cl-rtab="scorers">${CT("cl_tab_scorers")}</button>
      <button class="tab-btn${CL.ratingTab === "bracket" ? " active" : ""}" data-cl-rtab="bracket">${CT("cl_tab_bracket")}</button>
    </div>`;
  if (CL.ratingTab === "scorers") return `${tabs}<div class="card card--table">${clRenderScorers()}</div>`;
  // 2026-07-21: Setka — WC kabi ALOHIDA tab (cl_playoff.js clpoLoadBracket to'ldiradi)
  if (CL.ratingTab === "bracket")
    return `${tabs}<div id="cl-po-bracket-box"><div class="wc-loading-row">Yuklanmoqda…</div></div>`;

  // Barcha guruhlar ketma-ket (Guruh 1 → jadval, Guruh 2 → jadval ...)
  const groups = CL.ratingAll;
  if (groups === null || groups === undefined) return `${tabs}<div class="wc-loading-row">${CT("cl_loading")}</div>`;
  if (!groups.length) return `${tabs}<div class="card">${CT("cl_no_groups")}</div>`;

  const blocks = groups.map(g => {
    const rows = g.rating.map((p, i) => `
      <tr>
        <td class="rank-${i + 1}">${i + 1}</td>
        <td><div class="cl-rating-player" data-cl-player="${p.user_id}">${clClubBadge(p.club_name, 22)}<span class="cl-rating-user">${escHtml(p.username ? "@" + p.username : (p.nickname || ""))}${prizeStarsHtml(p)}</span></div></td>
        <td>${p.played}</td><td>${p.goal_difference > 0 ? "+" : ""}${p.goal_difference}</td>
        <td><b>${p.points}</b></td>
      </tr>`).join("");
    return `
      <div class="cl-rating-group-title">${ICON.get("ucl", 15)} ${CT("cl_col_group")} ${g.group_number}</div>
      <div class="card card--table" style="margin-bottom:14px">
        <table class="rating-table">
          <thead><tr><th>#</th><th>${CT("cl_player_col")}</th><th>${CT("cl_played_col")}</th><th>GF</th><th>${CT("cl_col_points")}</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }).join("");

  return `${tabs}${blocks}`;
}

// ---- MATCHES ----
function clRenderMatches() {
  if (!CL.meParticipant) {
    return `<div class="card">${CT("cl_not_participant")}</div>`;
  }
  const ms = CL.myMatches || [];
  if (!ms.length) {
    return `<div class="wc-loading-row">${CT("cl_no_matches")}</div>`;
  }
  return `<div class="matches-list">${ms.map(clRenderMatchItem).join("")}</div>`;
}

// Bitta o'yin kartasi (worldcup_matches.js — wcRenderMatchItem naqshi, qoida 10)
function clRenderMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  // 2026-07-19: o'qilmagan chat rozetka — RAQIB logosi ustida (liga naqshi)
  const unreadCount = (CL.unread && CL.unread.by_match && CL.unread.by_match[m.id]) || 0;
  const unreadBadge = unreadCount > 0
    ? `<span class="chat-badge">${unreadCount > 9 ? "9+" : unreadCount}</span>`
    : "";
  const iAmPlayer1 = clIsMe(m.player1_id);
  const center = `
    <span class="cl-mc-logo match-badge-wrap">${clClubBadge(m.player1_club, 26)}${iAmPlayer1 ? "" : unreadBadge}</span>
    <span class="match-score">${score}</span>
    <span class="cl-mc-logo match-badge-wrap">${clClubBadge(m.player2_club, 26)}${iAmPlayer1 ? unreadBadge : ""}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "pending" && !(CL.state?.started && m.matchday === CL.state.current_matchday)) {
    statusText = "YOPIQ";
  }
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "admin_pending")         { statusCls = "status--awaiting"; statusText = "ADMIN TASDIG'I"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  const st = CL.state || {};
  const isOpenRound = !!st.started && m.matchday === st.current_matchday;

  let action = "";
  if (m.status === "pending") {
    if (!isOpenRound) {
      action = `<span class="cl-locked" title="${CT("cl_round_locked")}">${ICON.get("lock", 16)}</span>`;
    } else if (CL.chatOpened && CL.chatOpened.has(m.id)) {
      // Chat ochilgan — endi "Natija" tugmasi
      action = `<button class="match-action-btn" data-cl-result="${m.id}">${CT("cl_result")}</button>`;
    } else {
      // Avval raqib bilan chat: 💬 tugmasi (bosilgach Natija ochiladi)
      action = `<button class="match-action-btn match-chat-btn" data-cl-chat="${m.id}" title="${CT("cl_agree_first")}">${ICON.get("chat", 18)}</button>`;
    }
  } else if (m.status === "awaiting_confirmation") {
    action = (m.submitted_by && !clIsMe(m.submitted_by))
      ? `<button class="match-action-btn" data-cl-confirm="${m.id}">${ICON.get("check", 16)}</button>`
      : `<span class="match-waiting">${CT("cl_pending")}</span>`;
  }

  const reject = (m.status === "awaiting_confirmation" && m.submitted_by && !clIsMe(m.submitted_by))
    ? `<div class="cl-score-row"><button class="btn" data-cl-reject="${m.id}">${ICON.get("cross", 15)} ${CT("cl_reject")}</button></div>` : "";

  // Uy/mehmon: player1 — uy egasi (cl_matches yozilish tartibi)
  const isHome = clIsMe(m.player1_id);
  const venue = isHome
    ? `<span class="cl-venue cl-venue--home">UY</span>`
    : `<span class="cl-venue cl-venue--away">MEHMON</span>`;

  // 2026-07-16: Yopiq (hali ochilmagan) turda VS/chat oynasi ochilmaydi
  // (liga is_locked naqshi). O'ynalgan/o'tgan o'yinlar — ochiq (tarix).
  const canOpenVs = isOpenRound || m.status !== "pending";
  const centerCls = canOpenVs ? "match-center match-center--clickable" : "match-center";
  const centerAttr = canOpenVs ? `data-cl-open-match="${m.id}"` : "";

  return `
    <div class="cl-match-wrap">
      <div class="cl-match-head">
        <span class="cl-match-round">${m.matchday}-tur</span><span class="cl-match-id">#${m.id}</span>
        ${venue}
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="cl-match-body">
        <div class="${centerCls}" ${centerAttr}>${center}</div>
        ${action}
      </div>
      ${reject}
    </div>`;
}

function clIsMe(userId) {
  // me_id backend'dan keladi (/cl/matches/my) — taxmin qilinmaydi
  return CL._myId !== null && CL._myId !== undefined && userId === CL._myId;
}

function clStatusLabel(s) {
  return ({ pending: CT("cl_pending"), awaiting_confirmation: CT("cl_awaiting"),
            confirmed: CT("cl_confirmed"), admin_pending: CT("cl_admin_pending") })[s] || s;
}

// ---- Eventlar ----
function clBindSectionEvents(root) {
  // Event delegation: bitta listener butun cl-root uchun (qayta render'da yo'qolmaydi).
  if (!root._clDelegated) {
    root._clDelegated = true;
    root.addEventListener("click", (e) => clHandleClick(e, root));
  }

  root.querySelectorAll("[data-cl-group]").forEach(b =>
    b.addEventListener("click", () => {
      CL.ratingGroup = Number(b.dataset.clGroup);
      void clLoadRating();
    }));

}

// Barcha ChL bosishlarini bitta joyda ushlaydi (delegation — qayta render'ga chidamli)
function clHandleClick(e, root) {
  const hit = (sel) => e.target.closest(sel);
  let el;

  if ((el = hit("[data-cl-result]"))) {
    clOpenResultModal(Number(el.dataset.clResult)); return;
  }
  if ((el = hit("[data-cl-chat]"))) {
    clOpenChatThenResult(Number(el.dataset.clChat)); return;
  }
  if ((el = hit("[data-cl-open-match]"))) {
    clOpenChatThenResult(Number(el.dataset.clOpenMatch)); return;
  }
  if ((el = hit("[data-cl-confirm]"))) {
    clConfirmMatch(el.dataset.clConfirm, true); return;
  }
  if ((el = hit("[data-cl-reject]"))) {
    clConfirmMatch(el.dataset.clReject, false); return;
  }
  if ((el = hit("[data-cl-player]"))) {
    clOpenPlayerModal(Number(el.dataset.clPlayer)); return;
  }
  if ((el = hit("[data-cl-home-group]"))) {
    CL.homeGroup = Number(el.dataset.clHomeGroup); renderChampionsLeague(); return;
  }
  if ((el = hit("[data-cl-rtab]"))) {
    CL.ratingTab = el.dataset.clRtab;
    renderChampionsLeague();
    if (CL.ratingTab === "scorers") void clLoadScorers();
    else if (CL.ratingTab === "bracket") { /* 2026-07-21: clpoLoadBracket render hookida chaqiriladi */ }
    else void clLoadRating();
    return;
  }
}

async function clConfirmMatch(id, accept) {
  try {
    await apiFetch(`/cl/match/confirm?match_id=${id}&accept=${accept}`, { method: "POST" });
    showToast(accept ? CT("cl_toast_confirmed") : CT("cl_toast_rejected"));
    await clLoadMatches();
  } catch (e) {
    showToast(CT("cl_error") + e.message);
  }
}

// ============================================================
//  NATIJA KIRITISH — liga #modal-result modalidan foydalanadi (qoida #26 DRY).
//  Submit esa ChL endpointiga yo'naltiriladi (CL._resultMatchId flag orqali).
// ============================================================
// 💬 bosilganda: raqib VS-oynasi ochiladi VA shu o'yin uchun "Natija" tugmasi
// ochiladi (liga oqimi bilan bir xil: avval kelishuv, keyin natija).
function clOpenChatThenResult(matchId) {
  if (!CL.chatOpened) CL.chatOpened = new Set();
  CL.chatOpened.add(matchId);
  clOpenOpponentModal(matchId);   // VS-oyna: "Chatni ochish" / "Raqib chatiga yozish"
  renderChampionsLeague();        // 💬 → Natija tugmasiga almashadi
}

function clOpenResultModal(matchId) {
  const m = (CL.myMatches || []).find(x => String(x.id) === String(matchId));
  if (!m) { showToast(CT("cl_match_404")); return; }
  const modal = document.getElementById("modal-result");
  if (!modal) { showToast(CT("cl_modal_404")); return; }

  CL._resultMatchId = matchId;         // submitMatchResult() shu flagni tekshiradi

  // #modal-result #section-profile ichida — ChL rejimida u sektsiya .active emas
  // (display:none). Modalni body'ga ko'chiramiz, aks holda ko'rinmaydi.
  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  // Logolar: chap = player1_club, o'ng = player2_club
  const setLogo = (id, club) => {
    const el = document.getElementById(id);
    if (!el) return;
    const logo = clClubLogo(club);
    if (logo) { el.src = logo; el.alt = club || ""; el.style.display = ""; }
    else { el.removeAttribute("src"); el.style.display = "none"; }
  };
  setLogo("result-logo1", m.player1_club);
  setLogo("result-logo2", m.player2_club);

  const s1 = document.getElementById("input-score1");
  const s2 = document.getElementById("input-score2");
  if (s1) s1.value = "0";
  if (s2) s2.value = "0";

  modal.classList.remove("hidden");
}

// Modaldagi "Yuborish" bosilganda ChL o'yiniga natija yuboradi
async function clSubmitResultFromModal() {
  const id = CL._resultMatchId;
  const s1 = Number(document.getElementById("input-score1").value || 0);
  const s2 = Number(document.getElementById("input-score2").value || 0);
  try {
    await apiFetch(`/cl/match/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`,
                   { method: "POST" });
    document.getElementById("modal-result").classList.add("hidden");
    CL._resultMatchId = null;
    showToast(CT("cl_toast_result_sent"));
    await clLoadMatches();
  } catch (e) {
    const msg = { matchday_locked: CT("cl_round_locked"),
                  match_not_found: CT("cl_match_404") }[e.message] || e.message;
    showToast(CT("cl_error") + msg);
  }
}
