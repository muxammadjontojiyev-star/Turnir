// ============================================================
//  cl_player.js — Reytingdagi ishtirokchiga bosilganda ochiladigan PROFIL SAHIFASI.
//  Modal emas: CL.section = "player". Profil bilan bir xil ko'rinish, lekin:
//    - GOLLAR/ochko bloki YO'Q (reytingda ko'rinadi — 1-punkt)
//    - o'yinlar faqat KO'RISH uchun (💬/Natija tugmalarisiz)
//  Ma'lumot: CL.viewPlayer (reyting qatoridan) + /cl/matches/user/{id} (o'yinlar).
// ============================================================

function clOpenPlayerModal(userId) {
  const rows = CL.rating || [];
  const row = rows.find(r => r.user_id === userId);
  if (!row) return;
  CL.viewPlayer = { ...row, position: row._pos, group_number: row._group };
  CL.viewPlayerMatches = null;
  CL.viewPlayerPoMatches = null;   // 2026-07-22: play-off o'yinlari (talab 3)
  CL.section = "player";
  renderChampionsLeague();
  void clLoadPlayerMatches(userId);
  void clLoadPlayerPoMatches(userId);
}

// 2026-07-22: setka juftligidan ochilgan profil — reyting qatorisiz ham ishlaydi.
// (Setkadagi odam guruh reytingida bo'ladi, lekin himoya uchun minimal karta.)
function clOpenPlayerFromBracket(userId, side) {
  const rows = CL.rating || [];
  const row = rows.find(r => r.user_id === userId);
  if (row) { clOpenPlayerModal(userId); return; }
  // Reytingda topilmasa — setka ma'lumotidan minimal profil (nomi/klubi)
  const p = side || {};
  CL.viewPlayer = {
    user_id: userId, nickname: p.nickname, username: p.username,
    club_name: p.club_name, position: "—", group_number: "—",
    wins: "—", draws: "—", losses: "—", _minimal: true,
  };
  CL.viewPlayerMatches = null;
  CL.viewPlayerPoMatches = null;
  CL.section = "player";
  renderChampionsLeague();
  void clLoadPlayerMatches(userId);
  void clLoadPlayerPoMatches(userId);
}

async function clLoadPlayerMatches(userId) {
  try {
    const d = await apiFetch(`/cl/matches/user/${userId}`);
    CL.viewPlayerMatches = d.matches || [];
  } catch (_) {
    CL.viewPlayerMatches = [];
  }
  if (CL.section === "player") renderChampionsLeague();
}

// Boshqa ishtirokchining play-off o'yinlari (faqat ko'rish — talab 3)
async function clLoadPlayerPoMatches(userId) {
  try {
    const d = await apiFetch(`/cl/playoff/user/${userId}/matches`);
    CL.viewPlayerPoMatches = (d && d.started) ? (d.matches || []) : [];
  } catch (_) {
    CL.viewPlayerPoMatches = [];
  }
  if (CL.section === "player") renderChampionsLeague();
}

function clRenderPlayer() {
  const p = CL.viewPlayer;
  if (!p) return `<div class="card">${CT("cl_player_404")}</div>`;

  const letter = (p.nickname || "?")[0].toUpperCase();

  return `
    <button class="btn cl-back-link" id="cl-player-back">
      ${ICON.get("back", 16)} Reytingga qaytish
    </button>

    <div class="card card--profile">
      <div class="profile-avatar" id="cl-player-avatar" data-uid="${p.user_id}">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}</h2>
        <div class="cl-rating-user${p.username ? " cl-user-link" : ""}"
             ${p.username ? `data-cl-tg="${escHtml(p.username)}"` : ""}>${p.username ? "@" + escHtml(p.username) : "—"}${prizeStarsHtml(p)}</div>
        <span class="profile-league">Guruh ${p.group_number} · ${p.position}-o'rin</span>
      </div>
      <div class="profile-club-badge">${clClubBadge(p.club_name, 44)}</div>
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
        <span class="stat-card-label">${CT("cl_losses")}</span>
      </div>
    </div>

    <div class="section-label">O'YINLAR</div>
    ${clRenderPlayerMatches()}
    ${clRenderPlayerPoMatches()}`;
}

