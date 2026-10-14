// ============================================================
//  ac_player.js — Reytingdagi ishtirokchiga bosilganda ochiladigan PROFIL SAHIFASI.
//  Modal emas: AC.section = "player". Profil bilan bir xil ko'rinish, lekin:
//    - GOLLAR/ochko bloki YO'Q (reytingda ko'rinadi — 1-punkt)
//    - o'yinlar faqat KO'RISH uchun (💬/Natija tugmalarisiz)
//  Ma'lumot: AC.viewPlayer (reyting qatoridan) + /ac/matches/user/{id} (o'yinlar).
// ============================================================

function acOpenPlayerModal(userId) {
  const rows = AC.rating || [];
  const row = rows.find(r => r.user_id === userId);
  if (!row) return;
  AC.viewPlayer = { ...row, position: row._pos, group_number: row._group };
  AC.viewPlayerMatches = null;
  AC.viewPlayerPoMatches = null;   // 2026-07-22: play-off o'yinlari (talab 3)
  AC.section = "player";
  renderAsianChampionsLeague();
  void acLoadPlayerMatches(userId);
  void acLoadPlayerPoMatches(userId);
}

// 2026-07-22: setka juftligidan ochilgan profil — reyting qatorisiz ham ishlaydi.
// (Setkadagi odam guruh reytingida bo'ladi, lekin himoya uchun minimal karta.)
function acOpenPlayerFromBracket(userId, side) {
  const rows = AC.rating || [];
  const row = rows.find(r => r.user_id === userId);
  if (row) { acOpenPlayerModal(userId); return; }
  // Reytingda topilmasa — setka ma'lumotidan minimal profil (nomi/klubi)
  const p = side || {};
  AC.viewPlayer = {
    user_id: userId, nickname: p.nickname, username: p.username,
    club_name: p.club_name, position: "—", group_number: "—",
    wins: "—", draws: "—", losses: "—", _minimal: true,
  };
  AC.viewPlayerMatches = null;
  AC.viewPlayerPoMatches = null;
  AC.section = "player";
  renderAsianChampionsLeague();
  void acLoadPlayerMatches(userId);
  void acLoadPlayerPoMatches(userId);
}

async function acLoadPlayerMatches(userId) {
  try {
    const d = await apiFetch(`/ac/matches/user/${userId}`);
    AC.viewPlayerMatches = d.matches || [];
  } catch (_) {
    AC.viewPlayerMatches = [];
  }
  if (AC.section === "player") renderAsianChampionsLeague();
}

// Boshqa ishtirokchining play-off o'yinlari (faqat ko'rish — talab 3)
async function acLoadPlayerPoMatches(userId) {
  try {
    const d = await apiFetch(`/ac/playoff/user/${userId}/matches`);
    AC.viewPlayerPoMatches = (d && d.started) ? (d.matches || []) : [];
  } catch (_) {
    AC.viewPlayerPoMatches = [];
  }
  if (AC.section === "player") renderAsianChampionsLeague();
}

