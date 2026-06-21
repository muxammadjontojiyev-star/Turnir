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

    renderLeagues(leagues);
    renderHeroCard(open || null);
    renderRules();
  } catch (e) {
    showToast("❌ " + e.message);
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
      renderClubsForLeague(league);
    });

    list.appendChild(item);
  });

  // Birinchi tanlangan liga uchun klublarni ham ko'rsat
  const selected = leagues.find(l => l.id === APP.selectedLeagueId);
  if (selected) renderClubsForLeague(selected);
}

// Foydalanuvchi bu mavsumda tanlagan klub (local state) — app.js dagi APP.selectedClub
function renderClubsForLeague(league) {
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

  // Alifbo tartibida (allaqachon alifbo tartibida, lekin sort qilamiz xavfsizlik uchun)
  const sorted = [...clubs].sort((a, b) => a.name.localeCompare(b.name));

  sorted.forEach(club => {
    const item = document.createElement("div");
    const isSelected = APP.selectedClub === club.name;
    item.className = "club-item" +
      (isSelected ? " selected" : "") +
      (alreadyRegistered ? " disabled" : "");

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

    if (!alreadyRegistered) {
      item.addEventListener("click", () => {
        APP.selectedClub     = club.name;
        APP.selectedClubLogo = club.logo;
        // Klublar bo'limini to'liq yashirish
        document.getElementById("clubs-section").classList.add("hidden");
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
  (APP.leagues || []).forEach(league => {
    const btn = document.createElement("button");
    btn.className = "tab-btn" + (league.id === APP.selectedLeagueId ? " active" : "");
    btn.textContent = league.name;
    btn.addEventListener("click", async () => {
      APP.selectedLeagueId = league.id;
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
    const rankCls = rank <= 3 ? ` class="rank-${rank}"` : "";
    const isMeCls = player.user_id === myId ? " class=\"is-me\"" : "";
    return `
      <tr${isMeCls}>
        <td${rankCls}>${rank}</td>
        <td>${escHtml(player.nickname)}</td>
        <td class="pts">${player.points}</td>
        <td>${player.wins}</td>
        <td>${player.draws}</td>
        <td>${player.losses}</td>
        <td>${player.goals_for}</td>
      </tr>
    `;
  }).join("");
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

  if (data.league_id) {
    const league = (APP.leagues || []).find(l => l.id === data.league_id);
    const leagueName = league ? league.name : `Liga #${data.league_id}`;

    // Klub logosi — DB dan club_name kelar, LEAGUE_CLUBS dan logoni topamiz
    const clubs = LEAGUE_CLUBS[leagueName] || [];
    const clubName = data.club_name || APP.selectedClub || null;
    const clubObj  = clubs.find(c => c.name === clubName) || null;

    // Avatar: klub logosi yoki harf
    if (clubObj) {
      avatarEl.innerHTML = `<img src="${escHtml(clubObj.logo)}" alt="${escHtml(clubObj.name)}" style="width:56px;height:56px;object-fit:contain;border-radius:50%;background:transparent;" onerror="this.style.display='none';this.parentElement.textContent='${clubObj.name[0].toUpperCase()}'" />`;
    } else {
      avatarEl.textContent = (data.nickname || "?")[0].toUpperCase();
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
    avatarEl.textContent = (data.nickname || "?")[0].toUpperCase();
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
    list.querySelectorAll(".match-action-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const matchId = parseInt(btn.dataset.matchId);
        const action  = btn.dataset.action;
        if (action === "submit") openResultModal(matchId);
        if (action === "confirm") confirmMatchResult(matchId, "confirm");
        if (action === "reject")  confirmMatchResult(matchId, "reject");
      });
    });
  } catch (e) {
    list.innerHTML = `<div class="empty-state">${e.message}</div>`;
  }
}

function renderMatchItem(m) {
  const t       = APP.t;
  const myId    = APP.currentUser?.id;
  const isP1    = m.player1_id === myId;
  const score   = m.score1 !== null
    ? `${m.score1} : ${m.score2}`
    : "— : —";

  let statusCls  = "status--pending";
  let statusText = t.status_pending || "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = t.status_awaiting || "TASDIQ"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = t.status_confirmed || "TASDIQLANDI"; }
  if (m.status === "rejected")              { statusCls = "status--rejected";  statusText = t.status_rejected  || "RAD ETILDI"; }

  let actionBtn = "";
  if (m.status === "pending") {
    actionBtn = `<button class="match-action-btn" data-match-id="${m.id}" data-action="submit">
      ${t.enter_result || "Natija"}
    </button>`;
  } else if (m.status === "awaiting_confirmation" && m.submitted_by !== myId) {
    actionBtn = `
      <button class="match-action-btn" data-match-id="${m.id}" data-action="confirm">✔</button>
      <button class="match-action-btn" style="color:var(--red-neon);border-color:rgba(255,69,96,.3)" data-match-id="${m.id}" data-action="reject">✖</button>
    `;
  }

  return `
    <div class="match-item">
      <span class="match-day">${m.matchday}</span>
      <span class="match-names">Men vs Raqib</span>
      <span class="match-score">${score}</span>
      <span class="match-status ${statusCls}">${statusText}</span>
      ${actionBtn}
    </div>
  `;
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

  document.getElementById("prize-top-scorer").textContent =
    data.top_scorer ? `${escHtml(data.top_scorer.nickname)} — ${data.top_scorer.goals_for} ${t.goals || "gol"}` : "—";

  document.getElementById("prize-winner").textContent =
    data.current_leader ? escHtml(data.current_leader.nickname) : "—";
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
    }[e.message] || e.message;
    showToast("❌ " + msg);
    btn.disabled = false;
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
    await loadMyMatches();
  } catch (e) {
    showToast("❌ " + e.message);
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
    await loadMyMatches();
  } catch (e) {
    showToast("❌ " + e.message);
  }
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
