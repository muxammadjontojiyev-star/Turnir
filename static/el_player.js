// ============================================================
//  el_player.js — Reytingdagi ishtirokchiga bosilganda ochiladigan PROFIL SAHIFASI.
//  Modal emas: EL.section = "player". Profil bilan bir xil ko'rinish, lekin:
//    - GOLLAR/ochko bloki YO'Q (reytingda ko'rinadi — 1-punkt)
//    - o'yinlar faqat KO'RISH uchun (💬/Natija tugmalarisiz)
//  Ma'lumot: EL.viewPlayer (reyting qatoridan) + /el/matches/user/{id} (o'yinlar).
// ============================================================

function elOpenPlayerModal(userId) {
  const rows = EL.rating || [];
  const row = rows.find(r => r.user_id === userId);
  if (!row) return;
  EL.viewPlayer = { ...row, position: row._pos, group_number: row._group };
  EL.viewPlayerMatches = null;
  EL.viewPlayerPoMatches = null;   // 2026-07-22: play-off o'yinlari (talab 3)
  EL.section = "player";
  renderEuropaLeague();
  void elLoadPlayerMatches(userId);
  void elLoadPlayerPoMatches(userId);
}

// 2026-07-22: setka juftligidan ochilgan profil — reyting qatorisiz ham ishlaydi.
// (Setkadagi odam guruh reytingida bo'ladi, lekin himoya uchun minimal karta.)
function elOpenPlayerFromBracket(userId, side) {
  const rows = EL.rating || [];
  const row = rows.find(r => r.user_id === userId);
  if (row) { elOpenPlayerModal(userId); return; }
  // Reytingda topilmasa — setka ma'lumotidan minimal profil (nomi/klubi)
  const p = side || {};
  EL.viewPlayer = {
    user_id: userId, nickname: p.nickname, username: p.username,
    club_name: p.club_name, position: "—", group_number: "—",
    wins: "—", draws: "—", losses: "—", _minimal: true,
  };
  EL.viewPlayerMatches = null;
  EL.viewPlayerPoMatches = null;
  EL.section = "player";
  renderEuropaLeague();
  void elLoadPlayerMatches(userId);
  void elLoadPlayerPoMatches(userId);
}

async function elLoadPlayerMatches(userId) {
  try {
    const d = await apiFetch(`/el/matches/user/${userId}`);
    EL.viewPlayerMatches = d.matches || [];
  } catch (_) {
    EL.viewPlayerMatches = [];
  }
  if (EL.section === "player") renderEuropaLeague();
}

// Boshqa ishtirokchining play-off o'yinlari (faqat ko'rish — talab 3)
async function elLoadPlayerPoMatches(userId) {
  try {
    const d = await apiFetch(`/el/playoff/user/${userId}/matches`);
    EL.viewPlayerPoMatches = (d && d.started) ? (d.matches || []) : [];
  } catch (_) {
    EL.viewPlayerPoMatches = [];
  }
  if (EL.section === "player") renderEuropaLeague();
}