function acRenderPlayer() {
  const p = AC.viewPlayer;
  if (!p) return `<div class="card">${ACT("ac_player_404")}</div>`;

  const letter = (p.nickname || "?")[0].toUpperCase();

  return `
    <button class="btn ac-back-link" id="ac-player-back">
      ${ICON.get("back", 16)} Reytingga qaytish
    </button>

    <div class="card card--profile">
      <div class="profile-avatar" id="ac-player-avatar" data-uid="${p.user_id}">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}</h2>
        <div class="ac-rating-user${p.username ? " ac-user-link" : ""}"
             ${p.username ? `data-ac-tg="${escHtml(p.username)}"` : ""}>${p.username ? "@" + escHtml(p.username) : "—"}${prizeStarsHtml(p)}</div>
        <span class="profile-league">${p.group_number ? `${ACT("ac_profile_phase")} · ${p.position}-o'rin` : ACT("ac_draw_pending")}</span>
      </div>
      <div class="profile-club-badge">${acClubBadge(p.club_name, 44)}</div>
    </div>

    <div class="section-label">STATISTIKA</div>
    <div class="stats-grid">
      <div class="stat-card stat-card--primary">
        <span class="stat-card-value neon-cyan">#${p.position}</span>
        <span class="stat-card-label">O'rin</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-cyan">${p.wins}</span>
        <span class="stat-card-label">G'alaba</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value">${p.draws}</span>
        <span class="stat-card-label">Durang</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-red">${p.losses}</span>
        <span class="stat-card-label">${ACT("ac_losses")}</span>
      </div>
    </div>

    <div class="section-label">O'YINLAR</div>
    ${acRenderPlayerMatches()}
    ${acRenderPlayerPoMatches()}`;
}

// Play-off o'yinlari bloki — faqat play-off boshlangan va o'yin bo'lsa ko'rinadi (talab 3)
function acRenderPlayerPoMatches() {
  const ms = AC.viewPlayerPoMatches;
  if (ms === null) return "";                 // hali yuklanmoqda — jim (guruh o'yinlari yetarli)
  if (!ms.length) return "";                  // play-off yo'q — blok umuman ko'rsatilmaydi
  return `
    <div class="section-label" style="margin-top:16px">PLAY-OFF O'YINLARI</div>
    <div class="matches-list">${ms.map(acRenderPlayerPoItem).join("")}</div>`;
}

// Play-off o'yin kartasi — faqat ko'rish (tugmasiz). acpoLegLabel/acClubBadge qayta ishlatiladi (DRY).
function acRenderPlayerPoItem(m) {
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const label = (typeof acpoLegLabel === "function")
    ? acpoLegLabel(m) : (m.round + (m.leg ? " · " + m.leg + "-o'yin" : ""));
  const center = `
    <span class="ac-mc-logo">${acClubBadge(m.p1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="ac-mc-logo">${acClubBadge(m.p2_club, 26)}</span>`;

  let statusCls = "status--pending", statusText = "KUTILMOQDA";
  if (m.status === "confirmed") { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }
  else if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }

  // 2-o'yinda 1-o'yin hisobi (agregat konteksti) — acpoMyMatchItem bilan bir xil
  const ctx = (m.leg === 2 && m.other_leg_score1 !== null && m.other_leg_score1 !== undefined)
    ? `<div class="ac-po-ctx">1-o'yin: ${m.other_leg_score1} : ${m.other_leg_score2}</div>` : "";

  return `
    <div class="ac-match-wrap">
      <div class="ac-match-head">
        <span class="ac-match-round">${escHtml(label)}</span><span class="ac-match-id">#${m.id}</span>
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="ac-match-body">
        <div class="match-center">${center}</div>
      </div>
      ${ctx}
    </div>`;
}

// Boshqa o'yinchining o'yinlari — faqat ko'rish (tugmasiz)
function acRenderPlayerMatches() {
  const ms = AC.viewPlayerMatches;
  if (ms === null) return `<div class="wc-loading-row">${ACT("ac_loading")}</div>`;
  if (!ms.length) return `<div class="wc-loading-row">${ACT("ac_no_matches_short")}</div>`;

  return `<div class="matches-list">${ms.map(acRenderPlayerMatchItem).join("")}</div>`;
}

function acRenderPlayerMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const center = `
    <span class="ac-mc-logo">${acClubBadge(m.player1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="ac-mc-logo">${acClubBadge(m.player2_club, 26)}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "confirmed") { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }
  else if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }

  return `
    <div class="ac-match-wrap">
      <div class="ac-match-head">
        <span class="ac-match-round">${m.matchday}-tur</span><span class="ac-match-id">#${m.id}</span>
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="ac-match-body">
        <div class="match-center">${center}</div>
      </div>
    </div>`;
}

function acBindPlayer(root) {
  const back = root.querySelector("#ac-player-back");
  if (back) back.addEventListener("click", () => {
    AC.section = "rating";
    renderAsianChampionsLeague();
  });

  // Username'ga bosilsa — raqib Telegram chati
  const tg = root.querySelector("[data-ac-tg]");
  if (tg) tg.addEventListener("click", () => {
    const uname = tg.dataset.acTg.replace(/^@/, "");
    const link = `https://t.me/${uname}`;
    const w = window.Telegram?.WebApp;
    if (w?.openTelegramLink) { try { w.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); } }
    else window.open(link, "_blank");
  });

  const box = root.querySelector("#ac-player-avatar");
  if (!box) return;
  const img = new Image();
  img.src = `${API_BASE}/players/${box.dataset.uid}/photo`;
  img.alt = "";
  img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};
}
