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
  CL.section = "player";
  renderChampionsLeague();
  void clLoadPlayerMatches(userId);
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

function clRenderPlayer() {
  const p = CL.viewPlayer;
  if (!p) return `<div class="card">Ishtirokchi topilmadi.</div>`;

  const letter = (p.nickname || "?")[0].toUpperCase();

  return `
    <button class="btn cl-back-link" id="cl-player-back">
      ${ICON.get("back", 16)} Reytingga qaytish
    </button>

    <div class="card card--profile">
      <div class="profile-avatar" id="cl-player-avatar" data-uid="${p.user_id}">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}</h2>
        <div class="cl-rating-user">${p.username ? "@" + escHtml(p.username) : "—"}</div>
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
        <span class="stat-card-label">Mag'lubiyat</span>
      </div>
    </div>

    <div class="section-label">O'YINLAR</div>
    ${clRenderPlayerMatches()}`;
}

// Boshqa o'yinchining o'yinlari — faqat ko'rish (tugmasiz)
function clRenderPlayerMatches() {
  const ms = CL.viewPlayerMatches;
  if (ms === null) return `<div class="wc-loading-row">Yuklanmoqda…</div>`;
  if (!ms.length) return `<div class="wc-loading-row">O'yinlar yo'q.</div>`;

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
        <span class="cl-match-round">${m.matchday}-tur</span>
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

  const box = root.querySelector("#cl-player-avatar");
  if (!box) return;
  const img = new Image();
  img.src = `${API_BASE}/players/${box.dataset.uid}/photo`;
  img.alt = "";
  img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};
}
