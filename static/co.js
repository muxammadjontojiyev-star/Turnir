// ============================================================
//  co.js — Konferensiya ligasi (KL) rejimi
//  Alohida ekran (worldcup.js naqshi). Mavjud liga/WC kodiga TEGMAYDI.
//  Rejim tanlash -> showConferenceLeague() shu yerda.
//
//  Bog'liqliklar (global): APP, apiFetch (api.js), escHtml (app.js),
//  showToast, hideModeSelect, showModeSelect.
//  Backend: GET /co/qualifiers, /co/groups, /co/rating/{n}, /co/matches/my,
//           POST /co/match/submit-result, /co/match/confirm
// ============================================================

// Yangi format (2026-08): guruh yo'q — yagona liga bosqichi.
const CO_ROUNDS = 6;    // Liga bosqichi turlari (backend: co_core.CO_ROUNDS)
const CO_TOTAL  = 36;   // Ishtirokchilar soni (backend: co_qualification.CO_TOTAL)
const CO_LEAGUE_GROUP = 1;  // Yagona reyting guruh raqami (backend: co_core.CO_LEAGUE_GROUP)
// Reyting chegaralari (backend: co_playin.CO_SEED_COUNT / CO_QUALIFY_TOTAL):
const CO_SEED_COUNT = 8;      // top-8 to'g'ridan setkaga (8/9 orasida YASHIL chiziq)
const CO_QUALIFY_TOTAL = 24;  // 9-24 pley-in (24/25 orasida QIZIL chiziq)

const CO = {
  section: "home",     // home | rating | profile | prizes
  groups: null,        // /co/groups javobi
  qualifiers: null,    // /co/qualifiers javobi (qur'agacha ko'rsatish uchun)
  ratingTab: "groups",  // Reyting tabi: "groups" | "scorers"
  scorers: null,
  ratingAll: null,
  viewPlayer: null,     // Reytingdan ochilgan ishtirokchi (co_player.js)
  rating: [],
  myMatches: [],
  meParticipant: false,
  state: null,         // /co/matches/my → tur holati (started, current_matchday)
  profile: null,       // /co/profile javobi
  unread: { total: 0, by_match: {} }, // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka)
};

// ---- Klub logosi (api.js: LEAGUE_CLUBS — qoida 26, DRY) ----
function coClubLogo(clubName) {
  if (!clubName || typeof LEAGUE_CLUBS === "undefined") return null;
  for (const clubs of Object.values(LEAGUE_CLUBS)) {
    const found = clubs.find(c => c.name === clubName);
    if (found) return found.logo;
  }
  return null;
}

// Klub logosi <img> (topilmasa — ⚽ fallback, qoida 40)
function coClubBadge(clubName, size = 24) {
  const logo = coClubLogo(clubName);
  if (!logo) return `<span class="co-club-fallback" style="width:${size}px;height:${size}px">${ICON.get("shield", Math.round(size * 0.8))}</span>`;
  return `<img class="co-club-logo" src="${escHtml(logo)}" alt="${escHtml(clubName)}" `
       + `title="${escHtml(clubName)}" style="width:${size}px;height:${size}px" `
       + `onerror="this.style.visibility='hidden'" />`;
}

// ---- Kirish nuqtasi ----
function showConferenceLeague() {
  if (typeof hideModeSelect === "function") hideModeSelect();
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));

  let root = document.getElementById("co-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "co-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  CO.section = "home";
  void coLoadThenRender();
  // 2026-07-20: rejimga kirishdayoq rozetkani yuklaymiz — Profilga kirmasdan ham ko'rinsin
  void coRefreshUnreadBadge();
}

