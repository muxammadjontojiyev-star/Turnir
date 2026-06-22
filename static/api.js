/**
 * api.js — eFootball Turnir WebApp
 * Barcha API chaqiruvlari va section ma'lumotlarini yuklash.
 * app.js bilan birga ishlaydi (APP global ob'ekti orqali).
 */

// ============================================================
//  API HELPER
// ============================================================

const API_BASE = "";  // Xuddi shu serverda ishlaydi (uvicorn)

// ============================================================
//  LIGA KLUBLAR MA'LUMOTLARI (statik, alifbo tartibida)
// ============================================================

const LEAGUE_CLUBS = {
  "LaLiga": [
    { name: "Almería",         logo: "https://media.api-sports.io/football/teams/723.png" },
    { name: "Athletic Club",   logo: "https://media.api-sports.io/football/teams/531.png" },
    { name: "Atlético Madrid", logo: "https://media.api-sports.io/football/teams/530.png" },
    { name: "Barcelona",       logo: "https://media.api-sports.io/football/teams/529.png" },
    { name: "Betis",           logo: "https://media.api-sports.io/football/teams/543.png" },
    { name: "Cádiz",           logo: "https://media.api-sports.io/football/teams/724.png" },
    { name: "Celta Vigo",      logo: "https://media.api-sports.io/football/teams/538.png" },
    { name: "Getafe",          logo: "https://media.api-sports.io/football/teams/546.png" },
    { name: "Girona",          logo: "https://media.api-sports.io/football/teams/547.png" },
    { name: "Granada",         logo: "https://media.api-sports.io/football/teams/715.png" },
    { name: "Las Palmas",      logo: "https://media.api-sports.io/football/teams/534.png" },
    { name: "Mallorca",        logo: "https://media.api-sports.io/football/teams/798.png" },
    { name: "Osasuna",         logo: "https://media.api-sports.io/football/teams/727.png" },
    { name: "Rayo Vallecano",  logo: "https://media.api-sports.io/football/teams/728.png" },
    { name: "Real Madrid",     logo: "https://media.api-sports.io/football/teams/541.png" },
    { name: "Real Sociedad",   logo: "https://media.api-sports.io/football/teams/548.png" },
    { name: "Sevilla",         logo: "https://media.api-sports.io/football/teams/536.png" },
    { name: "Valencia",        logo: "https://media.api-sports.io/football/teams/532.png" },
    { name: "Valladolid",      logo: "https://media.api-sports.io/football/teams/720.png" },
    { name: "Villarreal",      logo: "https://media.api-sports.io/football/teams/533.png" },
  ],
  "Premier Liga": [
    { name: "Arsenal",         logo: "https://media.api-sports.io/football/teams/42.png" },
    { name: "Aston Villa",     logo: "https://media.api-sports.io/football/teams/66.png" },
    { name: "Bournemouth",     logo: "https://media.api-sports.io/football/teams/35.png" },
    { name: "Brentford",       logo: "https://media.api-sports.io/football/teams/55.png" },
    { name: "Brighton",        logo: "https://media.api-sports.io/football/teams/51.png" },
    { name: "Burnley",         logo: "https://media.api-sports.io/football/teams/44.png" },
    { name: "Chelsea",         logo: "https://media.api-sports.io/football/teams/49.png" },
    { name: "Crystal Palace",  logo: "https://media.api-sports.io/football/teams/52.png" },
    { name: "Everton",         logo: "https://media.api-sports.io/football/teams/45.png" },
    { name: "Fulham",          logo: "https://media.api-sports.io/football/teams/36.png" },
    { name: "Liverpool",       logo: "https://media.api-sports.io/football/teams/40.png" },
    { name: "Luton Town",      logo: "https://media.api-sports.io/football/teams/1359.png" },
    { name: "Man City",        logo: "https://media.api-sports.io/football/teams/50.png" },
    { name: "Man United",      logo: "https://media.api-sports.io/football/teams/33.png" },
    { name: "Newcastle",       logo: "https://media.api-sports.io/football/teams/34.png" },
    { name: "Nottm Forest",    logo: "https://media.api-sports.io/football/teams/65.png" },
    { name: "Sheffield Utd",   logo: "https://media.api-sports.io/football/teams/62.png" },
    { name: "Tottenham",       logo: "https://media.api-sports.io/football/teams/47.png" },
    { name: "West Ham",        logo: "https://media.api-sports.io/football/teams/48.png" },
    { name: "Wolves",          logo: "https://media.api-sports.io/football/teams/39.png" },
  ],
};

