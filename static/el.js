// ============================================================
//  el.js — Yevropa ligasi (YeL) rejimi
//  Alohida ekran (worldcup.js naqshi). Mavjud liga/WC kodiga TEGMAYDI.
//  Rejim tanlash -> showEuropaLeague() shu yerda.
//
//  Bog'liqliklar (global): APP, apiFetch (api.js), escHtml (app.js),
//  showToast, hideModeSelect, showModeSelect.
//  Backend: GET /el/qualifiers, /el/groups, /el/rating/{n}, /el/matches/my,
//           POST /el/match/submit-result, /el/match/confirm
// ============================================================

// Yangi format (2026-08): guruh yo'q — yagona liga bosqichi.
const EL_ROUNDS = 8;    // Liga bosqichi turlari (backend: el_core.EL_ROUNDS)
const EL_TOTAL  = 36;   // Ishtirokchilar soni (backend: el_qualification.EL_TOTAL)
const EL_LEAGUE_GROUP = 1;  // Yagona reyting guruh raqami (backend: el_core.EL_LEAGUE_GROUP)
// Reyting chegaralari (backend: el_playin.EL_SEED_COUNT / EL_QUALIFY_TOTAL):
const EL_SEED_COUNT = 8;      // top-8 to'g'ridan setkaga (8/9 orasida YASHIL chiziq)
const EL_QUALIFY_TOTAL = 24;  // 9-24 pley-in (24/25 orasida QIZIL chiziq)

const EL = {
  section: "home",     // home | rating | profile | prizes
  groups: null,        // /el/groups javobi
  qualifiers: null,    // /el/qualifiers javobi (qur'agacha ko'rsatish uchun)
  ratingTab: "groups",  // Reyting tabi: "groups" | "scorers"
  scorers: null,
  ratingAll: null,
  viewPlayer: null,     // Reytingdan ochilgan ishtirokchi (el_player.js)
  rating: [],
  myMatches: [],
  meParticipant: false,
  state: null,         // /el/matches/my → tur holati (started, current_matchday)
  profile: null,       // /el/profile javobi
  unread: { total: 0, by_match: {} }, // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka)
};

// ---- Klub logosi (api.js: LEAGUE_CLUBS — qoida 26, DRY) ----
function elClubLogo(clubName) {
  if (!clubName || typeof LEAGUE_CLUBS === "undefined") return null;
  for (const clubs of Object.values(LEAGUE_CLUBS)) {
    const found = clubs.find(c => c.name === clubName);
    if (found) return found.logo;
  }
  return null;
}

// Klub logosi <img> (topilmasa — ⚽ fallback, qoida 40)
function elClubBadge(clubName, size = 24) {
  const logo = elClubLogo(clubName);
  if (!logo) return `<span class="el-club-fallback" style="width:${size}px;height:${size}px">${ICON.get("shield", Math.round(size * 0.8))}</span>`;
  return `<img class="el-club-logo" src="${escHtml(logo)}" alt="${escHtml(clubName)}" `
       + `title="${escHtml(clubName)}" style="width:${size}px;height:${size}px" `
       + `onerror="this.style.visibility='hidden'" />`;
}

// ---- Kirish nuqtasi ----
function showEuropaLeague() {
  if (typeof hideModeSelect === "function") hideModeSelect();
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));

  let root = document.getElementById("el-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "el-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  EL.section = "home";
  void elLoadThenRender();
  // 2026-07-20: rejimga kirishdayoq rozetkani yuklaymiz — Profilga kirmasdan ham ko'rinsin
  void elRefreshUnreadBadge();
}

