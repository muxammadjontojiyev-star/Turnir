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
  ratingGroup: 1,      // Reytingda tanlangan guruh (1..8)
  homeGroup: 1,        // Asosiy sahifada tanlangan guruh (1..8)
  rating: [],
  myMatches: [],
  meParticipant: false,
  profile: null,       // /cl/profile javobi
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
  if (!logo) return `<span class="cl-club-fallback" style="width:${size}px;height:${size}px">⚽</span>`;
  return `<img class="cl-club-logo" src="${escHtml(logo)}" alt="${escHtml(clubName)}" `
       + `title="${escHtml(clubName)}" style="width:${size}px;height:${size}px" `
       + `onerror="this.outerHTML='<span class=\'cl-club-fallback\' style=\'width:${size}px;height:${size}px\'>⚽</span>'" />`;
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
}

function exitChampionsLeague() {
  const root = document.getElementById("cl-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function clNavigate(section) {
  CL.section = section;
  renderChampionsLeague();
  if (section === "rating") void clLoadRating();
  if (section === "profile") void clLoadProfile();
  if (section === "prizes") void clLoadProfileForPrizes();
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
  try {
    CL.groups = await apiFetch("/cl/groups");
    CL.meParticipant = !!CL.groups.me_participant;
  } catch (_) { CL.groups = null; }
  try {
    CL.qualifiers = await apiFetch("/cl/qualifiers");
  } catch (_) { CL.qualifiers = null; }
  renderChampionsLeague();
}

async function clLoadRating() {
  try {
    const d = await apiFetch(`/cl/rating/${CL.ratingGroup}`);
    CL.rating = d.rating || [];
  } catch (_) { CL.rating = []; }
  renderChampionsLeague();
}

async function clLoadMatches() {
  try {
    const d = await apiFetch("/cl/matches/my");
    CL.myMatches = d.matches || [];
    CL._myId = d.me_id ?? null;
  } catch (_) { CL.myMatches = []; CL._myId = null; }
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
  else body = clRenderProfile();

  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="cl-back-btn">←</button>
      <div class="wc-header-title">Chempionlar ligasi</div>
    </div>
    <div class="wc-body" style="padding-bottom:90px;">${body}</div>
    <nav class="wc-nav">
      <button class="wc-nav-item ${CL.section === "home" ? "active" : ""}" data-cl-tab="home">
        <span class="nav-icon" data-icon="home"></span>
        <span class="nav-label">Asosiy</span>
      </button>
      <button class="wc-nav-item ${CL.section === "rating" ? "active" : ""}" data-cl-tab="rating">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">Reyting</span>
      </button>
      <button class="wc-nav-item ${CL.section === "profile" ? "active" : ""}" data-cl-tab="profile">
        <span class="nav-icon" data-icon="user"></span>
        <span class="nav-label">Profil</span>
      </button>
      <button class="wc-nav-item ${CL.section === "prizes" ? "active" : ""}" data-cl-tab="prizes">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">Sovrinlar</span>
      </button>
    </nav>
  `;

  if (typeof applyIcons === "function") applyIcons(root);
  document.getElementById("cl-back-btn").addEventListener("click", exitChampionsLeague);
  root.querySelectorAll("[data-cl-tab]").forEach(b =>
    b.addEventListener("click", () => clNavigate(b.dataset.clTab)));
  clBindSectionEvents(root);
  if (CL.section === "profile") clBindProfile(root);
  if (CL.section === "prizes") void clBindPrizes();
}


// ---- HOME ----  → cl_home.js (qoida 21: fayl 300 qatordan oshmasin)

// ---- RATING ----
function clRenderRating() {
  let selector = `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;">`;
  for (let n = 1; n <= CL_GROUP_COUNT; n++) {
    const active = CL.ratingGroup === n ? " active" : "";
    selector += `<button class="tab-btn${active}" data-cl-group="${n}">G${n}</button>`;
  }
  selector += `</div>`;

  const rows = (CL.rating || []).map((p, i) => `
    <tr>
      <td class="rank-${i + 1}">${i + 1}</td>
      <td><div class="cl-rating-player">${clClubBadge(p.club_name, 22)}<span>${escHtml(p.nickname || "")}</span></div></td>
      <td>${p.played}</td><td>${p.goal_difference > 0 ? "+" : ""}${p.goal_difference}</td>
      <td><b>${p.points}</b></td>
    </tr>`).join("");

  return `${selector}
    <div class="card card--table">
      <table class="rating-table">
        <thead><tr><th>#</th><th>O'yinchi</th><th>O</th><th>GF</th><th>Ochko</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5">Hozircha natijalar yo'q</td></tr>`}</tbody>
      </table>
    </div>`;
}

// ---- MATCHES ----
function clRenderMatches() {
  if (!CL.meParticipant) {
    return `<div class="card">Siz Chempionlar ligasi ishtirokchisi emassiz.</div>`;
  }
  const ms = CL.myMatches || [];
  if (!ms.length) {
    return `<div class="wc-loading-row">Hozircha o'yinlar yo'q (qur'a kutilmoqda).</div>`;
  }
  return `<div class="matches-list">${ms.map(clRenderMatchItem).join("")}</div>`;
}