async function apiFetch(path, options = {}) {
  const initData = window.Telegram?.WebApp?.initData || "";
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": initData,
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ============================================================
//  HOME SECTION
// ============================================================

async function loadHome() {
  try {
    const leagues = await apiFetch("/leagues");
    APP.leagues = leagues;

    // Birinchi ochiq ligani tanlash
    const open = leagues.find(l => l.status === "open") || leagues[0];
    if (open) APP.selectedLeagueId = open.id;
    APP.selectedClub = null;

    // Klublar ko'rsatish uchun profileData ni oldindan yuklash
    try {
      const profile = await apiFetch("/profile");
      APP.profileData = profile;
    } catch (_) { /* Foydalanuvchi topilmasa — null qoladi */ }

    renderLeagues(leagues);
    renderHeroCard(open || null);
    renderRules();
    await loadHomeMatches();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

// Home'dagi "Joriy o'yinlarim" — Profildagi natija kiritish mantig'ini qayta ishlatadi.
// O'yini yo'q bo'lsa (qur'a qilinmagan) bo'lim yashiriladi.
async function loadHomeMatches() {
  const section = document.getElementById("home-matches-section");
  const list    = document.getElementById("home-matches-list");
  const t       = APP.t;

  try {
    const data = await apiFetch("/matches/my");
    const matches = data.matches || [];

    if (matches.length === 0) {
      section.classList.add("hidden");
      list.innerHTML = "";
      return;
    }

    section.classList.remove("hidden");
    list.innerHTML = matches.map(m => renderMatchItem(m)).join("");
    bindMatchActions(list);
  } catch (e) {
    // Foydalanuvchi/o'yin topilmasa — bo'lim yashirin qoladi
    section.classList.add("hidden");
    list.innerHTML = "";
  }
}

function renderHeroCard(league) {
  if (!league) return;
  const t = APP.t;
  const badge = document.getElementById("home-status-badge");
  const name  = document.getElementById("home-league-name");
  const count = document.getElementById("home-players");
  const max   = document.getElementById("home-max");

  badge.textContent = league.is_full
    ? (t.league_full || "TO'LIQ")
    : (t.league_open || "OCHIQ — RO'YXAT DAVOM ETMOQDA");
  badge.style.color = league.is_full
    ? "var(--red-neon)"
    : "var(--cyan)";

  name.textContent  = league.name;
  count.textContent = league.current_players;
  max.textContent   = league.max_players;

  document.getElementById("home-matchday").textContent = "—";

  const btn = document.getElementById("btn-register");
  // Liga to'liq bo'lsa yoki klub tanlanmagan bo'lsa — disabled
  const clubSelected = !!APP.selectedClub;
  btn.disabled = league.is_full || !clubSelected;
  btn.style.opacity = (league.is_full || !clubSelected) ? "0.45" : "1";
}

function renderLeagues(leagues) {
  const t = APP.t;
  const list = document.getElementById("leagues-list");
  list.innerHTML = "";

  leagues.forEach(league => {
    const item = document.createElement("div");
    item.className = "league-item" + (league.id === APP.selectedLeagueId ? " selected" : "");
    item.dataset.id = league.id;

    const badgeClass = league.is_full ? "badge--full" : "badge--open";
    const badgeText  = league.is_full
      ? (t.full || "TO'LIQ")
      : (t.open || "OCHIQ");

    item.innerHTML = `
      <div>
        <div class="league-item-name">${league.name}</div>
        <div class="league-item-count">${league.current_players}/${league.max_players} ${t.players || "o'yinchi"}</div>
      </div>
      <span class="league-item-badge ${badgeClass}">${badgeText}</span>
    `;

    item.addEventListener("click", () => {
      APP.selectedLeagueId = league.id;
      APP.selectedClub = null;
      document.querySelectorAll(".league-item").forEach(el => el.classList.remove("selected"));
      item.classList.add("selected");
      renderHeroCard(league);
      // Allaqachon ro'yxatdan o'tgan bo'lsa klublarni ko'rsatmaymiz
      if (!APP.profileData?.league_id) {
        void renderClubsForLeague(league);
      }
    });

    list.appendChild(item);
  });

  // Birinchi tanlangan liga uchun klublarni ko'rsat — faqat ro'yxatdan o'tmagan bo'lsa
  const selected = leagues.find(l => l.id === APP.selectedLeagueId);
  if (selected && !APP.profileData?.league_id) {
    void renderClubsForLeague(selected);
  } else {
    document.getElementById("clubs-section").classList.add("hidden");
  }
}

// Foydalanuvchi bu mavsumda tanlagan klub (local state) — app.js dagi APP.selectedClub
async function renderClubsForLeague(league) {
  const section = document.getElementById("clubs-section");
  const list    = document.getElementById("clubs-list");
  const t       = APP.t;

  // Liga nomi bo'yicha klublar ro'yxatini topamiz
  const clubs = LEAGUE_CLUBS[league.name] || [];
  if (clubs.length === 0) {
    section.classList.add("hidden");
    return;
  }

  section.classList.remove("hidden");
  list.innerHTML = "";

  // Foydalanuvchi allaqachon ro'yxatdan o'tganmi?
  const alreadyRegistered = !!(APP.profileData && APP.profileData.league_id);

  // Boshqa foydalanuvchilar tomonidan band qilingan klublar ro'yxatini olamiz
  let takenClubs = [];
  if (!alreadyRegistered) {
    try {
      const data = await apiFetch(`/leagues/${league.id}/clubs`);
      takenClubs = data.taken_clubs || [];
    } catch (e) {
      takenClubs = [];
    }
  }

  // Alifbo tartibida (allaqachon alifbo tartibida, lekin sort qilamiz xavfsizlik uchun)
  const sorted = [...clubs].sort((a, b) => a.name.localeCompare(b.name));

  sorted.forEach(club => {
    const item = document.createElement("div");
    const isSelected = APP.selectedClub === club.name;
    const isTaken = takenClubs.includes(club.name);
    item.className = "club-item" +
      (isSelected ? " selected" : "") +
      (alreadyRegistered || isTaken ? " disabled" : "");

    item.innerHTML = `
      <img
        class="club-logo"
        src="${escHtml(club.logo)}"
        alt="${escHtml(club.name)}"
        onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"
      />
      <div class="club-logo-fallback" style="display:none">⚽</div>
      <span class="club-name">${escHtml(club.name)}</span>
    `;

    if (!alreadyRegistered && !isTaken) {
      item.addEventListener("click", () => {
        APP.selectedClub     = club.name;
        APP.selectedClubLogo = club.logo;
        // Tanlangan klubni belgilash uchun ro'yxatni qayta chizamiz (yashirmaymiz)
        void renderClubsForLeague(league);
        // Register tugmasini faollashtirish
        const btn = document.getElementById("btn-register");
        btn.disabled = false;
        btn.style.opacity = "1";
      });
    }

    list.appendChild(item);
  });

  // Agar allaqachon ro'yxatdan o'tgan bo'lsa — register tugmasini o'chirib qo'yamiz
  if (alreadyRegistered) {
    const btn = document.getElementById("btn-register");
    btn.disabled = true;
    btn.style.opacity = "0.45";
  }
}

function renderRules() {
  const t = APP.t;
  const rules = t.rules_list || [];
  const ul = document.getElementById("rules-list");
  ul.innerHTML = rules.map(r => `<li>${r}</li>`).join("");
}

// ============================================================
//  RATING SECTION
// ============================================================

async function loadRating() {
  const leagueId = APP.selectedLeagueId;
  if (!leagueId) return;

  // Filter tugmalarini chizish
  renderRatingFilter();

  if (APP.ratingTab === "top_scorers") {
    try { await loadTopScorers(); }
    catch (e) { showToast("❌ " + e.message); }
    return;
  }

  try {
    const data = await apiFetch(`/rating/${leagueId}`);
    renderRatingTable(data.rating);
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

function renderRatingFilter() {
  const filter = document.getElementById("rating-filter");
  filter.innerHTML = "";

  // Liga tablari
  (APP.leagues || []).forEach(league => {
    const btn = document.createElement("button");
    btn.className = "tab-btn" + (APP.ratingTab === "league" && league.id === APP.selectedLeagueId ? " active" : "");
    btn.textContent = league.name;
    btn.addEventListener("click", async () => {
      APP.selectedLeagueId = league.id;
      APP.ratingTab = "league";
      showRatingCard("league");
      document.querySelectorAll("#rating-filter .tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      try {
        const data = await apiFetch(`/rating/${league.id}`);
        renderRatingTable(data.rating);
      } catch (e) {
        showToast("❌ " + e.message);
      }
    });
    filter.appendChild(btn);
  });

  // To'p urarlar tabi (barcha ligalar bo'yicha umumiy, doimiy tab)
  const topScorersBtn = document.createElement("button");
  topScorersBtn.className = "tab-btn" + (APP.ratingTab === "top_scorers" ? " active" : "");
  topScorersBtn.textContent = APP.t.tab_top_scorers || "⚽ To'p urarlar";
  topScorersBtn.addEventListener("click", async () => {
    APP.ratingTab = "top_scorers";
    showRatingCard("top_scorers");
    document.querySelectorAll("#rating-filter .tab-btn").forEach(b => b.classList.remove("active"));
    topScorersBtn.classList.add("active");
    try { await loadTopScorers(); }
    catch (e) { showToast("❌ " + e.message); }
  });
  filter.appendChild(topScorersBtn);

  showRatingCard(APP.ratingTab);
}

function showRatingCard(tab) {
  document.getElementById("rating-card").classList.toggle("hidden", tab !== "league");
  document.getElementById("top-scorers-card").classList.toggle("hidden", tab !== "top_scorers");
}

function renderRatingTable(rating) {
  const tbody = document.getElementById("rating-tbody");
  const myId  = APP.currentUser?.id;

  if (!rating || rating.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">${APP.t.no_data || "Ma'lumot yo'q"}</td></tr>`;
    return;
  }

  tbody.innerHTML = rating.map((player, i) => {
    const rank    = i + 1;
    const rankCls = rank <= 3 ? `rank-${rank}` : "";
    const isMe    = player.user_id === myId;

    // Klub logosini LEAGUE_CLUBS dan topamiz
    let clubLogo = null;
    let clubDisplayName = player.club_name || player.nickname;
    if (player.club_name) {
      for (const clubs of Object.values(LEAGUE_CLUBS)) {
        const found = clubs.find(c => c.name === player.club_name);
        if (found) { clubLogo = found.logo; clubDisplayName = found.name; break; }
      }
    }

    const logoHtml = clubLogo
      ? `<img src="${escHtml(clubLogo)}" alt="" style="width:24px;height:24px;object-fit:contain;border-radius:4px;flex-shrink:0;" onerror="this.style.display='none'" />`
      : "";
    const usernameRow = player.username
      ? `<span class="player-username">@${escHtml(player.username)}</span>`
      : "";

    const playerCell = `
      <div class="player-cell">
        ${logoHtml}
        <div class="player-cell-text">
          <span class="player-clubname">${escHtml(clubDisplayName)}</span>
          ${usernameRow}
        </div>
      </div>`;

    const trCls = ["rating-row", isMe ? "is-me" : ""].filter(Boolean).join(" ");

    return `
      <tr class="${trCls}" data-user-id="${player.user_id}">
        <td${rankCls ? ` class="${rankCls}"` : ""}>${rank}</td>
        <td>${playerCell}</td>
        <td class="pts">${player.points}</td>
        <td>${player.wins}</td>
        <td>${player.draws}</td>
        <td>${player.losses}</td>
        <td>${player.goals_for}</td>
      </tr>
    `;
  }).join("");

  // Qatorga bosilganda — o'sha o'yinchining profilini ochish
  tbody.querySelectorAll(".rating-row").forEach(row => {
    row.addEventListener("click", () => {
      const userId = parseInt(row.dataset.userId);
      if (userId) openPlayerModal(userId);
    });
  });
}

// ============================================================
//  TOP SCORERS (barcha ligalar bo'yicha umumiy)
// ============================================================

async function loadTopScorers() {
  const leagues = APP.leagues || [];
  if (leagues.length === 0) return;

  // Har bir liga reytingini parallel so'raymiz, har bir o'yinchiga liga nomini qo'shamiz
  const results = await Promise.all(
    leagues.map(league =>
      apiFetch(`/rating/${league.id}`)
        .then(data => (data.rating || []).map(p => ({ ...p, league_name: league.name })))
        .catch(() => [])
    )
  );

  const allPlayers = results.flat();
  renderTopScorersTable(allPlayers);
}

function renderTopScorersTable(players) {
  const tbody = document.getElementById("top-scorers-tbody");

  // Faqat gol urgan o'yinchilar, eng ko'p gol bo'yicha kamayish tartibida
  const scorers = players
    .filter(p => p.goals_for > 0)
    .sort((a, b) => b.goals_for - a.goals_for);

  if (scorers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">${APP.t.no_data || "Ma'lumot yo'q"}</td></tr>`;
    return;
  }

  tbody.innerHTML = scorers.map((player, i) => {
    const rank    = i + 1;
    const rankCls = rank <= 3 ? `rank-${rank}` : "";

    // Klub logosini LEAGUE_CLUBS dan topamiz
    let clubLogo = null;
    let clubDisplayName = player.club_name || player.nickname;
    if (player.club_name) {
      for (const clubs of Object.values(LEAGUE_CLUBS)) {
        const found = clubs.find(c => c.name === player.club_name);
        if (found) { clubLogo = found.logo; clubDisplayName = found.name; break; }
      }
    }

    const logoHtml = clubLogo
      ? `<img src="${escHtml(clubLogo)}" alt="" style="width:24px;height:24px;object-fit:contain;border-radius:4px;flex-shrink:0;" onerror="this.style.display='none'" />`
      : "";
    const usernameRow = player.username
      ? `<span class="player-username">@${escHtml(player.username)}</span>`
      : "";

    const playerCell = `
      <div class="player-cell">
        ${logoHtml}
        <div class="player-cell-text">
          <span class="player-clubname">${escHtml(clubDisplayName)}</span>
          ${usernameRow}
        </div>
      </div>`;

    return `
      <tr class="rating-row" data-user-id="${player.user_id}">
        <td${rankCls ? ` class="${rankCls}"` : ""}>${rank}</td>
        <td>${playerCell}</td>
        <td>${escHtml(player.league_name)}</td>
        <td class="pts">${player.goals_for}</td>
      </tr>
    `;
  }).join("");

  // Qatorga bosilganda — o'sha o'yinchining profilini ochish
  tbody.querySelectorAll(".rating-row").forEach(row => {
    row.addEventListener("click", () => {
      const userId = parseInt(row.dataset.userId);
      if (userId) openPlayerModal(userId);
    });
  });
}



async function openPlayerModal(userId) {
  const t = APP.t;
  try {
    const data = await apiFetch(`/players/${userId}/profile`);
    renderPlayerModal(data);
    navigateTo("player");
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

function closePlayerModal() {
  // Reyting bo'limiga qaytish
  navigateTo("rating");
}

function renderPlayerModal(data) {
  const t = APP.t;

  const avatarEl   = document.getElementById("player-avatar-letter");
  const nicknameEl = document.getElementById("player-nickname");
  const leagueEl   = document.getElementById("player-league");
  const clubBadge  = document.getElementById("player-club-badge");

  // Avatar: Telegram rasmni proxy orqali yuklaymiz (maxfiy/yo'q bo'lsa — ism harfi)
  const letter = (data.nickname || "?")[0].toUpperCase();
  avatarEl.textContent = letter;
  if (data.user_id) {
    const img = new Image();
    img.src = `${API_BASE}/players/${data.user_id}/photo`;
    img.alt = escHtml(data.nickname || "");
    img.style.cssText = "width:56px;height:56px;object-fit:cover;border-radius:50%;";
    img.onload = () => {
      avatarEl.textContent = "";
      avatarEl.appendChild(img);
    };
    // onerror: rasm yo'q/maxfiy — ism harfi shundoq qoladi (hech narsa qilinmaydi)
  }

  // Klub logosi va nomi
  let clubObj = null;
  if (data.club_name) {
    for (const clubs of Object.values(LEAGUE_CLUBS)) {
      const found = clubs.find(c => c.name === data.club_name);
      if (found) { clubObj = found; break; }
    }
  }

  if (clubObj) {
    clubBadge.innerHTML = `<img src="${escHtml(clubObj.logo)}" alt="${escHtml(clubObj.name)}" style="width:32px;height:32px;object-fit:contain;" onerror="this.style.display='none'" />`;
    nicknameEl.textContent = clubObj.name;
  } else {
    clubBadge.innerHTML = "";
    nicknameEl.textContent = data.nickname || "—";
  }

  // Faqat Telegram username (link) yoki "Username yo'q" yozuvi — nickname ko'rsatilmaydi
  if (data.username) {
    const u = escHtml(data.username);
    leagueEl.innerHTML = `<a class="profile-username" href="https://t.me/${u}" target="_blank">@${u}</a>`;
  } else {
    leagueEl.innerHTML = `<span class="profile-no-username">${t.no_username || "Username yo'q"}</span>`;
  }

  // Statistika
  const r = data.rating;
  document.getElementById("player-stat-position").textContent = r ? `#${r.position}` : "—";
  document.getElementById("player-stat-wins").textContent     = r ? r.wins   : "—";
  document.getElementById("player-stat-draws").textContent    = r ? r.draws  : "—";
  document.getElementById("player-stat-losses").textContent   = r ? r.losses : "—";

  // O'yinlar tarixi (faqat ko'rsatish — tugmasiz, chunki bu boshqa odam)
  const list = document.getElementById("player-matches-list");
  const matches = data.matches || [];
  if (matches.length === 0) {
    list.innerHTML = `<div class="empty-state">${t.no_matches || "Hali o'yinlar yo'q"}</div>`;
    return;
  }
  list.innerHTML = matches.map(m => renderPlayerMatchItem(m)).join("");
}

function renderPlayerMatchItem(m) {
  const t = APP.t;

  let statusCls  = "status--pending";
  let statusText = t.status_pending || "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = t.status_awaiting || "TASDIQ"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = t.status_confirmed || "TASDIQLANDI"; }
  if (m.status === "rejected")              { statusCls = "status--rejected";  statusText = t.status_rejected  || "RAD ETILDI"; }

  return `
    <div class="match-item">
      <span class="match-day">${m.matchday}</span>
      <span class="match-names"><span class="match-id">#${m.id}</span></span>
      <span class="match-center">${renderMatchCenter(m)}</span>
      <span class="match-status ${statusCls}">${statusText}</span>
    </div>
  `;
}

// ============================================================
//  PROFILE SECTION
// ============================================================

async function loadProfile() {
  try {
    const data = await apiFetch("/profile");
    APP.profileData = data;
    renderProfile(data);
    await loadMyMatches();
    await loadAdminPanel();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

function renderProfile(data) {
  const t = APP.t;
  // Header nickname o'zgarmaydi
  document.getElementById("header-nickname").textContent = data.nickname || "—";

  const leagueEl = document.getElementById("profile-league");
  const avatarEl = document.getElementById("profile-avatar-letter");
  const nicknameEl = document.getElementById("profile-nickname");
  const clubBadgeEl = document.getElementById("profile-club-badge");

  // Avatar: telegram profil rasmi (bo'lmasa — ism harfi)
  const photoUrl = APP.currentUser?.photo_url || null;
  if (photoUrl) {
    avatarEl.innerHTML = `<img src="${escHtml(photoUrl)}" alt="${escHtml(data.nickname || "")}" style="width:56px;height:56px;object-fit:cover;border-radius:50%;" onerror="this.style.display='none';this.parentElement.textContent='${(data.nickname || "?")[0].toUpperCase()}'" />`;
  } else {
    avatarEl.textContent = (data.nickname || "?")[0].toUpperCase();
  }

  if (data.league_id) {
    const league = (APP.leagues || []).find(l => l.id === data.league_id);
    const leagueName = league ? league.name : `Liga #${data.league_id}`;

    // Klub logosi — DB dan club_name kelar, LEAGUE_CLUBS dan logoni topamiz
    const clubs = LEAGUE_CLUBS[leagueName] || [];
    const clubName = data.club_name || APP.selectedClub || null;
    const clubObj  = clubs.find(c => c.name === clubName) || null;

    // O'ng tomondagi belgi: tanlangan klub logosi (faqat ko'rsatish uchun)
    if (clubObj) {
      clubBadgeEl.innerHTML = `<img src="${escHtml(clubObj.logo)}" alt="${escHtml(clubObj.name)}" style="width:32px;height:32px;object-fit:contain;" onerror="this.style.display='none'" />`;
    } else {
      clubBadgeEl.innerHTML = "";
    }

    // profile-nickname — klub nomi
    nicknameEl.textContent = clubObj ? clubObj.name : (data.nickname || "—");

    // profile-league — foydalanuvchi nicki + username linki
    const username = APP.currentUser?.username || null;
    const displayName = escHtml(data.nickname || "");
    if (username) {
      leagueEl.innerHTML = `${displayName}<br><a class="profile-username" href="https://t.me/${escHtml(username)}" target="_blank">@${escHtml(username)}</a>`;
    } else {
      leagueEl.textContent = data.nickname || leagueName;
    }
  } else {
    // Ro'yxatdan o'tmagan
    clubBadgeEl.innerHTML = "";
    nicknameEl.textContent = data.nickname || "—";
    leagueEl.textContent = t.not_registered || "Ro'yxatdan o'tilmagan";
  }

  const r = data.rating;
  document.getElementById("stat-position").textContent = r ? `#${r.position}` : "—";
  document.getElementById("stat-wins").textContent     = r ? r.wins    : "—";
  document.getElementById("stat-draws").textContent    = r ? r.draws   : "—";
  document.getElementById("stat-losses").textContent   = r ? r.losses  : "—";
}

async function loadMyMatches() {
  const t = APP.t;
  const list = document.getElementById("matches-list");

  try {
    const data = await apiFetch("/matches/my");
    const matches = data.matches || [];

    if (matches.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <span class="empty-state-icon">⚽</span>
          ${t.no_matches || "Hali o'yinlar yo'q"}
        </div>`;
      return;
    }

    list.innerHTML = matches.map(m => renderMatchItem(m)).join("");

    // Natija kiritish tugmalariga event
    bindMatchActions(list);
  } catch (e) {
    list.innerHTML = `<div class="empty-state">${e.message}</div>`;
  }
}

// Match tugmalariga (Natija / ✔ / ✖) hodisa bog'laydi — Profil va Home ikkisida ishlatiladi
function bindMatchActions(listEl) {
  listEl.querySelectorAll(".match-action-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const matchId = parseInt(btn.dataset.matchId);
      const action  = btn.dataset.action;
      if (action === "submit") openResultModal(matchId);
      if (action === "confirm") confirmMatchResult(matchId, "confirm");
      if (action === "reject")  confirmMatchResult(matchId, "reject");
    });
  });
}

// Klub nomidan LEAGUE_CLUBS ichidan logoni topadi (topilmasa null)
function findClubLogo(clubName) {
  if (!clubName) return null;
  for (const clubs of Object.values(LEAGUE_CLUBS)) {
    const found = clubs.find(c => c.name === clubName);
    if (found) return found.logo;
  }
  return null;
}

// Bitta klub uchun logo (+ zaxira: nom yo'q bo'lsa bo'sh doira) HTML qaytaradi
function renderClubBadge(clubName) {
  const logo = findClubLogo(clubName);
  const safeName = escHtml(clubName || "");
  if (logo) {
    return `<img class="match-club-logo" src="${escHtml(logo)}" alt="${safeName}" title="${safeName}">`;
  }
  // Logo topilmadi (yoki klub nomi yo'q) — bo'sh doira zaxira
  return `<span class="match-club-logo match-club-logo--empty" title="${safeName}"></span>`;
}

// Match markazi: [logo1] score [logo2] — chap=player1, o'ng=player2 (qur'a tartibida).
// Klub nomlari hali yo'q bo'lsa (eski/registratsiyasiz holat) — faqat score ko'rsatiladi.
function renderMatchCenter(m) {
  const score = m.score1 !== null ? `${m.score1} : ${m.score2}` : "— : —";
  if (m.player1_club || m.player2_club) {
    return `
      ${renderClubBadge(m.player1_club)}
      <span class="match-score">${score}</span>
      ${renderClubBadge(m.player2_club)}
    `;
  }
  return `<span class="match-score">${score}</span>`;
}

function renderMatchItem(m) {
  const t       = APP.t;
  const myId    = APP.currentUser?.id;

  let statusCls  = "status--pending";
  let statusText = t.status_pending || "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = t.status_awaiting || "TASDIQ"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = t.status_confirmed || "TASDIQLANDI"; }
  if (m.status === "rejected")              { statusCls = "status--rejected";  statusText = t.status_rejected  || "RAD ETILDI"; }

  let actionBtn = "";
  if (m.status === "pending") {
    if (m.is_locked) {
      // Tur hali ochilmagan — natija kiritib bo'lmaydi, qulf belgisi
      actionBtn = `<span class="match-locked" title="${t.matchday_locked_short || "Tur hali ochilmagan"}">🔒</span>`;
    } else {
      actionBtn = `<button class="match-action-btn" data-match-id="${m.id}" data-action="submit">
        ${t.enter_result || "Natija"}
      </button>`;
    }
  } else if (m.status === "awaiting_confirmation" && m.submitted_by !== myId) {
    actionBtn = `
      <button class="match-action-btn" data-match-id="${m.id}" data-action="confirm">✔</button>
      <button class="match-action-btn" style="color:var(--red-neon);border-color:rgba(255,69,96,.3)" data-match-id="${m.id}" data-action="reject">✖</button>
    `;
  }

  return `
    <div class="match-item">
      <span class="match-day">${m.matchday}</span>
      <span class="match-names"><span class="match-id">#${m.id}</span></span>
      <span class="match-center">${renderMatchCenter(m)}</span>
      <span class="match-status ${statusCls}">${statusText}</span>
      ${actionBtn}
    </div>
  `;
}

// ============================================================
//  ADMIN PANEL
// ============================================================

async function loadAdminPanel() {
  const panel = document.getElementById("admin-panel");
  try {
    const players = await apiFetch("/admin/players");
    panel.classList.remove("hidden");
    renderAdminDraw();
    renderAdminPlayers(players);
    await loadRejectedMatches();
  } catch (e) {
    // Admin emas (403) yoki boshqa xato — panel yashirin qoladi
    panel.classList.add("hidden");
  }
}

function renderAdminDraw() {
  const t = APP.t;
  const list = document.getElementById("admin-draw-list");
  const leagues = APP.leagues || [];

  if (leagues.length === 0) {
    list.innerHTML = `<div class="empty-state">${t.no_data || "Ma'lumot yo'q"}</div>`;
    return;
  }

  list.innerHTML = leagues.map(league => {
    const isFull = !!league.is_full;
    const hasMatches = league.status !== "open";   // jadval (qur'a) bormi
    const hasDrawDate = !!league.has_draw_date;     // turnir boshlanganmi (draw_date)

    // Holat matni
    let stateText;
    if (!hasMatches) {
      stateText = `${league.current_players}/${league.max_players}`;
    } else if (!hasDrawDate) {
      stateText = t.admin_state_not_started || "Qur'a o'tkazilgan, hali boshlanmagan";
    } else {
      stateText = t.admin_state_running || "Turnir davom etmoqda";
    }

    // Tugmalar (holatga qarab)
    let buttons = "";
    if (!hasMatches) {
      // Hali qur'a o'tkazilmagan — Qur'a tugmasi (liga to'lgan bo'lsa)
      buttons = `
        <button class="admin-remove-btn admin-draw-btn" data-league-id="${league.id}" ${isFull ? "" : "disabled"}>
          ${t.admin_draw_button || "🎲 Qur'a o'tkazish"}
        </button>`;
    } else {
      // Qur'a o'tkazilgan
      if (!hasDrawDate) {
        // draw_date yo'q — Turnirni boshlash (xavfsiz)
        buttons += `
          <button class="admin-remove-btn admin-start-btn" data-league-id="${league.id}">
            ${t.admin_start_button || "▶️ Turnirni boshlash"}
          </button>`;
      }
      // Qayta qur'a (xavfli) — har doim ko'rinadi (qur'a bor bo'lsa)
      buttons += `
        <button class="admin-remove-btn admin-redraw-btn" data-league-id="${league.id}">
          ${t.admin_redraw_button || "🔄 Qayta qur'a"}
        </button>`;
    }

    return `
      <div class="admin-player-item">
        <div class="admin-player-info">
          ${escHtml(league.name)}
          <div class="admin-player-league">${stateText}</div>
        </div>
        <div class="admin-draw-actions">${buttons}</div>
      </div>
    `;
  }).join("");

  list.querySelectorAll(".admin-draw-btn").forEach(btn => {
    if (btn.disabled) return;
    btn.addEventListener("click", () => runLeagueDraw(parseInt(btn.dataset.leagueId)));
  });
  list.querySelectorAll(".admin-start-btn").forEach(btn => {
    btn.addEventListener("click", () => startLeagueTournament(parseInt(btn.dataset.leagueId)));
  });
  list.querySelectorAll(".admin-redraw-btn").forEach(btn => {
    btn.addEventListener("click", () => redrawLeague(parseInt(btn.dataset.leagueId)));
  });
}

async function runLeagueDraw(leagueId) {
  const t = APP.t;
  const confirmed = window.confirm(t.admin_draw_confirm || "Bu liga uchun qur'a o'tkazishni tasdiqlaysizmi?");
  if (!confirmed) return;

  try {
    await apiFetch(`/admin/league/${leagueId}/draw`, { method: "POST" });
    showToast(t.admin_draw_success || "✅ Qur'a o'tkazildi");
    await loadHome();
    await loadAdminPanel();
  } catch (e) {
    const msg = {
      league_not_full: t.admin_draw_not_full || "Liga hali to'lmagan",
      already_drawn:   t.admin_draw_already  || "Qur'a allaqachon o'tkazilgan",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

async function startLeagueTournament(leagueId) {
  const t = APP.t;
  const confirmed = window.confirm(t.admin_start_confirm || "Turnirni bugundan boshlashni tasdiqlaysizmi? (Natijalar saqlanadi)");
  if (!confirmed) return;

  try {
    await apiFetch(`/admin/league/${leagueId}/start`, { method: "POST" });
    showToast(t.admin_start_success || "✅ Turnir boshlandi");
    await loadHome();
    await loadAdminPanel();
  } catch (e) {
    const msg = {
      no_matches: t.admin_start_no_matches || "Avval qur'a o'tkazing",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

async function redrawLeague(leagueId) {
  const t = APP.t;
  // Xavfli amal — ikki marta tasdiq so'raymiz
  const c1 = window.confirm(t.admin_redraw_confirm || "DIQQAT: Qayta qur'a barcha kiritilgan natijalarni o'chiradi! Davom etasizmi?");
  if (!c1) return;
  const c2 = window.confirm(t.admin_redraw_confirm2 || "Aniqmisiz? Bu amalni ortga qaytarib bo'lmaydi.");
  if (!c2) return;

  try {
    await apiFetch(`/admin/league/${leagueId}/redraw`, { method: "POST" });
    showToast(t.admin_redraw_success || "✅ Qayta qur'a o'tkazildi");
    await loadHome();
    await loadAdminPanel();
  } catch (e) {
    const msg = {
      league_not_full: t.admin_draw_not_full || "Liga hali to'lmagan",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

function renderAdminPlayers(players) {
  const t = APP.t;
  const list = document.getElementById("admin-players-list");

  if (players.length === 0) {
    list.innerHTML = `<div class="empty-state">${t.no_data || "Ma'lumot yo'q"}</div>`;
    return;
  }

  list.innerHTML = players.map(p => {
    const usernamePart = p.username
      ? `<span class="admin-player-username">@${escHtml(p.username)}</span> `
      : "";
    let leagueLine;
    if (p.league_id) {
      const leagueName = (APP.leagues || []).find(l => l.id === p.league_id)?.name || `Liga #${p.league_id}`;
      const clubPart = p.club_name ? ` · ${escHtml(p.club_name)}` : "";
      leagueLine = `${escHtml(leagueName)}${clubPart}`;
    } else {
      leagueLine = t.not_registered || "Ro'yxatdan o'tilmagan";
    }
    return `
      <div class="admin-player-item">
        <div class="admin-player-info">
          ${usernamePart}${escHtml(p.nickname)}
          <div class="admin-player-league">${leagueLine}</div>
        </div>
        <button class="admin-remove-btn" data-user-id="${p.id}">
          ${t.admin_remove_player || "Chiqarish"}
        </button>
      </div>
    `;
  }).join("");

  list.querySelectorAll(".admin-remove-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const userId = parseInt(btn.dataset.userId);
      removePlayer(userId);
    });
  });
}

async function removePlayer(userId) {
  const t = APP.t;
  const confirmed = window.confirm(t.admin_confirm_remove || "Bu o'yinchini chiqarishni tasdiqlaysizmi?");
  if (!confirmed) return;

  try {
    await apiFetch(`/admin/players/${userId}`, { method: "DELETE" });
    showToast(t.admin_player_removed || "✅ O'yinchi chiqarildi");
    await loadAdminPanel();
    await loadHome();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

async function loadRejectedMatches() {
  const list = document.getElementById("admin-rejected-list");
  try {
    const matches = await apiFetch("/admin/rejected-matches");
    renderRejectedMatches(matches);
  } catch (e) {
    list.innerHTML = `<div class="empty-state">${e.message}</div>`;
  }
}

function renderRejectedMatches(matches) {
  const t = APP.t;
  const list = document.getElementById("admin-rejected-list");

  if (matches.length === 0) {
    list.innerHTML = `<div class="empty-state">${t.no_data || "Ma'lumot yo'q"}</div>`;
    return;
  }

  list.innerHTML = matches.map(m => `
    <div class="admin-player-item">
      <div class="admin-player-info">
        <span class="match-id">#${m.id}</span> ${escHtml(m.player1_nickname)} vs ${escHtml(m.player2_nickname)}
        <div class="admin-player-league">${t.matchday || "Tur"} ${m.matchday}</div>
      </div>
      <button class="admin-remove-btn admin-set-result-btn"
        data-match-id="${m.id}"
        data-p1="${escHtml(m.player1_nickname)}"
        data-p2="${escHtml(m.player2_nickname)}">
        ${t.admin_set_result || "Natija"}
      </button>
      <button class="admin-remove-btn admin-reset-match-btn" data-match-id="${m.id}">
        ${t.admin_reset_match || "Qayta tiklash"}
      </button>
    </div>
  `).join("");

  list.querySelectorAll(".admin-set-result-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const matchId = parseInt(btn.dataset.matchId);
      openAdminResolveModal(matchId, btn.dataset.p1, btn.dataset.p2);
    });
  });

  list.querySelectorAll(".admin-reset-match-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const matchId = parseInt(btn.dataset.matchId);
      resetRejectedMatch(matchId);
    });
  });
}

function openAdminResolveModal(matchId, p1Name, p2Name) {
  APP.adminResolveMatchId = matchId;
  document.getElementById("admin-resolve-player1-name").textContent = p1Name;
  document.getElementById("admin-resolve-player2-name").textContent = p2Name;
  document.getElementById("admin-resolve-score1").value = 0;
  document.getElementById("admin-resolve-score2").value = 0;
  document.getElementById("modal-admin-resolve").classList.remove("hidden");
}

function closeAdminResolveModal() {
  document.getElementById("modal-admin-resolve").classList.add("hidden");
  APP.adminResolveMatchId = null;
}

async function submitAdminSetResult() {
  const t = APP.t;
  const matchId = APP.adminResolveMatchId;
  if (!matchId) return;

  const score1 = parseInt(document.getElementById("admin-resolve-score1").value);
  const score2 = parseInt(document.getElementById("admin-resolve-score2").value);

  try {
    await apiFetch(`/admin/match/resolve?match_id=${matchId}&action=set_result&score1=${score1}&score2=${score2}`, {
      method: "POST",
    });
    showToast(t.admin_match_resolved || "✅ Natija belgilandi");
    closeAdminResolveModal();
    await loadRejectedMatches();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

async function resetRejectedMatch(matchId) {
  const t = APP.t;
  try {
    await apiFetch(`/admin/match/resolve?match_id=${matchId}&action=reset`, {
      method: "POST",
    });
    showToast(t.admin_match_resolved || "✅ Natija belgilandi");
    await loadRejectedMatches();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

async function submitAdminFixConfirmed() {
  const t = APP.t;
  const matchIdInput = document.getElementById("admin-fix-match-id");
  const matchId = parseInt(matchIdInput.value);

  if (!matchId) {
    showToast("❌ " + (t.admin_fix_match_id_required || "Match ID kiritilmadi"));
    return;
  }

  const score1 = parseInt(document.getElementById("admin-fix-score1").value);
  const score2 = parseInt(document.getElementById("admin-fix-score2").value);

  try {
    await apiFetch(`/admin/match/fix-confirmed?match_id=${matchId}&score1=${score1}&score2=${score2}`, {
      method: "POST",
    });
    showToast(t.admin_fix_success || "✅ Natija tuzatildi");
    matchIdInput.value = "";
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

// ============================================================
//  PRIZES SECTION
// ============================================================

async function loadPrizes() {
  const leagueId = APP.selectedLeagueId;
  if (!leagueId) return;

  renderPrizesFilter();

  try {
    await fetchAndRenderPrizes(leagueId);
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

async function fetchAndRenderPrizes(leagueId) {
  const data = await apiFetch(`/prizes/${leagueId}`);
  const t = APP.t;

  // Klub logosini LEAGUE_CLUBS dan topuvchi yordamchi funksiya
  function findClub(player) {
    if (!player || !player.club_name) return null;
    for (const clubs of Object.values(LEAGUE_CLUBS)) {
      const found = clubs.find(c => c.name === player.club_name);
      if (found) return found;
    }
    return null;
  }

  function renderPrizeClub(player, holderEl, clubEl) {
    if (!player) {
      holderEl.textContent = "—";
      clubEl.innerHTML = "";
      return;
    }
    // Birinchi qator: username (Telegram chatiga link) yoki nickname (oddiy)
    let displayName;
    if (player.username) {
      const u = escHtml(player.username);
      displayName = `<a class="prize-holder-link" href="https://t.me/${u}" target="_blank">@${u}</a>`;
    } else {
      displayName = `<span class="prize-holder-name">${escHtml(player.nickname)}</span>`;
    }
    holderEl.innerHTML = displayName;

    // Ikkinchi qator: klub logosi + klub nomi
    const club = findClub(player);
    if (club) {
      clubEl.innerHTML = `
        <img src="${escHtml(club.logo)}" alt="${escHtml(club.name)}"
             class="prize-club-logo"
             onerror="this.style.display='none'" />
        <span class="prize-club-name">${escHtml(club.name)}</span>`;
    } else {
      clubEl.innerHTML = "";
    }
  }

  renderPrizeClub(
    data.top_scorer
      ? { ...data.top_scorer, _suffix: ` — ${data.top_scorer.goals_for} ${t.goals || "gol"}` }
      : null,
    document.getElementById("prize-top-scorer"),
    document.getElementById("prize-top-scorer-club")
  );

  // top_scorer uchun gol sonini qo'shib chiqamiz
  if (data.top_scorer) {
    const el = document.getElementById("prize-top-scorer");
    el.innerHTML += `<span class="prize-goals"> — ${data.top_scorer.goals_for} ${t.goals || "gol"}</span>`;
  }

  renderPrizeClub(
    data.current_leader || null,
    document.getElementById("prize-winner"),
    document.getElementById("prize-winner-club")
  );
}

function renderPrizesFilter() {
  const filter = document.getElementById("prizes-filter");
  filter.innerHTML = "";
  (APP.leagues || []).forEach(league => {
    const btn = document.createElement("button");
    btn.className = "tab-btn" + (league.id === APP.selectedLeagueId ? " active" : "");
    btn.textContent = league.name;
    btn.addEventListener("click", async () => {
      APP.selectedLeagueId = league.id;
      document.querySelectorAll("#prizes-filter .tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      try { await fetchAndRenderPrizes(league.id); }
      catch (e) { showToast("❌ " + e.message); }
    });
    filter.appendChild(btn);
  });
}

// ============================================================
//  REGISTER
// ============================================================

async function registerToLeague() {
  const leagueId = APP.selectedLeagueId;
  if (!leagueId) { showToast(APP.t.choose_league || "Liga tanlang"); return; }

  if (!APP.selectedClub) { showToast(APP.t.select_club || "Klub tanlang"); return; }

  // Mavsumda allaqachon ro'yxatdan o'tganligini tekshirish (local)
  if (APP.profileData && APP.profileData.league_id) {
    showToast(APP.t.already_in_season || "Siz bu mavsumda allaqachon ro'yxatdansiz");
    return;
  }

  const btn = document.getElementById("btn-register");
  btn.disabled = true;
  try {
    await apiFetch(
      `/register?league_id=${leagueId}&club_name=${encodeURIComponent(APP.selectedClub)}`,
      { method: "POST" }
    );
    showToast(APP.t.registered_ok || "✅ Ro'yxatdan o'tdingiz!");
    APP.selectedClub = null;
    document.getElementById("clubs-section").classList.add("hidden");
    await loadHome();
    await loadProfile();
  } catch (e) {
    const msg = {
      already_registered: APP.t.already_registered || "Siz allaqachon ro'yxatdansiz",
      league_full:        APP.t.league_full_err    || "Liga to'liq",
      club_taken:         APP.t.club_taken          || "Bu klub allaqachon band qilingan",
    }[e.message] || e.message;
    showToast("❌ " + msg);
    btn.disabled = false;
    // Klub band bo'lib chiqsa — ro'yxatni yangilab, band holatini ko'rsatamiz
    if (e.message === "club_taken") {
      APP.selectedClub = null;
      const league = (APP.leagues || []).find(l => l.id === leagueId);
      if (league) void renderClubsForLeague(league);
    }
  }
}

// ============================================================
//  RESULT MODAL
// ============================================================

function openResultModal(matchId) {
  APP.activeMatchId = matchId;
  document.getElementById("modal-result").classList.remove("hidden");
}

function closeResultModal() {
  APP.activeMatchId = null;
  document.getElementById("modal-result").classList.add("hidden");
  document.getElementById("input-score1").value = "0";
  document.getElementById("input-score2").value = "0";
}

async function submitMatchResult() {
  const matchId = APP.activeMatchId;
  const score1  = parseInt(document.getElementById("input-score1").value) || 0;
  const score2  = parseInt(document.getElementById("input-score2").value) || 0;

  try {
    await apiFetch(
      `/match/submit-result?match_id=${matchId}&score1=${score1}&score2=${score2}`,
      { method: "POST" }
    );
    closeResultModal();
    showToast(APP.t.result_submitted || "✅ Natija yuborildi");
    await refreshMatchViews();
  } catch (e) {
    const msg = {
      matchday_locked: APP.t.matchday_locked || "Bu tur hali ochilmagan",
    }[e.message] || e.message;
    showToast("❌ " + msg);
  }
}

async function confirmMatchResult(matchId, action) {
  try {
    await apiFetch(
      `/match/confirm?match_id=${matchId}&action=${action}`,
      { method: "POST" }
    );
    const msg = action === "confirm"
      ? (APP.t.result_confirmed || "✅ Tasdiqlandi")
      : (APP.t.result_rejected  || "❌ Rad etildi");
    showToast(msg);
    await refreshMatchViews();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

// Natija o'zgargach Profil va Home dagi o'yinlar ro'yxatini izchil yangilaydi
async function refreshMatchViews() {
  await loadMyMatches();
  await loadHomeMatches();
}

// ============================================================
//  NICKNAME MODAL
// ============================================================

function openNicknameModal() {
  const current = document.getElementById("profile-nickname").textContent;
  document.getElementById("input-nickname").value = current === "—" ? "" : current;
  document.getElementById("modal-nickname").classList.remove("hidden");
}

function closeNicknameModal() {
  document.getElementById("modal-nickname").classList.add("hidden");
}

async function saveNickname() {
  const val = document.getElementById("input-nickname").value.trim();
  if (val.length < 2 || val.length > 20) {
    showToast(APP.t.nickname_invalid || "2–20 belgi bo'lishi kerak");
    return;
  }
  try {
    await apiFetch(`/profile/nickname?nickname=${encodeURIComponent(val)}`, { method: "POST" });
    showToast(APP.t.nickname_saved || "✅ Nickname saqlandi");
    closeNicknameModal();
    await loadProfile();
  } catch (e) {
    showToast("❌ " + e.message);
  }
}

// ============================================================
//  UTILITY
// ============================================================

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
