// ============================================================
//  worldcup.js — Jahon Chempionati (World Cup) rejimi
//  2-BOSQICH: frontend karkasi (statik, backendsiz).
//
//  Ligalardan butunlay alohida ekran. Mavjud liga kodiga TEGMAYDI.
//  Tab 2 (rejim tanlash) -> showWorldCup() shu yerda.
//
//  Bog'liqliklar (app.js'dan global): APP, escHtml (api.js),
//  showToast, navigateTo, ICON, renderRules, hideModeSelect, showModeSelect.
// ============================================================

// ---- WORLD CUP holati (liga APP'idan alohida, izolatsiya) ----
const WC = {
  selectedGroup: "A",   // Home'da tanlangan guruh (ro'yxatdan o'tish uchun)
  selectedTeam:  null,  // Tanlangan terma jamoa nomi
  ratingGroup:   "A",   // Reyting bo'limida ko'rilayotgan guruh
  ratingMode:    "groups", // Reyting rejimi: groups | top_scorers
  section:       "home", // Joriy WC bo'limi: home | rating | profile | prizes | viewplayer
  profile:       null,  // /wc/profile javobi (ro'yxatdan o'tgan bo'lsa)
  takenTeams:    [],     // Joriy guruhda band qilingan jamoalar
  myMatches:     [],     // WC o'yinlarim (worldcup_matches.js)
  activeMatchId: null,   // Natija/tasdiqlash modali uchun
  viewedProfile: null,   // Reytingdan bosilgan boshqa o'yinchi profili (faqat ko'rish)
  chatOpened:    null,    // Set: chat ochilgan WC matchlar (Natija tugmasi ochiladi)
};