function elRenderPlayer() {
  const p = EL.viewPlayer;
  if (!p) return `<div class="card">${ET("el_player_404")}</div>`;

  const letter = (p.nickname || "?")[0].toUpperCase();

  return `
    <button class="btn el-back-link" id="el-player-back">
      ${ICON.get("back", 16)} Reytingga qaytish
    </button>

    <div class="card card--profile">
      <div class="profile-avatar" id="el-player-avatar" data-uid="${p.user_id}">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}</h2>
        <div class="el-rating-user${p.username ? " el-user-link" : ""}"
             ${p.username ? `data-el-tg="${escHtml(p.username)}"` : ""}>${p.username ? "@" + escHtml(p.username) : "—"}${prizeStarsHtml(p)}</div>
        <span class="profile-league">${p.group_number ? `${ET("el_profile_phase")} · ${p.position}-o'rin` : ET("el_draw_pending")}</span>
      </div>
      <div class="profile-club-badge">${elClubBadge(p.club_name, 44)}</div>
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
        <span class="stat-card-label">${ET("el_losses")}</span>
      </div>
    </div>

    <div class="section-label">O'YINLAR</div>
    ${elRenderPlayerMatches()}
    ${elRenderPlayerPoMatches()}`;
}

// Play-off o'yinlari bloki — faqat play-off boshlangan va o'yin bo'lsa ko'rinadi (talab 3)
function elRenderPlayerPoMatches() {
  const ms = EL.viewPlayerPoMatches;
  if (ms === null) return "";                 // hali yuklanmoqda — jim (guruh o'yinlari yetarli)
  if (!ms.length) return "";                  // play-off yo'q — blok umuman ko'rsatilmaydi
  return `
    <div class="section-label" style="margin-top:16px">PLAY-OFF O'YINLARI</div>
    <div class="matches-list">${ms.map(elRenderPlayerPoItem).join("")}</div>`;
}

// Play-off o'yin kartasi — faqat ko'rish (tugmasiz). elpoLegLabel/elClubBadge qayta ishlatiladi (DRY).
function elRenderPlayerPoItem(m) {
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const label = (typeof elpoLegLabel === "function")
    ? elpoLegLabel(m) : (m.round + (m.leg ? " · " + m.leg + "-o'yin" : ""));
  const center = `
    <span class="el-mc-logo">${elClubBadge(m.p1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="el-mc-logo">${elClubBadge(m.p2_club, 26)}</span>`;

  let statusCls = "status--pending", statusText = "KUTILMOQDA";
  if (m.status === "confirmed") { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }
  else if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }

  // 2-o'yinda 1-o'yin hisobi (agregat konteksti) — elpoMyMatchItem bilan bir xil
  const ctx = (m.leg === 2 && m.other_leg_score1 !== null && m.other_leg_score1 !== undefined)
    ? `<div class="el-po-ctx">1-o'yin: ${m.other_leg_score1} : ${m.other_leg_score2}</div>` : "";

  return `
    <div class="el-match-wrap">
      <div class="el-match-head">
        <span class="el-match-round">${escHtml(label)}</span><span class="el-match-id">#${m.id}</span>
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="el-match-body">
        <div class="match-center">${center}</div>
      </div>
      ${ctx}
    </div>`;
}

// Boshqa o'yinchining o'yinlari — faqat ko'rish (tugmasiz)
function elRenderPlayerMatches() {
  const ms = EL.viewPlayerMatches;
  if (ms === null) return `<div class="wc-loading-row">${ET("el_loading")}</div>`;
  if (!ms.length) return `<div class="wc-loading-row">${ET("el_no_matches_short")}</div>`;

  return `<div class="matches-list">${ms.map(elRenderPlayerMatchItem).join("")}</div>`;
}

function elRenderPlayerMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const center = `
    <span class="el-mc-logo">${elClubBadge(m.player1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="el-mc-logo">${elClubBadge(m.player2_club, 26)}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "confirmed") { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }
  else if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }

  return `
    <div class="el-match-wrap">
      <div class="el-match-head">
        <span class="el-match-round">${m.matchday}-tur</span><span class="el-match-id">#${m.id}</span>
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="el-match-body">
        <div class="match-center">${center}</div>
      </div>
    </div>`;
}

function elBindPlayer(root) {
  const back = root.querySelector("#el-player-back");
  if (back) back.addEventListener("click", () => {
    EL.section = "rating";
    renderEuropaLeague();
  });

  // Username'ga bosilsa — raqib Telegram chati
  const tg = root.querySelector("[data-el-tg]");
  if (tg) tg.addEventListener("click", () => {
    const uname = tg.dataset.elTg.replace(/^@/, "");
    const link = `https://t.me/${uname}`;
    const w = window.Telegram?.WebApp;
    if (w?.openTelegramLink) { try { w.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); } }
    else window.open(link, "_blank");
  });

  const box = root.querySelector("#el-player-avatar");
  if (!box) return;
  const img = new Image();
  img.src = `${API_BASE}/players/${box.dataset.uid}/photo`;
  img.alt = "";
  img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};
}
