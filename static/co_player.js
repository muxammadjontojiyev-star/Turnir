// ============================================================
//  co_player.js — Reytingdagi ishtirokchiga bosilganda ochiladigan PROFIL SAHIFASI.
//  Modal emas: CO.section = "player". Profil bilan bir xil ko'rinish, lekin:
//    - GOLLAR/ochko bloki YO'Q (reytingda ko'rinadi — 1-punkt)
//    - o'yinlar faqat KO'RISH uchun (💬/Natija tugmalarisiz)
//  Ma'lumot: CO.viewPlayer (reyting qatoridan) + /co/matches/user/{id} (o'yinlar).
// ============================================================

function coOpenPlayerModal(userId) {
  const rows = CO.rating || [];
  const row = rows.find(r => r.user_id === userId);
  if (!row) return;
  CO.viewPlayer = { ...row, position: row._pos, group_number: row._group };
  CO.viewPlayerMatches = null;
  CO.viewPlayerPoMatches = null;   // 2026-07-22: play-off o'yinlari (talab 3)
  CO.section = "player";
  renderConferenceLeague();
  void coLoadPlayerMatches(userId);
  void coLoadPlayerPoMatches(userId);
}

// 2026-07-22: setka juftligidan ochilgan profil — reyting qatorisiz ham ishlaydi.
// (Setkadagi odam guruh reytingida bo'ladi, lekin himoya uchun minimal karta.)
function coOpenPlayerFromBracket(userId, side) {
  const rows = CO.rating || [];
  const row = rows.find(r => r.user_id === userId);
  if (row) { coOpenPlayerModal(userId); return; }
  // Reytingda topilmasa — setka ma'lumotidan minimal profil (nomi/klubi)
  const p = side || {};
  CO.viewPlayer = {
    user_id: userId, nickname: p.nickname, username: p.username,
    club_name: p.club_name, position: "—", group_number: "—",
    wins: "—", draws: "—", losses: "—", _minimal: true,
  };
  CO.viewPlayerMatches = null;
  CO.viewPlayerPoMatches = null;
  CO.section = "player";
  renderConferenceLeague();
  void coLoadPlayerMatches(userId);
  void coLoadPlayerPoMatches(userId);
}

async function coLoadPlayerMatches(userId) {
  try {
    const d = await apiFetch(`/co/matches/user/${userId}`);
    CO.viewPlayerMatches = d.matches || [];
  } catch (_) {
    CO.viewPlayerMatches = [];
  }
  if (CO.section === "player") renderConferenceLeague();
}

// Boshqa ishtirokchining play-off o'yinlari (faqat ko'rish — talab 3)
async function coLoadPlayerPoMatches(userId) {
  try {
    const d = await apiFetch(`/co/playoff/user/${userId}/matches`);
    CO.viewPlayerPoMatches = (d && d.started) ? (d.matches || []) : [];
  } catch (_) {
    CO.viewPlayerPoMatches = [];
  }
  if (CO.section === "player") renderConferenceLeague();
}