// ---- 48 terma jamoa, 12 guruh (rasmga muvofiq) ----
// Har guruhda 4 jamoa. emoji = bayroq (qo'shimcha rasm kerak emas).
const WC_GROUPS = {
  A: [["Mexico", "🇲🇽"], ["South Africa", "🇿🇦"], ["South Korea", "🇰🇷"], ["Czech Republic", "🇨🇿"]],
  B: [["Canada", "🇨🇦"], ["Bosnia", "🇧🇦"], ["Qatar", "🇶🇦"], ["Switzerland", "🇨🇭"]],
  C: [["Brazil", "🇧🇷"], ["Morocco", "🇲🇦"], ["Haiti", "🇭🇹"], ["Scotland", "🏴󠁧󠁢󠁳󠁣󠁴󠁿"]],
  D: [["USA", "🇺🇸"], ["Paraguay", "🇵🇾"], ["Australia", "🇦🇺"], ["Turkey", "🇹🇷"]],
  E: [["Germany", "🇩🇪"], ["Curacao", "🇨🇼"], ["Ivory Coast", "🇨🇮"], ["Ecuador", "🇪🇨"]],
  F: [["Netherlands", "🇳🇱"], ["Japan", "🇯🇵"], ["Sweden", "🇸🇪"], ["Tunisia", "🇹🇳"]],
  G: [["Belgium", "🇧🇪"], ["Egypt", "🇪🇬"], ["Iran", "🇮🇷"], ["New Zealand", "🇳🇿"]],
  H: [["Spain", "🇪🇸"], ["Cape Verde", "🇨🇻"], ["Saudi Arabia", "🇸🇦"], ["Uruguay", "🇺🇾"]],
  I: [["France", "🇫🇷"], ["Senegal", "🇸🇳"], ["Iraq", "🇮🇶"], ["Norway", "🇳🇴"]],
  J: [["Argentina", "🇦🇷"], ["Algeria", "🇩🇿"], ["Austria", "🇦🇹"], ["Jordan", "🇯🇴"]],
  K: [["Portugal", "🇵🇹"], ["DR Congo", "🇨🇩"], ["Uzbekistan", "🇺🇿"], ["Colombia", "🇨🇴"]],
  L: [["England", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"], ["Croatia", "🇭🇷"], ["Ghana", "🇬🇭"], ["Panama", "🇵🇦"]],
};

// Guruh tablari joylashuvi: A B C / D E F / G H I / J K L (4 qator)
const WC_GROUP_ROWS = [
  ["A", "B", "C"],
  ["D", "E", "F"],
  ["G", "H", "I"],
  ["J", "K", "L"],
];

// Jamoa nomidan bayroq emojini topadi (topilmasa bo'sh)
function wcTeamFlag(teamName) {
  for (const teams of Object.values(WC_GROUPS)) {
    const found = teams.find(([n]) => n === teamName);
    if (found) return found[1];
  }
  return "";
}

// ============================================================
//  KIRISH NUQTASI — Tab 2 (rejim tanlash) shu funksiyani chaqiradi
// ============================================================
function showWorldCup() {
  if (typeof hideModeSelect === "function") hideModeSelect();
  // Liga navigatsiyasi va bo'limlarini yashiramiz (alohida ekran)
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));

  let root = document.getElementById("worldcup-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "worldcup-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  WC.section = "home";
  // WC profilini (ro'yxatdan o'tganmi) yuklab, keyin chizamiz
  void wcLoadProfileThenRender();
}

// WC profilini yuklaydi (ro'yxat holati), so'ng ekranni chizadi
async function wcLoadProfileThenRender() {
  try {
    WC.profile = await apiFetch("/wc/profile");
    // Ro'yxatdan o'tgan bo'lsa — uning guruhini ko'rsatamiz
    if (WC.profile && WC.profile.registered) {
      WC.selectedGroup = WC.profile.group_letter || WC.selectedGroup;
      WC.ratingGroup = WC.profile.group_letter || WC.ratingGroup;
    }
  } catch (_) {
    WC.profile = null;
  }
  // Tanlangan guruhdagi band jamoalarni ham yuklab, keyin chizamiz
  try {
    const data = await apiFetch(`/wc/groups/${WC.selectedGroup}/teams`);
    WC.takenTeams = data.taken_teams || [];
  } catch (_) {
    WC.takenTeams = [];
  }
  renderWorldCup();
}

// World Cup ekranini butunlay yopib, rejim tanlashga qaytaradi
function exitWorldCup() {
  const root = document.getElementById("worldcup-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

// WC ichki navigatsiyasi
function wcNavigate(section) {
  WC.section = section;
  renderWorldCup();
}

// ============================================================
//  RENDER — butun World Cup ekrani (header + bo'lim + nav)
// ============================================================
function renderWorldCup() {
  const t = APP.t;
  const root = document.getElementById("worldcup-root");
  if (!root) return;

  let body = "";
  if (WC.section === "home")        body = wcRenderHome();
  else if (WC.section === "rating") body = wcRenderRating();
  else if (WC.section === "profile") body = wcRenderProfile();
  else if (WC.section === "viewplayer") body = wcRenderViewProfile();
  else                              body = wcRenderPlaceholder();

  root.innerHTML = `
    <div class="wc-banner">
      <img src="worldcup-banner.jpg?v=20260628v" alt="World Cup 2026" class="wc-banner-img" />
    </div>
    <div class="wc-header">
      <button class="wc-back" id="wc-back-btn">
        <span class="back-btn-arrow" data-icon="back"></span>
        <span>${escHtml(t.mode_leagues || "Ligalar")}</span>
      </button>
      <div class="wc-header-title">${escHtml(t.mode_worldcup || "Jahon Chempionati")}</div>
      <span class="wc-lang" id="wc-lang">${(APP.lang || "uz").toUpperCase()}</span>
    </div>
    <div class="wc-body">${body}</div>
    <nav class="wc-nav">
      <button class="wc-nav-item ${WC.section === "home" ? "active" : ""}" data-wc="home">
        <span class="nav-icon" data-icon="home"></span>
        <span class="nav-label">${escHtml(t.nav_home || "Asosiy")}</span>
      </button>
      <button class="wc-nav-item ${WC.section === "rating" ? "active" : ""}" data-wc="rating">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">${escHtml(t.nav_rating || "Reyting")}</span>
      </button>
      <button class="wc-nav-item ${WC.section === "profile" ? "active" : ""}" data-wc="profile">
        <span class="nav-icon" data-icon="user"></span>
        <span class="nav-label">${escHtml(t.nav_profile || "Profil")}</span>
      </button>
      <button class="wc-nav-item ${WC.section === "prizes" ? "active" : ""}" data-wc="prizes">
        <span class="nav-icon" data-icon="gift"></span>
        <span class="nav-label">${escHtml(t.nav_prizes || "Sovrinlar")}</span>
      </button>
    </nav>
  `;

  // Ikonlarni joylashtirish (mavjud applyIcons)
  if (typeof applyIcons === "function") applyIcons(root);

  // Hodisalarni bog'lash
  document.getElementById("wc-back-btn")?.addEventListener("click", exitWorldCup);
  document.getElementById("wc-lang")?.addEventListener("click", () => {
    if (typeof cycleLanguage === "function") cycleLanguage();
  });
  root.querySelectorAll(".wc-nav-item").forEach(btn => {
    btn.addEventListener("click", () => wcNavigate(btn.dataset.wc));
  });

  // Bo'limga xos hodisalar
  if (WC.section === "home")        wcBindHome();
  else if (WC.section === "rating") wcBindRating();
  else if (WC.section === "profile") wcBindProfile();
  else if (WC.section === "viewplayer") wcBindViewProfile();
}

// ============================================================
//  HOME — guruh tanlash + bayroq tanlash + qoidalar (liga tartibi)
// ============================================================
function wcRenderHome() {
  const t = APP.t;
  const teams = WC_GROUPS[WC.selectedGroup] || [];
  const alreadyRegistered = !!(WC.profile && WC.profile.registered);
  const teamSelected = !!WC.selectedTeam;

  // Hero karta — tanlangan guruh bo'yicha (4 jamoa max, liga bilan izchil)
  const heroBadge = t.wc_open || "OCHIQ — RO'YXAT DAVOM ETMOQDA";
  const groupLabel = (t.wc_group || "{g} guruh").replace("{g}", WC.selectedGroup);

  const flagItems = teams.map(([name, flag]) => {
    const isSel = WC.selectedTeam === name;
    const isTaken = WC.takenTeams.includes(name);
    const myTeam = alreadyRegistered && WC.profile.team_name === name;
    const disabled = alreadyRegistered || isTaken;
    return `
      <div class="wc-flag-item ${isSel ? "selected" : ""} ${disabled ? "disabled" : ""} ${myTeam ? "mine" : ""}" data-team="${escHtml(name)}">
        <span class="wc-flag">${flag}</span>
        <span class="wc-flag-name">${escHtml(name)}</span>
      </div>`;
  }).join("");

  // Guruh tablari (4 qatorli A B C / D E F / ...)
  const groupTabs = WC_GROUP_ROWS.map(row => `
    <div class="wc-group-row">
      ${row.map(g => `
        <button class="wc-group-tab ${WC.selectedGroup === g ? "active" : ""}" data-group="${g}">${g}</button>
      `).join("")}
    </div>`).join("");

  // Register tugmasi: ro'yxatdan o'tgan bo'lsa — matn o'zgaradi, disabled
  const canRegister = !alreadyRegistered && teamSelected;
  const regLabel = alreadyRegistered
    ? (t.wc_registered_label || "Ro'yxatdan o'tgansiz")
    : (t.register || "Ro'yxatdan o'tish");

  return `
    <div class="card card--hero">
      <div class="card-eyebrow" style="color:var(--cyan)">${escHtml(heroBadge)}</div>
      <h2 class="card-title">${escHtml(groupLabel)}</h2>
      <div class="card-stats">
        <div class="stat">
          <span class="stat-value">${teams.length}</span>
          <span class="stat-label">${escHtml(t.wc_teams || "Jamoalar")}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat">
          <span class="stat-value">4</span>
          <span class="stat-label">${escHtml(t.max_players || "Maksimal")}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat">
          <span class="stat-value">1</span>
          <span class="stat-label">${escHtml(t.season || "Mavsum")}</span>
        </div>
      </div>
      <button id="wc-btn-register" class="btn btn--primary btn--glow" ${canRegister ? "" : "disabled"} style="opacity:${canRegister ? "1" : "0.45"}">
        ${escHtml(regLabel)}
      </button>
    </div>

    <div class="section-label">${escHtml(t.wc_choose_group || "GURUH TANLASH")}</div>
    <div class="wc-group-tabs">${groupTabs}</div>

    <div class="section-label">${escHtml(t.wc_teams_in_group || "GURUHDAGI JAMOALAR")}</div>
    <div class="wc-flags-list">${flagItems}</div>

    <div class="card card--flat">
      <div class="card-header">
        <span class="card-header-icon" data-icon="clipboard"></span>
        <span class="card-header-text">${escHtml(t.rules || "Qoidalar")}</span>
      </div>
      <ul class="rules-list" id="wc-rules-list"></ul>
    </div>
  `;
}

function wcBindHome() {
  const root = document.getElementById("worldcup-root");

  // Qoidalar — liga bilan bir xil (t.rules_list qayta ishlatiladi)
  const ul = document.getElementById("wc-rules-list");
  if (ul) {
    const rules = APP.t.rules_list || [];
    ul.innerHTML = rules.map(r => `<li>${r}</li>`).join("");
  }

  const alreadyRegistered = !!(WC.profile && WC.profile.registered);

  // Guruh tab tanlash — band jamoalarni yangilab qayta chizamiz
  root.querySelectorAll(".wc-group-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      WC.selectedGroup = btn.dataset.group;
      WC.selectedTeam = null;   // guruh o'zgarsa tanlov tushadi
      void wcLoadTakenThenRender();
    });
  });

  // Bayroq (jamoa) tanlash — faqat ro'yxatdan o'tmagan va band bo'lmagan bo'lsa
  if (!alreadyRegistered) {
    root.querySelectorAll(".wc-flag-item:not(.disabled)").forEach(item => {
      item.addEventListener("click", () => {
        WC.selectedTeam = item.dataset.team;
        renderWorldCup();
      });
    });
  }

  // Ro'yxatdan o'tish — real backend chaqiruvi
  document.getElementById("wc-btn-register")?.addEventListener("click", wcRegister);
}