function exitEuropaLeague() {
  const root = document.getElementById("el-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function elNavigate(section) {
  EL.section = section;
  renderEuropaLeague();
  // 2026-07-19: har sahifada o'qilmagan rozetkani yangilab turamiz (liga naqshi)
  void elRefreshUnreadBadge();
  // 2026-07-20: pir-pirash tuzatildi — navigate allaqachon render qildi; fetch'dan
  // keyin faqat ma'lumot O'ZGARGAN bo'lsa qayta chizamiz (onlyIfChanged=true)
  if (section === "rating") void (EL.ratingTab === "scorers" ? elLoadScorers(true) : elLoadRating(true));
  if (section === "profile") void elLoadProfile();
  if (section === "prizes") void elLoadProfileForPrizes();
  if (section === "admin") void elLoadAdminData();
}

// 2026-07-19: YeL o'qilmagan soni — Profil nav tugmasidagi qizil rozetka (liga naqshi)
async function elRefreshUnreadBadge() {
  try {
    EL.unread = await apiFetch("/el/matches/unread");
  } catch (_) {
    EL.unread = { total: 0, by_match: {} };
  }
  elUpdateNavBadge();
}

function elUpdateNavBadge() {
  if (typeof setNavBadge !== "function") return;
  setNavBadge(
    document.querySelector('#el-root .wc-nav-item[data-el-tab="profile"]'),
    (EL.unread && EL.unread.total) || 0
  );
}

// Admin sahifasi uchun groups + state kerak (panel matnlari uchun)
async function elLoadAdminData() {
  try { EL.groups = await apiFetch("/el/groups"); } catch (_) {}
  try { EL.state = (await apiFetch("/el/state")); } catch (_) {}
  renderEuropaLeague();
}

// Sovrinlar uchun user_id kerak — profil bir marta yuklanadi
async function elLoadProfileForPrizes() {
  if (!EL.profile) {
    try { EL.profile = await apiFetch("/el/profile"); } catch (_) { EL.profile = null; }
    renderEuropaLeague();
  } else {
    void elBindPrizes();
  }
}

async function elLoadThenRender() {
  if (typeof elCheckAdmin === "function") { try { await elCheckAdmin(); } catch (_) {} }
  try {
    EL.groups = await apiFetch("/el/groups");
    EL.meParticipant = !!EL.groups.me_participant;
  } catch (_) { EL.groups = null; }
  try {
    EL.qualifiers = await apiFetch("/el/qualifiers");
  } catch (_) { EL.qualifiers = null; }
  renderEuropaLeague();
}

async function elLoadRating(onlyIfChanged = false) {
  const prev = JSON.stringify(EL.ratingAll || []);
  try {
    // 2026-07-23: yulduzchalar reyting bilan birga yangilanadi — yangi berilgan
    // kubok (el_cup) darhol ko'rinadi (ilgari faqat ilova ochilganда yuklanardi,
    // shuning uchun yangi kubok egasining ★ chiqmasди).
    const [d] = await Promise.all([
      apiFetch("/el/rating-all"),
      (typeof loadPrizeStars === "function") ? loadPrizeStars() : Promise.resolve(),
    ]);
    EL.ratingAll = d.groups || [];
    EL.rating = [];
    for (const g of EL.ratingAll) {
      g.rating.forEach((p, i) => EL.rating.push({ ...p, _group: g.group_number, _pos: i + 1 }));
    }
  } catch (_) { EL.ratingAll = []; EL.rating = []; }
  // 2026-07-20: pir-pirash tuzatildi — sahifa allaqachon chizilgan bo'lsa va
  // ma'lumot o'zgarmagan bo'lsa, ikkinchi (keraksiz) to'liq renderni o'tkazib yuboramiz
  if (onlyIfChanged && JSON.stringify(EL.ratingAll || []) === prev) return;
  renderEuropaLeague();
}

async function elLoadMatches() {
  // 2026-07-19: o'qilmagan chat xabarlari (qizil rozetka) — liga loadMyMatches naqshi
  try {
    EL.unread = await apiFetch("/el/matches/unread");
  } catch (_) {
    EL.unread = { total: 0, by_match: {} };
  }
  elUpdateNavBadge();
  try {
    const d = await apiFetch("/el/matches/my");
    EL.myMatches = d.matches || [];
    EL._myId = d.me_id ?? null;
    EL.state = d.state || null;
  } catch (_) { EL.myMatches = []; EL._myId = null; EL.state = null; }
  renderEuropaLeague();
}

// ---- RENDER ----
function renderEuropaLeague() {
  const root = document.getElementById("el-root");
  if (!root) return;

  let body = "";
  if (EL.section === "home") body = elRenderHome();
  else if (EL.section === "rating") body = elRenderRating();
  else if (EL.section === "prizes") body = elRenderPrizes();
  else if (EL.section === "player") body = elRenderPlayer();
  else if (EL.section === "admin") body = `<div id="el-admin-page"></div>`;
  else body = elRenderProfile();

  // 2026-07-22: Admin tab — bosh admin YOKI tayinlangan YeL admin (isCl) ko'radi
  const adminTab = (typeof EL_ADMIN !== "undefined" && (EL_ADMIN.isSuper || EL_ADMIN.isCl)) ? `
      <button class="wc-nav-item ${EL.section === "admin" ? "active" : ""}" data-el-tab="admin">
        <span class="nav-icon" data-icon="shield"></span>
        <span class="nav-label">${ET("el_nav_admin")}</span>
      </button>` : "";

  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="el-back-btn">←</button>
      <div class="wc-header-title el-title">${ICON.get("trophy", 20)} <span>${ET("el_title")}</span></div>
    </div>
    <div class="wc-body" style="padding-bottom:90px;">${body}</div>
    <nav class="wc-nav">
      <button class="wc-nav-item ${EL.section === "home" ? "active" : ""}" data-el-tab="home">
        <span class="nav-icon" data-icon="home"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_home) || "Asosiy"}</span>
      </button>
      <button class="wc-nav-item ${EL.section === "rating" ? "active" : ""}" data-el-tab="rating">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_rating) || "Reyting"}</span>
      </button>
      <button class="wc-nav-item ${EL.section === "profile" ? "active" : ""}" data-el-tab="profile">
        <span class="nav-icon" data-icon="user"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_profile) || "Profil"}</span>
      </button>
      <button class="wc-nav-item ${EL.section === "prizes" ? "active" : ""}" data-el-tab="prizes">
        <span class="nav-icon" data-icon="gift"></span>
        <span class="nav-label">${(APP.t && APP.t.nav_prizes) || "Sovrinlar"}</span>
      </button>${adminTab}
    </nav>
  `;

  if (typeof applyIcons === "function") applyIcons(root);
  // 2026-07-19: nav har renderda qayta quriladi — rozetkani qayta qo'yamiz
  elUpdateNavBadge();
  // 2026-07-20: play-off bloklari (boshlanmagan bo'lsa bo'sh qoladi)
  if (EL.section === "rating" && typeof elpoLoadBracket === "function") void elpoLoadBracket();
  if (EL.section === "profile" && typeof elpoLoadMyMatches === "function") void elpoLoadMyMatches();
  document.getElementById("el-back-btn").addEventListener("click", exitEuropaLeague);
  root.querySelectorAll("[data-el-tab]").forEach(b =>
    b.addEventListener("click", () => elNavigate(b.dataset.elTab)));
  elBindSectionEvents(root);
  if (EL.section === "player") elBindPlayer(root);
  if (EL.section === "profile") elBindProfile(root);
  if (EL.section === "prizes") void elBindPrizes();
  if (EL.section === "admin") void elRenderAdminPage();
}


// ---- HOME ----  → el_home.js (qoida 21: fayl 300 qatordan oshmasin)

// ---- SCORERS (to'purarlar) ----
async function elLoadScorers(onlyIfChanged = false) {
  const prev = JSON.stringify(EL.scorers || []);
  try {
    const d = await apiFetch("/el/scorers");
    EL.scorers = d.scorers || [];
  } catch (_) { EL.scorers = []; }
  // 2026-07-20: pir-pirash tuzatildi (elLoadRating bilan bir xil mantiq)
  if (onlyIfChanged && JSON.stringify(EL.scorers || []) === prev) return;
  renderEuropaLeague();
}

function elRenderScorers() {
  const rows = EL.scorers;
  if (rows === null) return `<div class="wc-loading-row">${ET("el_loading")}</div>`;
  if (!rows.length) return `<div class="wc-loading-row">${ET("el_no_goals")}</div>`;

  const body = rows.map((p, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><div class="el-rating-player" data-el-player="${p.user_id}">
        ${elClubBadge(p.club_name, 22)}
        <span class="el-rating-user">${escHtml(p.username ? "@" + p.username : (p.nickname || ""))}${prizeStarsHtml(p)}</span>
      </div></td>
      <td>${p.played}</td>
      <td><b>${p.goals}</b></td>
    </tr>`).join("");

  return `
    <table class="rating-table">
      <thead><tr><th>#</th><th>${ET("el_player_col")}</th><th>${ET("el_played_col")}</th><th>${ET("el_col_goals")}</th></tr></thead>
      <tbody>${body}</tbody>
    </table>`;
}