function exitConferenceLeague() {
  const root = document.getElementById("co-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function coNavigate(section) {
  CO.section = section;
  renderConferenceLeague();
  // 2026-07-19: har sahifada o'qilmagan rozetkani yangilab turamiz (liga naqshi)
  void coRefreshUnreadBadge();
  // 2026-07-20: pir-pirash tuzatildi — navigate allaqachon render qildi; fetch'dan
  // keyin faqat ma'lumot O'ZGARGAN bo'lsa qayta chizamiz (onlyIfChanged=true)
  if (section === "rating") void (CO.ratingTab === "scorers" ? coLoadScorers(true) : coLoadRating(true));
  if (section === "profile") void coLoadProfile();
  if (section === "prizes") void coLoadProfileForPrizes();
  if (section === "admin") void coLoadAdminData();
}

// 2026-07-19: KL o'qilmagan soni — Profil nav tugmasidagi qizil rozetka (liga naqshi)
async function coRefreshUnreadBadge() {
  try {
    CO.unread = await apiFetch("/co/matches/unread");
  } catch (_) {
    CO.unread = { total: 0, by_match: {} };
  }
  coUpdateNavBadge();
}

function coUpdateNavBadge() {
  if (typeof setNavBadge !== "function") return;
  setNavBadge(
    document.querySelector('#co-root .wc-nav-item[data-co-tab="profile"]'),
    (CO.unread && CO.unread.total) || 0
  );
}

// Admin sahifasi uchun groups + state kerak (panel matnlari uchun)
async function coLoadAdminData() {
  try { CO.groups = await apiFetch("/co/groups"); } catch (_) {}
  try { CO.state = (await apiFetch("/co/state")); } catch (_) {}
  renderConferenceLeague();
}

// Sovrinlar uchun user_id kerak — profil bir marta yuklanadi
async function coLoadProfileForPrizes() {
  if (!CO.profile) {
    try { CO.profile = await apiFetch("/co/profile"); } catch (_) { CO.profile = null; }
    renderConferenceLeague();
  } else {
    void coBindPrizes();
  }
}

async function coLoadThenRender() {
  if (typeof coCheckAdmin === "function") { try { await coCheckAdmin(); } catch (_) {} }
  try {
    CO.groups = await apiFetch("/co/groups");
    CO.meParticipant = !!CO.groups.me_participant;
  } catch (_) { CO.groups = null; }
  try {
    CO.qualifiers = await apiFetch("/co/qualifiers");
  } catch (_) { CO.qualifiers = null; }
  renderConferenceLeague();
}

async function coLoadRating(onlyIfChanged = false) {
  const prev = JSON.stringify(CO.ratingAll || []);
  try {
    // 2026-07-23: yulduzchalar reyting bilan birga yangilanadi — yangi berilgan
    // kubok (co_cup) darhol ko'rinadi (ilgari faqat ilova ochilganда yuklanardi,
    // shuning uchun yangi kubok egasining ★ chiqmasди).
    const [d] = await Promise.all([
      apiFetch("/co/rating-all"),
      (typeof loadPrizeStars === "function") ? loadPrizeStars() : Promise.resolve(),
    ]);
    CO.ratingAll = d.groups || [];
    CO.rating = [];
    for (const g of CO.ratingAll) {
      g.rating.forEach((p, i) => CO.rating.push({ ...p, _group: g.group_number, _pos: i + 1 }));
    }
  } catch (_) { CO.ratingAll = []; CO.rating = []; }
  // 2026-07-20: pir-pirash tuzatildi — sahifa allaqachon chizilgan bo'lsa va
  // ma'lumot o'zgarmagan bo'lsa, ikkinchi (keraksiz) to'liq renderni o'tkazib yuboramiz
  if (onlyIfChanged && JSON.stringify(CO.ratingAll || []) === prev) return;
  renderConferenceLeague();
}

async function coLoadMatches() {
  // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka) — liga loadMyMatches naqshi
  try {
    CO.unread = await apiFetch("/co/matches/unread");
  } catch (_) {
    CO.unread = { total: 0, by_match: {} };
  }
  coUpdateNavBadge();
  try {
    const d = await apiFetch("/co/matches/my");
    CO.myMatches = d.matches || [];
    CO._myId = d.me_id ?? null;
    CO.state = d.state || null;
  } catch (_) { CO.myMatches = []; CO._myId = null; CO.state = null; }
  renderConferenceLeague();
}

// ---- RENDER ----
function renderConferenceLeague() {
  const root = document.getElementById("co-root");
  if (!root) return;

  let body = "";
  if (CO.section === "home") body = coRenderHome();
  else if (CO.section === "rating") body = coRenderRating();
  else if (CO.section === "prizes") body = coRenderPrizes();
  else if (CO.section === "player") body = coRenderPlayer();
  else if (CO.section === "admin") body = `<div id="co-admin-page"></div>`;
  else body = coRenderProfile();

  // 2026-07-22: Admin tab — bosh admin YOKI tayinlangan KL admin (isCl) ko'radi
  const adminTab = (typeof CO_ADMIN !== "undefined" && (CO_ADMIN.isSuper || CO_ADMIN.isCl)) ? `
      <button class="wc-nav-item ${CO.section === "admin" ? "active" : ""}" data-co-tab="admin">
        <span class="nav-icon" data-icon="shield"></span>
        <span class="nav-label">${COT("co_nav_admin")}</span>
      </button>` : "";

  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="co-back-btn">←</button>
      <div class="wc-header-title co-title">${ICON.get("trophy", 20)} <span>${COT("co_title")}</span></div>
    </div>
    <div class="wc-body" style="padding-bottom:90px;">${body}</div>
    <nav class="wc-nav">
      <button class="wc-nav-item ${CO.section === "home" ? "active" : ""}" data-co-tab="home">
        <span class="nav-icon" data-icon="home"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_home) || "Asosiy"}</span>
      </button>
      <button class="wc-nav-item ${CO.section === "rating" ? "active" : ""}" data-co-tab="rating">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_rating) || "Reyting"}</span>
      </button>
      <button class="wc-nav-item ${CO.section === "profile" ? "active" : ""}" data-co-tab="profile">
        <span class="nav-icon" data-icon="user"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_profile) || "Profil"}</span>
      </button>
      <button class="wc-nav-item ${CO.section === "prizes" ? "active" : ""}" data-co-tab="prizes">
        <span class="nav-icon" data-icon="gift"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_prizes) || "Sovrinlar"}</span>
      </button>${adminTab}
    </nav>
  `;

  if (typeof applyIcons === "function") applyIcons(root);
  // 2026-07-19: nav har renderda qayta quriladi — rozetkani qayta qo'yamiz
  coUpdateNavBadge();
  // 2026-07-20: play-off bloklari (boshlanmagan bo'lsa bo'sh qoladi)
  if (CO.section === "rating" && typeof copoLoadBracket === "function") void copoLoadBracket();
  if (CO.section === "profile" && typeof copoLoadMyMatches === "function") void copoLoadMyMatches();
  document.getElementById("co-back-btn").addEventListener("click", exitConferenceLeague);
  root.querySelectorAll("[data-co-tab]").forEach(b =>
    b.addEventListener("click", () => coNavigate(b.dataset.coTab)));
  coBindSectionEvents(root);
  if (CO.section === "player") coBindPlayer(root);
  if (CO.section === "profile") coBindProfile(root);
  if (CO.section === "prizes") void coBindPrizes();
  if (CO.section === "admin") void coRenderAdminPage();
}


// ---- HOME ----  → co_home.js (qoida 21: fayl 300 qatordan oshmasin)

// ---- SCORERS (to'purarlar) ----
async function coLoadScorers(onlyIfChanged = false) {
  const prev = JSON.stringify(CO.scorers || []);
  try {
    const d = await apiFetch("/co/scorers");
    CO.scorers = d.scorers || [];
  } catch (_) { CO.scorers = []; }
  // 2026-07-20: pir-pirash tuzatildi (coLoadRating bilan bir xil mantiq)
  if (onlyIfChanged && JSON.stringify(CO.scorers || []) === prev) return;
  renderConferenceLeague();
}

function coRenderScorers() {
  const rows = CO.scorers;
  if (rows === null) return `<div class="wc-loading-row">${COT("co_loading")}</div>`;
  if (!rows.length) return `<div class="wc-loading-row">${COT("co_no_goals")}</div>`;

  const body = rows.map((p, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><div class="co-rating-player" data-co-player="${p.user_id}">
        ${coClubBadge(p.club_name, 22)}
        <span class="co-rating-user">${escHtml(p.username ? "@" + p.username : (p.nickname || ""))}${prizeStarsHtml(p)}</span>
      </div></td>
      <td>${p.played}</td>
      <td><b>${p.goals}</b></td>
    </tr>`).join("");

  return `
    <table class="rating-table">
      <thead><tr><th>#</th><th>${COT("co_player_col")}</th><th>${COT("co_played_col")}</th><th>${COT("co_col_goals")}</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

// ---- RATING ----
function coRenderRating() {
  const tabs = `
    <div class="co-rating-tabs">
      <button class="tab-btn${CO.ratingTab === "groups" ? " active" : ""}" data-co-rtab="groups">${COT("co_tab_groups")}</button>
      <button class="tab-btn${CO.ratingTab === "scorers" ? " active" : ""}" data-co-rtab="scorers">${COT("co_tab_scorers")}</button>
      <button class="tab-btn${CO.ratingTab === "bracket" ? " active" : ""}" data-co-rtab="bracket">${COT("co_tab_bracket")}</button>
    </div>`;
  if (CO.ratingTab === "scorers") return `${tabs}<div class="card card--table">${coRenderScorers()}</div>`;
  // 2026-07-21: Setka — WC kabi ALOHIDA tab (co_playoff.js copoLoadBracket to'ldiradi)
  if (CO.ratingTab === "bracket")
    return `${tabs}<div id="co-po-bracket-box"><div class="wc-loading-row">Yuklanmoqda…</div></div>`;

  // Barcha guruhlar ketma-ket (Guruh 1 → jadval, Guruh 2 → jadval ...)
  const groups = CO.ratingAll;
  if (groups === null || groups === undefined) return `${tabs}<div class="wc-loading-row">${COT("co_loading")}</div>`;
  if (!groups.length) return `${tabs}<div class="card">${COT("co_no_groups")}</div>`;

  // Yangi format: yagona umumiy reyting (bitta "guruh"). Guruh sarlavhasi ko'rsatilmaydi.
  // 8/9 orasida YASHIL chiziq (top-8 to'g'ridan setkaga), 24/25 orasida QIZIL chiziq
  // (9-24 pley-in; 24 dan pastda KL tugaydi) — qoida #17: konstantalar yuqorida.
  const blocks = groups.map(g => {
    const rows = g.rating.map((p, i) => {
      const pos = i + 1;
      const cut = pos === CO_SEED_COUNT ? " co-cut-green"
                : pos === CO_QUALIFY_TOTAL ? " co-cut-red" : "";
      return `
      <tr class="co-rating-row${cut}">
        <td class="rank-${i + 1}">${i + 1}</td>
        <td><div class="co-rating-player" data-co-player="${p.user_id}">${coClubBadge(p.club_name, 22)}<span class="co-rating-user">${escHtml(p.username ? "@" + p.username : (p.nickname || ""))}${prizeStarsHtml(p)}</span></div></td>
        <td>${p.played}</td><td>${p.goal_difference > 0 ? "+" : ""}${p.goal_difference}</td>
        <td><b>${p.points}</b></td>
      </tr>`;
    }).join("");
    return `
      <div class="card card--table" style="margin-bottom:14px">
        <table class="rating-table">
          <thead><tr><th>#</th><th>${COT("co_player_col")}</th><th>${COT("co_played_col")}</th><th>GF</th><th>${COT("co_col_points")}</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }).join("");

  return `${tabs}${blocks}`;
}