// Play-off o'yinlari bloki — faqat play-off boshlangan va o'yin bo'lsa ko'rinadi (talab 3)
function clRenderPlayerPoMatches() {
  const ms = CL.viewPlayerPoMatches;
  if (ms === null) return "";                 // hali yuklanmoqda — jim (guruh o'yinlari yetarli)
  if (!ms.length) return "";                  // play-off yo'q — blok umuman ko'rsatilmaydi
  return `
    <div class="section-label" style="margin-top:16px">PLAY-OFF O'YINLARI</div>
    <div class="matches-list">${ms.map(clRenderPlayerPoItem).join("")}</div>`;
}

// Play-off o'yin kartasi — faqat ko'rish (tugmasiz). clpoLegLabel/clClubBadge qayta ishlatiladi (DRY).
function clRenderPlayerPoItem(m) {
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const label = (typeof clpoLegLabel === "function")
    ? clpoLegLabel(m) : (m.round + (m.leg ? " · " + m.leg + "-o'yin" : ""));
  const center = `
    <span class="cl-mc-logo">${clClubBadge(m.p1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="cl-mc-logo">${clClubBadge(m.p2_club, 26)}</span>`;

  let statusCls = "status--pending", statusText = "KUTILMOQDA";
  if (m.status === "confirmed") { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }
  else if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }

  // 2-o'yinda 1-o'yin hisobi (agregat konteksti) — clpoMyMatchItem bilan bir xil
  const ctx = (m.leg === 2 && m.other_leg_score1 !== null && m.other_leg_score1 !== undefined)
    ? `<div class="cl-po-ctx">1-o'yin: ${m.other_leg_score1} : ${m.other_leg_score2}</div>` : "";

  return `
    <div class="cl-match-wrap">
      <div class="cl-match-head">
        <span class="cl-match-round">${escHtml(label)}</span><span class="cl-match-id">#${m.id}</span>
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="cl-match-body">
        <div class="match-center">${center}</div>
      </div>
      ${ctx}
    </div>`;
}

// Boshqa o'yinchining o'yinlari — faqat ko'rish (tugmasiz)
function clRenderPlayerMatches() {
  const ms = CL.viewPlayerMatches;
  if (ms === null) return `<div class="wc-loading-row">${CT("cl_loading")}</div>`;
  if (!ms.length) return `<div class="wc-loading-row">${CT("cl_no_matches_short")}</div>`;

  return `<div class="matches-list">${ms.map(clRenderPlayerMatchItem).join("")}</div>`;
}

function clRenderPlayerMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const center = `
    <span class="cl-mc-logo">${clClubBadge(m.player1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="cl-mc-logo">${clClubBadge(m.player2_club, 26)}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "confirmed") { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }
  else if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }

  return `
    <div class="cl-match-wrap">
      <div class="cl-match-head">
        <span class="cl-match-round">${m.matchday}-tur</span><span class="cl-match-id">#${m.id}</span>
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="cl-match-body">
        <div class="match-center">${center}</div>
      </div>
    </div>`;
}

function clBindPlayer(root) {
  const back = root.querySelector("#cl-player-back");
  if (back) back.addEventListener("click", () => {
    CL.section = "rating";
    renderChampionsLeague();
  });

  // Username'ga bosilsa — raqib Telegram chati
  const tg = root.querySelector("[data-cl-tg]");
  if (tg) tg.addEventListener("click", () => {
    const uname = tg.dataset.clTg.replace(/^@/, "");
    const link = `https://t.me/${uname}`;
    const w = window.Telegram?.WebApp;
    if (w?.openTelegramLink) { try { w.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); } }
    else window.open(link, "_blank");
  });

  const box = root.querySelector("#cl-player-avatar");
  if (!box) return;
  const img = new Image();
  img.src = `${API_BASE}/players/${box.dataset.uid}/photo`;
  img.alt = "";
  img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};
}
