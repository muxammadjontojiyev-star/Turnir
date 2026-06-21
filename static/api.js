/**
 * api.js — eFootball Turnir WebApp
 * Barcha API chaqiruvlari va section ma'lumotlarini yuklash.
 * app.js bilan birga ishlaydi (APP global ob'ekti orqali).
 */

// ============================================================
//  API HELPER
// ============================================================

const API_BASE = "";  // Xuddi shu serverda ishlaydi (uvicorn)

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

// ============================================================
//  LIGA KLUBLAR MA'LUMOTLARI (statik, alifbo tartibida)
// ============================================================

const LEAGUE_CLUBS = {
  "LaLiga": [
    { name: "Almería",          logo: "https://upload.wikimedia.org/wikipedia/en/0/09/UD_Almer%C3%ADa_logo.svg" },
    { name: "Athletic Club",    logo: "https://upload.wikimedia.org/wikipedia/en/9/98/Club_Athletic_de_Bilbao_logo.svg" },
    { name: "Atlético Madrid",  logo: "https://upload.wikimedia.org/wikipedia/en/f/f4/Atletico_de_madrid_crest.svg" },
    { name: "Barcelona",        logo: "https://upload.wikimedia.org/wikipedia/en/4/47/FC_Barcelona_%28crest%29.svg" },
    { name: "Betis",            logo: "https://upload.wikimedia.org/wikipedia/en/1/13/Real_betis_logo.svg" },
    { name: "Cádiz",            logo: "https://upload.wikimedia.org/wikipedia/en/3/39/C%C3%A1diz_CF_logo.svg" },
    { name: "Celta Vigo",       logo: "https://upload.wikimedia.org/wikipedia/en/3/30/RC_Celta_de_Vigo_logo.svg" },
    { name: "Getafe",           logo: "https://upload.wikimedia.org/wikipedia/en/3/35/Getafe_CF_logo.svg" },
    { name: "Girona",           logo: "https://upload.wikimedia.org/wikipedia/en/6/60/Girona_FC_logo.svg" },
    { name: "Granada",          logo: "https://upload.wikimedia.org/wikipedia/en/6/6a/Granada_CF_logo.svg" },
    { name: "Las Palmas",       logo: "https://upload.wikimedia.org/wikipedia/en/7/75/UD_Las_Palmas_logo.svg" },
    { name: "Mallorca",         logo: "https://upload.wikimedia.org/wikipedia/en/9/9f/Real_Mallorca.svg" },
    { name: "Osasuna",          logo: "https://upload.wikimedia.org/wikipedia/en/d/db/Osasuna_logo.svg" },
    { name: "Rayo Vallecano",   logo: "https://upload.wikimedia.org/wikipedia/en/2/27/Rayo_Vallecano_logo.svg" },
    { name: "Real Madrid",      logo: "https://upload.wikimedia.org/wikipedia/en/5/56/Real_Madrid_CF.svg" },
    { name: "Real Sociedad",    logo: "https://upload.wikimedia.org/wikipedia/en/f/f1/Real_Sociedad_logo.svg" },
    { name: "Sevilla",          logo: "https://upload.wikimedia.org/wikipedia/en/3/3b/Sevilla_FC_logo.svg" },
    { name: "Valencia",         logo: "https://upload.wikimedia.org/wikipedia/en/c/ce/Valenciacf.svg" },
    { name: "Valladolid",       logo: "https://upload.wikimedia.org/wikipedia/en/6/6d/Real_Valladolid_logo.svg" },
    { name: "Villarreal",       logo: "https://upload.wikimedia.org/wikipedia/en/b/b9/Villarreal_CF_logo.svg" },
  ],
  "Premier Liga": [
    { name: "Arsenal",          logo: "https://upload.wikimedia.org/wikipedia/en/5/53/Arsenal_FC.svg" },
    { name: "Aston Villa",      logo: "https://upload.wikimedia.org/wikipedia/en/f/f9/Aston_Villa_FC_crest_%282016%29.svg" },
    { name: "Bournemouth",      logo: "https://upload.wikimedia.org/wikipedia/en/e/e5/AFC_Bournemouth_%282013%29.svg" },
    { name: "Brentford",        logo: "https://upload.wikimedia.org/wikipedia/en/2/2a/Brentford_FC_crest.svg" },
    { name: "Brighton",         logo: "https://upload.wikimedia.org/wikipedia/en/f/fd/Brighton_%26_Hove_Albion_logo.svg" },
    { name: "Burnley",          logo: "https://upload.wikimedia.org/wikipedia/en/6/62/Burnley_F.C._Logo.svg" },
    { name: "Chelsea",          logo: "https://upload.wikimedia.org/wikipedia/en/c/cc/Chelsea_FC.svg" },
    { name: "Crystal Palace",   logo: "https://upload.wikimedia.org/wikipedia/en/a/a2/Crystal_Palace_FC_logo_%282022%29.svg" },
    { name: "Everton",          logo: "https://upload.wikimedia.org/wikipedia/en/7/7c/Everton_FC_logo.svg" },
    { name: "Fulham",           logo: "https://upload.wikimedia.org/wikipedia/en/e/eb/Fulham_FC_%28shield%29.svg" },
    { name: "Liverpool",        logo: "https://upload.wikimedia.org/wikipedia/en/0/0c/Liverpool_FC.svg" },
    { name: "Luton Town",       logo: "https://upload.wikimedia.org/wikipedia/en/9/9d/Luton_Town_FC_logo.svg" },
    { name: "Man City",         logo: "https://upload.wikimedia.org/wikipedia/en/e/eb/Manchester_City_FC_badge.svg" },
    { name: "Man United",       logo: "https://upload.wikimedia.org/wikipedia/en/7/7a/Manchester_United_FC_crest.svg" },
    { name: "Newcastle",        logo: "https://upload.wikimedia.org/wikipedia/en/5/56/Newcastle_United_Logo.svg" },
    { name: "Nottm Forest",     logo: "https://upload.wikimedia.org/wikipedia/en/e/e5/Nottingham_Forest_F.C._logo.svg" },
    { name: "Sheffield Utd",    logo: "https://upload.wikimedia.org/wikipedia/en/9/9c/Sheffield_United_FC_logo.svg" },
    { name: "Tottenham",        logo: "https://upload.wikimedia.org/wikipedia/en/b/b4/Tottenham_Hotspur.svg" },
    { name: "West Ham",         logo: "https://upload.wikimedia.org/wikipedia/en/c/c2/West_Ham_United_FC_logo.svg" },
    { name: "Wolves",           logo: "https://upload.wikimedia.org/wikipedia/en/f/fc/Wolverhampton_Wanderers.svg" },
  ],
};

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
        APP.selectedClub = club.name;
        document.querySelectorAll(".club-item").forEach(el => el.classList.remove("selected"));
        item.classList.add("selected");
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
  document.getElementById("profile-nickname").textContent = data.nickname || "—";
  document.getElementById("header-nickname").textContent  = data.nickname || "—";

  const letter = (data.nickname || "?")[0].toUpperCase();
  document.getElementById("profile-avatar-letter").textContent = letter;

  const leagueEl = document.getElementById("profile-league");
  if (data.league_id) {
    const league = (APP.leagues || []).find(l => l.id === data.league_id);
    leagueEl.textContent = league ? league.name : `Liga #${data.league_id}`;
  } else {
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