// ---- MATCHES ----
function coRenderMatches() {
  if (!CO.meParticipant) {
    return `<div class="card">${COT("co_not_participant")}</div>`;
  }
  const ms = CO.myMatches || [];
  if (!ms.length) {
    return `<div class="wc-loading-row">${COT("co_no_matches")}</div>`;
  }
  return `<div class="matches-list">${ms.map(coRenderMatchItem).join("")}</div>`;
}

// Bitta o'yin kartasi (worldcup_matches.js — wcRenderMatchItem naqshi, qoida 10)
function coRenderMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  // 2026-07-19: o'qilmagan chat rozetka — RAQIB logosi ustida (liga naqshi)
  const unreadCount = (CO.unread && CO.unread.by_match && CO.unread.by_match[m.id]) || 0;
  const unreadBadge = unreadCount > 0
    ? `<span class="chat-badge">${unreadCount > 9 ? "9+" : unreadCount}</span>`
    : "";
  const iAmPlayer1 = coIsMe(m.player1_id);
  const center = `
    <span class="co-mc-logo match-badge-wrap">${coClubBadge(m.player1_club, 26)}${iAmPlayer1 ? "" : unreadBadge}</span>
    <span class="match-score">${score}</span>
    <span class="co-mc-logo match-badge-wrap">${coClubBadge(m.player2_club, 26)}${iAmPlayer1 ? unreadBadge : ""}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "pending" && !(CO.state?.started && m.matchday === CO.state.current_matchday)) {
    statusText = "YOPIQ";
  }
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "admin_pending")         { statusCls = "status--awaiting"; statusText = "ADMIN TASDIG'I"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  const st = CO.state || {};
  const isOpenRound = !!st.started && m.matchday === st.current_matchday;

  let action = "";
  if (m.status === "pending") {
    if (!isOpenRound) {
      action = `<span class="co-locked" title="${COT("co_round_locked")}">${ICON.get("lock", 16)}</span>`;
    } else {
      // 2026-10-11: soddalashtirildi — "Natija" darhol, yonida 💬 (VS-oyna: xona ID / bot chati / Telegram)
      action = `<button class="match-action-btn" data-co-result="${m.id}">${COT("co_result")}</button>`
        + `<button class="match-action-btn match-chat-btn" data-co-chat="${m.id}" title="${COT("co_agree_first")}">${ICON.get("chat", 18)}</button>`;
    }
  } else if (m.status === "awaiting_confirmation") {
    action = (m.submitted_by && !coIsMe(m.submitted_by))
      ? `<button class="match-action-btn" data-co-confirm="${m.id}">${ICON.get("check", 16)}</button>`
      : `<span class="match-waiting">${COT("co_pending")}</span>`;
  }

  const reject = (m.status === "awaiting_confirmation" && m.submitted_by && !coIsMe(m.submitted_by))
    ? `<div class="co-score-row"><button class="btn" data-co-reject="${m.id}">${ICON.get("cross", 15)} ${COT("co_reject")}</button></div>` : "";

  // Uy/mehmon: player1 — uy egasi (co_matches yozilish tartibi)
  const isHome = coIsMe(m.player1_id);
  const venue = isHome
    ? `<span class="co-venue co-venue--home">UY</span>`
    : `<span class="co-venue co-venue--away">MEHMON</span>`;

  // 2026-07-16: Yopiq (hali ochilmagan) turda VS/chat oynasi ochilmaydi
  // (liga is_locked naqshi). O'ynalgan/o'tgan o'yinlar — ochiq (tarix).
  const canOpenVs = isOpenRound || m.status !== "pending";
  const centerCls = canOpenVs ? "match-center match-center--clickable" : "match-center";
  const centerAttr = canOpenVs ? `data-co-open-match="${m.id}"` : "";

  return `
    <div class="co-match-wrap">
      <div class="co-match-head">
        <span class="co-match-round">${m.matchday}-tur</span><span class="co-match-id">#${m.id}</span>
        ${venue}
        ${m.status === "pending" && isOpenRound ? "" : `<span class="match-status ${statusCls}">${statusText}</span>`}
      </div>
      <div class="co-match-body">
        <div class="${centerCls}" ${centerAttr}>${center}</div>
        ${action}
      </div>
      ${reject}
    </div>`;
}

function coIsMe(userId) {
  // me_id backend'dan keladi (/co/matches/my) — taxmin qilinmaydi
  return CO._myId !== null && CO._myId !== undefined && userId === CO._myId;
}

function coStatusLabel(s) {
  return ({ pending: COT("co_pending"), awaiting_confirmation: COT("co_awaiting"),
            confirmed: COT("co_confirmed"), admin_pending: COT("co_admin_pending") })[s] || s;
}

// ---- Eventlar ----
function coBindSectionEvents(root) {
  // Event delegation: bitta listener butun co-root uchun (qayta render'da yo'qolmaydi).
  if (!root._coDelegated) {
    root._coDelegated = true;
    root.addEventListener("click", (e) => coHandleClick(e, root));
  }

}

// Barcha KL bosishlarini bitta joyda ushlaydi (delegation — qayta render'ga chidamli)
function coHandleClick(e, root) {
  const hit = (sel) => e.target.closest(sel);
  let co;

  if ((co = hit("[data-co-result]"))) {
    coOpenResultModal(Number(co.dataset.coResult)); return;
  }
  if ((co = hit("[data-co-chat]"))) {
    coOpenChatThenResult(Number(co.dataset.coChat)); return;
  }
  if ((co = hit("[data-co-open-match]"))) {
    coOpenChatThenResult(Number(co.dataset.coOpenMatch)); return;
  }
  if ((co = hit("[data-co-confirm]"))) {
    coConfirmMatch(co.dataset.coConfirm, true); return;
  }
  if ((co = hit("[data-co-reject]"))) {
    coConfirmMatch(co.dataset.coReject, false); return;
  }
  if ((co = hit("[data-co-player]"))) {
    coOpenPlayerModal(Number(co.dataset.coPlayer)); return;
  }
  if ((co = hit("[data-co-rtab]"))) {
    CO.ratingTab = co.dataset.coRtab;
    renderConferenceLeague();
    if (CO.ratingTab === "scorers") void coLoadScorers();
    else if (CO.ratingTab === "bracket") { /* 2026-07-21: copoLoadBracket render hookida chaqiriladi */ }
    else void coLoadRating();
    return;
  }
}

async function coConfirmMatch(id, accept) {
  try {
    await apiFetch(`/co/match/confirm?match_id=${id}&accept=${accept}`, { method: "POST" });
    showToast(accept ? COT("co_toast_confirmed") : COT("co_toast_rejected"));
    await coLoadMatches();
  } catch (e) {
    showToast(COT("co_error") + e.message);
  }
}

// ============================================================
//  NATIJA KIRITISH — liga #modal-result modalidan foydalanadi (qoida #26 DRY).
//  Submit esa KL endpointiga yo'naltiriladi (CO._resultMatchId flag orqali).
// ============================================================
// 💬 bosilganda: raqib VS-oynasi ochiladi VA shu o'yin uchun "Natija" tugmasi
// ochiladi (liga oqimi bilan bir xil: avval kelishuv, keyin natija).
function coOpenChatThenResult(matchId) {
  if (!CO.chatOpened) CO.chatOpened = new Set();
  CO.chatOpened.add(matchId);
  coOpenOpponentModal(matchId);   // VS-oyna: "Chatni ochish" / "Raqib chatiga yozish"
  renderConferenceLeague();        // 💬 → Natija tugmasiga almashadi
}

function coOpenResultModal(matchId) {
  const m = (CO.myMatches || []).find(x => String(x.id) === String(matchId));
  if (!m) { showToast(COT("co_match_404")); return; }
  const modal = document.getElementById("modal-result");
  if (!modal) { showToast(COT("co_modal_404")); return; }

  CO._resultMatchId = matchId;         // submitMatchResult() shu flagni tekshiradi

  // #modal-result #section-profile ichida — KL rejimida u sektsiya .active emas
  // (display:none). Modalni body'ga ko'chiramiz, aks holda ko'rinmaydi.
  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  // Logolar: chap = player1_club, o'ng = player2_club
  const setLogo = (id, club) => {
    const co = document.getElementById(id);
    if (!co) return;
    const logo = coClubLogo(club);
    if (logo) { co.src = logo; co.alt = club || ""; co.style.display = ""; }
    else { co.removeAttribute("src"); co.style.display = "none"; }
  };
  setLogo("result-logo1", m.player1_club);
  setLogo("result-logo2", m.player2_club);

  const s1 = document.getElementById("input-score1");
  const s2 = document.getElementById("input-score2");
  if (s1) s1.value = "0";
  if (s2) s2.value = "0";

  modal.classList.remove("hidden");
}

// Modaldagi "Yuborish" bosilganda KL o'yiniga natija yuboradi
async function coSubmitResultFromModal() {
  const id = CO._resultMatchId;
  const s1 = Number(document.getElementById("input-score1").value || 0);
  const s2 = Number(document.getElementById("input-score2").value || 0);
  try {
    const res = await apiFetch(`/co/match/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`,
                   { method: "POST" });
    document.getElementById("modal-result").classList.add("hidden");
    CO._resultMatchId = null;
    // 2026-10-13: katta hisob — skrinshotni shu rejim adminiga yuborish oynasi
    if (typeof isBigScoreResponse === "function" && isBigScoreResponse(res)) openBigScoreModal("co");
    else showToast(COT("co_toast_result_sent"));
    await coLoadMatches();
  } catch (e) {
    const msg = { matchday_locked: COT("co_round_locked"),
                  match_not_found: COT("co_match_404") }[e.message] || e.message;
    showToast(COT("co_error") + msg);
  }
}