// ---- RATING ----
function elRenderRating() {
  const tabs = `
    <div class="el-rating-tabs">
      <button class="tab-btn${EL.ratingTab === "groups" ? " active" : ""}" data-el-rtab="groups">${ET("el_tab_groups")}</button>
      <button class="tab-btn${EL.ratingTab === "scorers" ? " active" : ""}" data-el-rtab="scorers">${ET("el_tab_scorers")}</button>
      <button class="tab-btn${EL.ratingTab === "bracket" ? " active" : ""}" data-el-rtab="bracket">${ET("el_tab_bracket")}</button>
    </div>`;
  if (EL.ratingTab === "scorers") return `${tabs}<div class="card card--table">${elRenderScorers()}</div>`;
  // 2026-07-21: Setka — WC kabi ALOHIDA tab (el_playoff.js elpoLoadBracket to'ldiradi)
  if (EL.ratingTab === "bracket")
    return `${tabs}<div id="el-po-bracket-box"><div class="wc-loading-row">Yuklanmoqda…</div></div>`;

  // Barcha guruhlar ketma-ket (Guruh 1 → jadval, Guruh 2 → jadval ...)
  const groups = EL.ratingAll;
  if (groups === null || groups === undefined) return `${tabs}<div class="wc-loading-row">${ET("el_loading")}</div>`;
  if (!groups.length) return `${tabs}<div class="card">${ET("el_no_groups")}</div>`;

  // Yangi format: yagona umumiy reyting (bitta "guruh"). Guruh sarlavhasi ko'rsatilmaydi.
  // 8/9 orasida YASHIL chiziq (top-8 to'g'ridan setkaga), 24/25 orasida QIZIL chiziq
  // (9-24 pley-in; 24 dan pastda YeL tugaydi) — qoida #17: konstantalar yuqorida.
  const blocks = groups.map(g => {
    const rows = g.rating.map((p, i) => {
      const pos = i + 1;
      const cut = pos === EL_SEED_COUNT ? " el-cut-green"
                : pos === EL_QUALIFY_TOTAL ? " el-cut-red" : "";
      return `
      <tr class="el-rating-row${cut}">
        <td class="rank-${i + 1}">${i + 1}</td>
        <td><div class="el-rating-player" data-el-player="${p.user_id}">${elClubBadge(p.club_name, 22)}<span class="el-rating-user">${escHtml(p.username ? "@" + p.username : (p.nickname || ""))}${prizeStarsHtml(p)}</span></div></td>
        <td>${p.played}</td><td>${p.goal_difference > 0 ? "+" : ""}${p.goal_difference}</td>
        <td><b>${p.points}</b></td>
      </tr>`;
    }).join("");
    return `
      <div class="card card--table" style="margin-bottom:14px">
        <table class="rating-table">
          <thead><tr><th>#</th><th>${ET("el_player_col")}</th><th>${ET("el_played_col")}</th><th>GF</th><th>${ET("el_col_points")}</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }).join("");

  return `${tabs}${blocks}`;
}

// ---- MATCHES ----
function elRenderMatches() {
  if (!EL.meParticipant) {
    return `<div class="card">${ET("el_not_participant")}</div>`;
  }
  const ms = EL.myMatches || [];
  if (!ms.length) {
    return `<div class="wc-loading-row">${ET("el_no_matches")}</div>`;
  }
  return `<div class="matches-list">${ms.map(elRenderMatchItem).join("")}</div>`;
}

// Bitta o'yin kartasi (worldcup_matches.js — wcRenderMatchItem naqshi, qoida 10)
function elRenderMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  // 2026-07-19: o'qilmagan chat rozetka — RAQIB logosi ustida (liga naqshi)
  const unreadCount = (EL.unread && EL.unread.by_match && EL.unread.by_match[m.id]) || 0;
  const unreadBadge = unreadCount > 0
    ? `<span class="chat-badge">${unreadCount > 9 ? "9+" : unreadCount}</span>`
    : "";
  const iAmPlayer1 = elIsMe(m.player1_id);
  const center = `
    <span class="el-mc-logo match-badge-wrap">${elClubBadge(m.player1_club, 26)}${iAmPlayer1 ? "" : unreadBadge}</span>
    <span class="match-score">${score}</span>
    <span class="el-mc-logo match-badge-wrap">${elClubBadge(m.player2_club, 26)}${iAmPlayer1 ? unreadBadge : ""}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "pending" && !(EL.state?.started && m.matchday === EL.state.current_matchday)) {
    statusText = "YOPIQ";
  }
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "admin_pending")         { statusCls = "status--awaiting"; statusText = "ADMIN TASDIG'I"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  const st = EL.state || {};
  const isOpenRound = !!st.started && m.matchday === st.current_matchday;

  let action = "";
  if (m.status === "pending") {
    if (!isOpenRound) {
      action = `<span class="el-locked" title="${ET("el_round_locked")}">${ICON.get("lock", 16)}</span>`;
    } else if (EL.chatOpened && EL.chatOpened.has(m.id)) {
      // Chat ochilgan — endi "Natija" tugmasi
      action = `<button class="match-action-btn" data-el-result="${m.id}">${ET("el_result")}</button>`;
    } else {
      // Avval raqib bilan chat: 💬 tugmasi (bosilgach Natija ochiladi)
      action = `<button class="match-action-btn match-chat-btn" data-el-chat="${m.id}" title="${ET("el_agree_first")}">${ICON.get("chat", 18)}</button>`;
    }
  } else if (m.status === "awaiting_confirmation") {
    action = (m.submitted_by && !elIsMe(m.submitted_by))
      ? `<button class="match-action-btn" data-el-confirm="${m.id}">${ICON.get("check", 16)}</button>`
      : `<span class="match-waiting">${ET("el_pending")}</span>`;
  }

  const reject = (m.status === "awaiting_confirmation" && m.submitted_by && !elIsMe(m.submitted_by))
    ? `<div class="el-score-row"><button class="btn" data-el-reject="${m.id}">${ICON.get("cross", 15)} ${ET("el_reject")}</button></div>` : "";

  // Uy/mehmon: player1 — uy egasi (el_matches yozilish tartibi)
  const isHome = elIsMe(m.player1_id);
  const venue = isHome
    ? `<span class="el-venue el-venue--home">UY</span>`
    : `<span class="el-venue el-venue--away">MEHMON</span>`;

  // 2026-07-16: Yopiq (hali ochilmagan) turda VS/chat oynasi ochilmaydi
  // (liga is_locked naqshi). O'ynalgan/o'tgan o'yinlar — ochiq (tarix).
  const canOpenVs = isOpenRound || m.status !== "pending";
  const centerCls = canOpenVs ? "match-center match-center--clickable" : "match-center";
  const centerAttr = canOpenVs ? `data-el-open-match="${m.id}"` : "";

  return `
    <div class="el-match-wrap">
      <div class="el-match-head">
        <span class="el-match-round">${m.matchday}-tur</span><span class="el-match-id">#${m.id}</span>
        ${venue}
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="el-match-body">
        <div class="${centerCls}" ${centerAttr}>${center}</div>
        ${action}
      </div>
      ${reject}
    </div>`;
}

function elIsMe(userId) {
  // me_id backend'dan keladi (/el/matches/my) — taxmin qilinmaydi
  return EL._myId !== null && EL._myId !== undefined && userId === EL._myId;
}

function elStatusLabel(s) {
  return ({ pending: ET("el_pending"), awaiting_confirmation: ET("el_awaiting"),
            confirmed: ET("el_confirmed"), admin_pending: ET("el_admin_pending") })[s] || s;
}

// ---- Eventlar ----
function elBindSectionEvents(root) {
  // Event delegation: bitta listener butun el-root uchun (qayta render'da yo'qolmaydi).
  if (!root._elDelegated) {
    root._elDelegated = true;
    root.addEventListener("click", (e) => elHandleClick(e, root));
  }

}

// Barcha YeL bosishlarini bitta joyda ushlaydi (delegation — qayta render'ga chidamli)
function elHandleClick(e, root) {
  const hit = (sel) => e.target.closest(sel);
  let el;

  if ((el = hit("[data-el-result]"))) {
    elOpenResultModal(Number(el.dataset.elResult)); return;
  }
  if ((el = hit("[data-el-chat]"))) {
    elOpenChatThenResult(Number(el.dataset.elChat)); return;
  }
  if ((el = hit("[data-el-open-match]"))) {
    elOpenChatThenResult(Number(el.dataset.elOpenMatch)); return;
  }
  if ((el = hit("[data-el-confirm]"))) {
    elConfirmMatch(el.dataset.elConfirm, true); return;
  }
  if ((el = hit("[data-el-reject]"))) {
    elConfirmMatch(el.dataset.elReject, false); return;
  }
  if ((el = hit("[data-el-player]"))) {
    elOpenPlayerModal(Number(el.dataset.elPlayer)); return;
  }
  if ((el = hit("[data-el-rtab]"))) {
    EL.ratingTab = el.dataset.elRtab;
    renderEuropaLeague();
    if (EL.ratingTab === "scorers") void elLoadScorers();
    else if (EL.ratingTab === "bracket") { /* 2026-07-21: elpoLoadBracket render hookida chaqiriladi */ }
    else void elLoadRating();
    return;
  }
}

async function elConfirmMatch(id, accept) {
  try {
    await apiFetch(`/el/match/confirm?match_id=${id}&accept=${accept}`, { method: "POST" });
    showToast(accept ? ET("el_toast_confirmed") : ET("el_toast_rejected"));
    await elLoadMatches();
  } catch (e) {
    showToast(ET("el_error") + e.message);
  }
}

// ============================================================
//  NATIJA KIRITISH — liga #modal-result modalidan foydalanadi (qoida #26 DRY).
//  Submit esa YeL endpointiga yo'naltiriladi (EL._resultMatchId flag orqali).
// ============================================================
// 💬 bosilganda: raqib VS-oynasi ochiladi VA shu o'yin uchun "Natija" tugmasi
// ochiladi (liga oqimi bilan bir xil: avval kelishuv, keyin natija).
function elOpenChatThenResult(matchId) {
  if (!EL.chatOpened) EL.chatOpened = new Set();
  EL.chatOpened.add(matchId);
  elOpenOpponentModal(matchId);   // VS-oyna: "Chatni ochish" / "Raqib chatiga yozish"
  renderEuropaLeague();        // 💬 → Natija tugmasiga almashadi
}

function elOpenResultModal(matchId) {
  const m = (EL.myMatches || []).find(x => String(x.id) === String(matchId));
  if (!m) { showToast(ET("el_match_404")); return; }
  const modal = document.getElementById("modal-result");
  if (!modal) { showToast(ET("el_modal_404")); return; }

  EL._resultMatchId = matchId;         // submitMatchResult() shu flagni tekshiradi

  // #modal-result #section-profile ichida — YeL rejimida u sektsiya .active emas
  // (display:none). Modalni body'ga ko'chiramiz, aks holda ko'rinmaydi.
  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  // Logolar: chap = player1_club, o'ng = player2_club
  const setLogo = (id, club) => {
    const el = document.getElementById(id);
    if (!el) return;
    const logo = elClubLogo(club);
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

// Modaldagi "Yuborish" bosilganda YeL o'yiniga natija yuboradi
async function elSubmitResultFromModal() {
  const id = EL._resultMatchId;
  const s1 = Number(document.getElementById("input-score1").value || 0);
  const s2 = Number(document.getElementById("input-score2").value || 0);
  try {
    await apiFetch(`/el/match/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`,
                   { method: "POST" });
    document.getElementById("modal-result").classList.add("hidden");
    EL._resultMatchId = null;
    showToast(ET("el_toast_result_sent"));
    await elLoadMatches();
  } catch (e) {
    const msg = { matchday_locked: ET("el_round_locked"),
                  match_not_found: ET("el_match_404") }[e.message] || e.message;
    showToast(ET("el_error") + msg);
  }
}