// Bitta o'yin kartasi (worldcup_matches.js — wcRenderMatchItem naqshi, qoida 10)
function clRenderMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const center = `
    <span class="cl-mc-logo">${clClubBadge(m.player1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="cl-mc-logo">${clClubBadge(m.player2_club, 26)}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "admin_pending")         { statusCls = "status--awaiting"; statusText = "ADMIN TASDIG'I"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  let action = "";
  if (m.status === "pending") {
    action = `<button class="match-action-btn" data-cl-open="${m.id}">Natija</button>`;
  } else if (m.status === "awaiting_confirmation") {
    action = (m.submitted_by && !clIsMe(m.submitted_by))
      ? `<button class="match-action-btn" data-cl-confirm="${m.id}">✔</button>`
      : `<span class="match-waiting">Kutilmoqda</span>`;
  }

  // Natija kiritish qatori — faqat "Natija" bosilganda ochiladi (hidden)
  const inputs = (m.status === "pending") ? `
    <div class="cl-score-row hidden" id="cl-score-${m.id}">
      <input class="score-input" id="cl-s1-${m.id}" type="number" min="0" max="99" value="0">
      <span class="score-separator">:</span>
      <input class="score-input" id="cl-s2-${m.id}" type="number" min="0" max="99" value="0">
      <button class="btn btn--primary" data-cl-submit="${m.id}">Kiritish</button>
    </div>` : "";

  const reject = (m.status === "awaiting_confirmation" && m.submitted_by && !clIsMe(m.submitted_by))
    ? `<div class="cl-score-row"><button class="btn" data-cl-reject="${m.id}">❌ Rad etish</button></div>` : "";

  // Uy/mehmon: player1 — uy egasi (cl_matches yozilish tartibi)
  const venue = clIsMe(m.player1_id)
    ? `<span class="cl-venue cl-venue--home">UY</span>`
    : `<span class="cl-venue cl-venue--away">MEHMON</span>`;

  return `
    <div class="cl-match-wrap">
      <div class="match-item">
        <span class="match-names">#${m.matchday}-tur ${venue}</span>
        <div class="match-center match-center--clickable" data-cl-open-match="${m.id}">${center}</div>
        <span class="match-status ${statusCls}">${statusText}</span>
        ${action}
      </div>
      ${inputs}${reject}
    </div>`;
}

function clIsMe(userId) {
  // me_id backend'dan keladi (/cl/matches/my) — taxmin qilinmaydi
  return CL._myId !== null && CL._myId !== undefined && userId === CL._myId;
}

function clStatusLabel(s) {
  return ({ pending: "Kutilmoqda", awaiting_confirmation: "Tasdiq kutilmoqda",
            confirmed: "Tasdiqlangan", admin_pending: "Admin tasdig'i" })[s] || s;
}

// ---- Eventlar ----
function clBindSectionEvents(root) {
  root.querySelectorAll("[data-cl-home-group]").forEach(b =>
    b.addEventListener("click", () => {
      CL.homeGroup = Number(b.dataset.clHomeGroup);
      renderChampionsLeague();
    }));

  // Logolar juftligiga bosilsa — raqib VS-oynasi (cl_chat.js: 2 xil chat)
  root.querySelectorAll("[data-cl-open-match]").forEach(el =>
    el.addEventListener("click", () => clOpenOpponentModal(Number(el.dataset.clOpenMatch))));

  root.querySelectorAll("[data-cl-open]").forEach(b =>
    b.addEventListener("click", () => {
      const row = document.getElementById(`cl-score-${b.dataset.clOpen}`);
      if (row) { row.classList.toggle("hidden"); }
    }));

  root.querySelectorAll("[data-cl-group]").forEach(b =>
    b.addEventListener("click", () => {
      CL.ratingGroup = Number(b.dataset.clGroup);
      void clLoadRating();
    }));

  root.querySelectorAll("[data-cl-submit]").forEach(b =>
    b.addEventListener("click", async () => {
      const id = b.dataset.clSubmit;
      const s1 = Number(document.getElementById(`cl-s1-${id}`).value || 0);
      const s2 = Number(document.getElementById(`cl-s2-${id}`).value || 0);
      b.disabled = true; // ikki marta bosishdan himoya (qoida #38/#40)
      try {
        await apiFetch(`/cl/match/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`, { method: "POST" });
        showToast("Natija kiritildi ✅");
        CL._myId = undefined;
        await clLoadMatches();
      } catch (e) {
        b.disabled = false;
        showToast("Xato: " + e.message);
      }
    }));

  const act = async (id, accept) => {
    try {
      await apiFetch(`/cl/match/confirm?match_id=${id}&accept=${accept}`, { method: "POST" });
      showToast(accept ? "Tasdiqlandi ✅" : "Rad etildi");
      CL._myId = undefined;
      await clLoadMatches();
    } catch (e) {
      showToast("Xato: " + e.message);
    }
  };
  root.querySelectorAll("[data-cl-confirm]").forEach(b =>
    b.addEventListener("click", () => act(b.dataset.clConfirm, true)));
  root.querySelectorAll("[data-cl-reject]").forEach(b =>
    b.addEventListener("click", () => act(b.dataset.clReject, false)));
}