// Tanlangan guruhdagi band jamoalarni yuklab, keyin home'ni chizadi
async function wcLoadTakenThenRender() {
  try {
    const data = await apiFetch(`/wc/groups/${WC.selectedGroup}/teams`);
    WC.takenTeams = data.taken_teams || [];
  } catch (_) {
    WC.takenTeams = [];
  }
  renderWorldCup();
}

// World Cup'ga ro'yxatdan o'tish (backend /wc/register)
async function wcRegister() {
  const t = APP.t;
  if (WC.profile && WC.profile.registered) {
    showToast(t.wc_already_in || "Siz World Cup'da allaqachon ro'yxatdansiz");
    return;
  }
  if (!WC.selectedTeam) {
    showToast(t.wc_select_team || "Avval jamoa tanlang");
    return;
  }
  const btn = document.getElementById("wc-btn-register");
  if (btn) btn.disabled = true;
  try {
    await apiFetch(
      `/wc/register?group_letter=${encodeURIComponent(WC.selectedGroup)}&team_name=${encodeURIComponent(WC.selectedTeam)}`,
      { method: "POST" }
    );
    showToast(t.wc_registered_ok || "✅ World Cup'ga ro'yxatdan o'tdingiz!");
    WC.selectedTeam = null;
    // To'liq profilni (user_id, rating bilan) qayta yuklab chizamiz
    try {
      WC.profile = await apiFetch("/wc/profile");
    } catch (_) {
      WC.profile = { registered: true, group_letter: WC.selectedGroup, team_name: WC.selectedTeam };
    }
    renderWorldCup();
  } catch (e) {
    const msg = {
      wc_already_registered: t.wc_already_in || "Siz World Cup'da allaqachon ro'yxatdansiz",
      wc_group_full:         t.wc_group_full_err || "Bu guruh to'lgan",
      wc_team_taken:         t.wc_team_taken || "Bu jamoa allaqachon band qilingan",
      wc_invalid_group:      t.wc_invalid || "Noto'g'ri guruh",
      wc_invalid_team:       t.wc_invalid || "Noto'g'ri jamoa",
    }[e.message] || e.message;
    showToast("❌ " + msg);
    if (btn) btn.disabled = false;
    // Jamoa band bo'lib chiqsa — ro'yxatni yangilaymiz
    if (e.message === "wc_team_taken" || e.message === "wc_group_full") {
      WC.selectedTeam = null;
      void wcLoadTakenThenRender();
    }
  }
}