function coRenderPlayer() {
  const p = CO.viewPlayer;
  if (!p) return `<div class="card">${COT("co_player_404")}</div>`;

  const letter = (p.nickname || "?")[0].toUpperCase();

  return `
    <button class="btn co-back-link" id="co-player-back">
      ${ICON.get("back", 16)} Reytingga qaytish
    </button>

    <div class="card card--profile">
      <div class="profile-avatar" id="co-player-avatar" data-uid="${p.user_id}">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}</h2>
        <div class="co-rating-user${p.username ? " co-user-link" : ""}"
             ${p.username ? `data-co-tg="${escHtml(p.username)}"` : ""}>${p.username ? "@" + escHtml(p.username) : "—"}${prizeStarsHtml(p)}</div>
        <span class="profile-league">${p.group_number ? `${COT("co_profile_phase")} · ${p.position}-o'rin` : COT("co_draw_pending")}</span>
      </div>
      <div class="profile-club-badge">${coClubBadge(p.club_name, 44)}</div>
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
        <span class="stat-card-label">${COT("co_losses")}</span>
      </div>
    </div>

    <div class="section-label">O'YINLAR</div>
    ${coRenderPlayerMatches()}
    ${coRenderPlayerPoMatches()}`;
}

// Play-off o'yinlari bloki — faqat play-off boshlangan va o'yin bo'lsa ko'rinadi (talab 3)
function coRenderPlayerPoMatches() {
  const ms = CO.viewPlayerPoMatches;
  if (ms === null) return "";                 // hali yuklanmoqda — jim (guruh o'yinlari yetarli)
  if (!ms.length) return "";                  // play-off yo'q — blok umuman ko'rsatilmaydi
  return `
    <div class="section-label" style="margin-top:16px">PLAY-OFF O'YINLARI</div>
    <div class="matches-list">${ms.map(coRenderPlayerPoItem).join("")}</div>`;
}

// Play-off o'yin kartasi — faqat ko'rish (tugmasiz). copoLegLabel/coClubBadge qayta ishlatiladi (DRY).
function coRenderPlayerPoItem(m) {
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const label = (typeof copoLegLabel === "function")
    ? copoLegLabel(m) : (m.round + (m.leg ? " · " + m.leg + "-o'yin" : ""));
  const center = `
    <span class="co-mc-logo">${coClubBadge(m.p1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="co-mc-logo">${coClubBadge(m.p2_club, 26)}</span>`;

  let statusCls = "status--pending", statusText = "KUTILMOQDA";
  if (m.status === "confirmed") { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }
  else if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }

  // 2-o'yinda 1-o'yin hisobi (agregat konteksti) — copoMyMatchItem bilan bir xil
  const ctx = (m.leg === 2 && m.other_leg_score1 !== null && m.other_leg_score1 !== undefined)
    ? `<div class="co-po-ctx">1-o'yin: ${m.other_leg_score1} : ${m.other_leg_score2}</div>` : "";

  return `
    <div class="co-match-wrap">
      <div class="co-match-head">
        <span class="co-match-round">${escHtml(label)}</span><span class="co-match-id">#${m.id}</span>
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="co-match-body">
        <div class="match-center">${center}</div>
      </div>
      ${ctx}
    </div>`;
}

// Boshqa o'yinchining o'yinlari — faqat ko'rish (tugmasiz)
function coRenderPlayerMatches() {
  const ms = CO.viewPlayerMatches;
  if (ms === null) return `<div class="wc-loading-row">${COT("co_loading")}</div>`;
  if (!ms.length) return `<div class="wc-loading-row">${COT("co_no_matches_short")}</div>`;

  return `<div class="matches-list">${ms.map(coRenderPlayerMatchItem).join("")}</div>`;
}

function coRenderPlayerMatchItem(m) {
  const hasScore = (m.score1 !== null && m.score1 !== undefined);
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
  const center = `
    <span class="co-mc-logo">${coClubBadge(m.player1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="co-mc-logo">${coClubBadge(m.player2_club, 26)}</span>`;

  let statusCls = "status--pending";
  let statusText = "KUTILMOQDA";
  if (m.status === "confirmed") { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }
  else if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }

  return `
    <div class="co-match-wrap">
      <div class="co-match-head">
        <span class="co-match-round">${m.matchday}-tur</span><span class="co-match-id">#${m.id}</span>
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="co-match-body">
        <div class="match-center">${center}</div>
      </div>
    </div>`;
}

function coBindPlayer(root) {
  const back = root.querySelector("#co-player-back");
  if (back) back.addEventListener("click", () => {
    CO.section = "rating";
    renderConferenceLeague();
  });

  // Username'ga bosilsa — raqib Telegram chati
  const tg = root.querySelector("[data-co-tg]");
  if (tg) tg.addEventListener("click", () => {
    const uname = tg.dataset.coTg.replace(/^@/, "");
    const link = `https://t.me/${uname}`;
    const w = window.Telegram?.WebApp;
    if (w?.openTelegramLink) { try { w.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); } }
    else window.open(link, "_blank");
  });

  const box = root.querySelector("#co-player-avatar");
  if (!box) return;
  const img = new Image();
  img.src = `${API_BASE}/players/${box.dataset.uid}/photo`;
  img.alt = "";
  img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};
}
