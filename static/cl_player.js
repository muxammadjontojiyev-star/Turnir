// ============================================================
//  cl_player.js — Reytingdagi ishtirokchiga bosilganda ochiladigan PROFIL SAHIFASI.
//
//  Modal emas: CL.section = "player" bo'ladi va Profil tabi bilan bir xil
//  ko'rinish (card--profile + STATISTIKA) to'liq ekranda chiziladi (qoida #42).
//  Ma'lumot manbai: CL.rating (yangi so'rov yo'q — qoida #49). Avatar: /players/{id}/photo.
//  Global: CL, escHtml, clClubBadge (cl.js), API_BASE, ICON, renderChampionsLeague.
// ============================================================

function clOpenPlayerModal(userId) {
  const rows = CL.rating || [];
  const idx = rows.findIndex(r => r.user_id === userId);
  if (idx < 0) return;
  CL.viewPlayer = { ...rows[idx], position: idx + 1, group_number: CL.ratingGroup };
  CL.section = "player";
  renderChampionsLeague();
}

function clRenderPlayer() {
  const p = CL.viewPlayer;
  if (!p) return `<div class="card">Ishtirokchi topilmadi.</div>`;

  const letter = (p.nickname || "?")[0].toUpperCase();
  const gd = p.goal_difference > 0 ? `+${p.goal_difference}` : p.goal_difference;

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

    <div class="section-label">GOLLAR</div>
    <div class="stats-grid">
      <div class="stat-card">
        <span class="stat-card-value">${p.played}</span>
        <span class="stat-card-label">O'yin</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-cyan">${p.goals_for}</span>
        <span class="stat-card-label">Urilgan</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value">${p.goals_against}</span>
        <span class="stat-card-label">O'tkazgan</span>
      </div>
      <div class="stat-card stat-card--primary">
        <span class="stat-card-value neon-cyan">${p.points}</span>
        <span class="stat-card-label">Ochko (${gd})</span>
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