// ============================================================
//  RATING — guruh tablari + 4 jamoali jadval (statik)
// ============================================================
function wcRenderRating() {
  const t = APP.t;

  // Rejim tugmalari: Guruhlar / To'p urarlar
  const modeTabs = `
    <div class="wc-mode-tabs">
      <button class="wc-mode-tab ${WC.ratingMode === "groups" ? "active" : ""}" data-rmode="groups">${escHtml(t.wc_mode_groups || "Guruhlar")}</button>
      <button class="wc-mode-tab ${WC.ratingMode === "top_scorers" ? "active" : ""}" data-rmode="top_scorers">${escHtml(t.tab_top_scorers || "⚽ To'p urarlar")}</button>
    </div>`;

  // To'p urarlar rejimi
  if (WC.ratingMode === "top_scorers") {
    return `
      <div class="section-label">${escHtml(t.rating_title || "REYTING JADVALI")}</div>
      ${modeTabs}
      <div class="card card--flat card--table">
        <table class="rating-table" id="wc-scorers-table">
          <thead>
            <tr>
              <th>#</th>
              <th>${escHtml(t.th_player || "O'yinchi")}</th>
              <th>${escHtml(t.th_group || "Guruh")}</th>
              <th>${escHtml(t.th_goals_col || "Gol")}</th>
            </tr>
          </thead>
          <tbody id="wc-scorers-tbody">
            <tr><td colspan="4" class="wc-loading-row">${escHtml(t.loading || "Yuklanmoqda...")}</td></tr>
          </tbody>
        </table>
      </div>
    `;
  }

  // Guruhlar rejimi (standart)
  // Guruh tablari (4 qatorli, home bilan bir xil joylashuv)
  const groupTabs = WC_GROUP_ROWS.map(row => `
    <div class="wc-group-row">
      ${row.map(g => `
        <button class="wc-group-tab ${WC.ratingGroup === g ? "active" : ""}" data-rgroup="${g}">${g}</button>
      `).join("")}
    </div>`).join("");

  const teams = WC_GROUPS[WC.ratingGroup] || [];
  // Dastlab jamoalarni 0 bilan ko'rsatamiz; real statistika wcLoadRating bilan keladi
  const rows = teams.map(([name, flag], idx) => `
    <tr>
      <td>${idx + 1}</td>
      <td>
        <div class="wc-row-cell">
          <span class="wc-row-flag">${flag}</span>
          <div class="wc-row-text">
            <span class="wc-row-name">${escHtml(name)}</span>
          </div>
        </div>
      </td>
      <td>0</td><td>0</td><td>0</td><td>0</td>
      <td>0</td><td>0</td><td>0</td>
    </tr>`).join("");

  return `
    <div class="section-label">${escHtml(t.rating_title || "REYTING JADVALI")}</div>
    ${modeTabs}
    <div class="wc-group-tabs">${groupTabs}</div>
    <div class="card card--flat card--table">
      <table class="rating-table" id="wc-rating-table">
        <thead>
          <tr>
            <th>#</th>
            <th>${escHtml(t.th_player || "O'yinchi")}</th>
            <th>${escHtml(t.th_pts || "B")}</th>
            <th>${escHtml(t.th_w || "G")}</th>
            <th>${escHtml(t.th_d || "D")}</th>
            <th>${escHtml(t.th_l || "M")}</th>
            <th>${escHtml(t.th_gf || "GF")}</th>
            <th>${escHtml(t.th_ga || "GA")}</th>
            <th>${escHtml(t.th_gd || "GD")}</th>
          </tr>
        </thead>
        <tbody id="wc-rating-tbody">${rows}</tbody>
      </table>
    </div>
  `;
}

