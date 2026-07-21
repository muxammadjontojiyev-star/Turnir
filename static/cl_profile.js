// ============================================================
//  cl_profile.js — ChL "Profil" va "Sovrinlar" sahifalari
//  cl.js ning davomi (qoida 21: fayl 200-300 qatordan oshmasin).
//  Global: CL, apiFetch, escHtml, showToast, API_BASE, loadPrizesInto (api.js)
//  Backend: GET /cl/profile, GET /players/{user_id}/photo, GET /users/{id}/prizes
// ============================================================

async function clLoadProfile() {
  try {
    CL.profile = await apiFetch("/cl/profile");
  } catch (_) {
    CL.profile = null;
  }
  await clLoadMatches();   // Profil ostida o'yinlar ko'rinadi (renderni o'zi chaqiradi)
}

// ---- PROFIL: WC naqshi (card--profile + stats-grid + matches-list) ----
function clRenderProfile() {
  const p = CL.profile;
  if (!p) return `<div class="card">${CT("cl_profile_failed")}</div>`;
  if (!p.registered) {
    return `<div class="card">${CT("cl_not_participant")}</div>`;
  }

  const letter = (p.nickname || "?")[0].toUpperCase();
  const groupLabel = p.group_number ? `Guruh ${p.group_number}` : CT("cl_draw_pending");
  const pos = p.position ? `#${p.position}` : "—";

  return `
    <div class="card card--profile">
      <div class="profile-avatar" id="cl-avatar">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}${prizeStarsHtml({ user_id: p.user_id })}</h2>
        <span class="profile-league">${escHtml(groupLabel)}</span>
      </div>
      <div class="profile-club-badge">${clClubBadge(p.club_name, 44)}</div>
    </div>

    <div class="section-label">STATISTIKA</div>
    <div class="stats-grid">
      <div class="stat-card stat-card--primary">
        <span class="stat-card-value neon-cyan">${pos}</span>
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

    <div class="section-label">MENING O'YINLARIM</div>
    ${clRenderMatches()}

    <div id="cl-po-my-box"></div>`;
}

// Avatar rasmini yuklash (bo'lmasa — harf qoladi, qoida 40)
function clBindProfile(root) {
  const box = root.querySelector("#cl-avatar");
  const uid = CL.profile && CL.profile.user_id;
  if (!box || !uid) return;
  const img = new Image();
  img.src = `${API_BASE}/players/${uid}/photo`;
  img.alt = "";
  img.style.cssText = "width:56px;height:56px;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};   // Rasm yo'q — bosh harf qoladi
}

// ---- SOVRINLAR ----
function clRenderPrizes() {
  return `
    <div class="cl-trophy-hero">
      <img src="cl-trophy.png" alt="${CT("cl_cup_title")}" class="cl-trophy-img">
      <div class="cl-trophy-caption">${CT("cl_cup_title")}</div>
      <div class="cl-trophy-sub">${CT("cl_cup_sub")}</div>
    </div>
    <div class="section-label">MENING SOVRINLARIM</div>
    <div id="cl-prizes-section">
      <div class="card" style="opacity:.7">${CT("cl_loading")}</div>
    </div>`;
}

async function clBindPrizes() {
  const uid = CL.profile && CL.profile.user_id;
  const box = document.getElementById("cl-prizes-section");
  if (!box) return;
  if (!uid) {
    box.innerHTML = `<div class="card">Ma'lumot yuklanmadi.</div>`;
    return;
  }
  try {
    box.innerHTML = "";
    await loadPrizesInto(uid, "cl-prizes-section");   // api.js — DRY (qoida 26)
    if (!box.innerHTML.trim()) {
      box.innerHTML = `<div class="card" style="opacity:.75">${CT("cl_no_prizes")}</div>`;
    }
  } catch (_) {
    box.innerHTML = `<div class="card">${CT("cl_prizes_failed")}</div>`;
  }
}