function wcBindRating() {
  const root = document.getElementById("worldcup-root");

  // Rejim tugmalari (Guruhlar / To'p urarlar)
  root.querySelectorAll(".wc-mode-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      WC.ratingMode = btn.dataset.rmode;
      renderWorldCup();
    });
  });

  if (WC.ratingMode === "top_scorers") {
    void wcLoadTopScorers();
    return;
  }

  root.querySelectorAll(".wc-group-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      WC.ratingGroup = btn.dataset.rgroup;
      renderWorldCup();
    });
  });
  // Real reytingni yuklaymiz (band jamoalar statistikasi bilan)
  void wcLoadRating();
}

// Barcha guruhlardan eng ko'p gol urganlar (to'p urarlar)
async function wcLoadTopScorers() {
  const tbody = document.getElementById("wc-scorers-tbody");
  if (!tbody) return;
  const t = APP.t;
  try {
    const data = await apiFetch("/wc/top-scorers");
    const scorers = data.scorers || [];
    if (scorers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="empty-state">${escHtml(t.no_data || "Ma'lumot yo'q")}</td></tr>`;
      return;
    }
    tbody.innerHTML = scorers.map((p, i) => {
      const flag = wcTeamFlag(p.team_name);
      const userLine = p.username
        ? `<span class="wc-row-user">@${escHtml(p.username)}</span>`
        : (p.nickname ? `<span class="wc-row-user">${escHtml(p.nickname)}</span>` : "");
      const rankCls = (i + 1) <= 3 ? `rank-${i + 1}` : "";
      return `
        <tr>
          <td class="${rankCls}">${i + 1}</td>
          <td>
            <div class="wc-row-cell">
              <span class="wc-row-flag">${flag}</span>
              <div class="wc-row-text">
                <span class="wc-row-name">${escHtml(p.team_name || "")}</span>
                ${userLine}
              </div>
            </div>
          </td>
          <td>${escHtml(p.group_letter || "")}</td>
          <td><strong>${p.goals_for}</strong></td>
        </tr>`;
    }).join("");
  } catch (_) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">${escHtml(t.no_data || "Ma'lumot yo'q")}</td></tr>`;
  }
}

// Guruh reytingini backenddan olib, jadvalni to'ldiradi
async function wcLoadRating() {
  const tbody = document.getElementById("wc-rating-tbody");
  if (!tbody) return;
  try {
    const data = await apiFetch(`/wc/rating/${WC.ratingGroup}`);
    const rating = data.rating || [];
    if (rating.length === 0) return;  // bo'sh — dastlabki 0-jadval qoladi
    tbody.innerHTML = rating.map((p, idx) => {
      const flag = wcTeamFlag(p.team_name);
      const gd = p.goal_difference > 0 ? `+${p.goal_difference}` : `${p.goal_difference}`;
      const userLine = p.username
        ? `<span class="wc-row-user">@${escHtml(p.username)}</span>`
        : (p.nickname ? `<span class="wc-row-user">${escHtml(p.nickname)}</span>` : "");
      return `
        <tr class="rating-row" data-user-id="${p.user_id}">
          <td>${idx + 1}</td>
          <td>
            <div class="wc-row-cell">
              <span class="wc-row-flag">${flag}</span>
              <div class="wc-row-text">
                <span class="wc-row-name">${escHtml(p.team_name || "")}</span>
                ${userLine}
              </div>
            </div>
          </td>
          <td>${p.points}</td>
          <td>${p.wins}</td>
          <td>${p.draws}</td>
          <td>${p.losses}</td>
          <td>${p.goals_for}</td>
          <td>${p.goals_against}</td>
          <td>${gd}</td>
        </tr>`;
    }).join("");

    // Qatorga bosilganda — o'sha o'yinchining WC profili (faqat ro'yxatdan o'tganlar)
    tbody.querySelectorAll(".rating-row").forEach(row => {
      row.addEventListener("click", () => {
        const uid = parseInt(row.dataset.userId);
        if (uid) wcOpenPlayerProfile(uid);
      });
    });
  } catch (_) { /* xato — dastlabki jadval qoladi */ }
}

// Reytingdan bosilgan boshqa o'yinchining WC profilini ochadi (faqat ko'rish)
async function wcOpenPlayerProfile(userId) {
  const t = APP.t;
  try {
    const data = await apiFetch(`/wc/players/${userId}/profile`);
    WC.viewedProfile = data;
    WC.section = "viewplayer";
    renderWorldCup();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

// Boshqa o'yinchi profilidan reyting bo'limiga qaytadi
function wcBackToRating() {
  WC.viewedProfile = null;
  WC.section = "rating";
  renderWorldCup();
}

// Profil / Sovrinlar — keyingi bosqichda
function wcRenderPlaceholder() {
  const t = APP.t;
  return `
    <div class="wc-placeholder">
      <span class="wc-placeholder-icon" data-icon="lock"></span>
      <div class="wc-placeholder-text">${escHtml(t.worldcup_soon || "Jahon Chempionati tez orada ishga tushadi!")}</div>
    </div>
  `;
}
