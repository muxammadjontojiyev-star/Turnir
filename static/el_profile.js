// ============================================================
//  el_profile.js — YeL "Profil" va "Sovrinlar" sahifalari
//  el.js ning davomi (qoida 21: fayl 200-300 qatordan oshmasin).
//  Global: EL, apiFetch, escHtml, showToast, API_BASE, loadPrizesInto (api.js)
//  Backend: GET /el/profile, GET /players/{user_id}/photo, GET /users/{id}/prizes
// ============================================================

async function elLoadProfile() {
  try {
    // 2026-07-23: yulduzchalar profil bilan birga yangilanadi (yangi kubok ★ ko'rinsin)
    const [prof] = await Promise.all([
      apiFetch("/el/profile"),
      (typeof loadPrizeStars === "function") ? loadPrizeStars() : Promise.resolve(),
    ]);
    EL.profile = prof;
  } catch (_) {
    EL.profile = null;
  }
  await elLoadMatches();   // Profil ostida o'yinlar ko'rinadi (renderni o'zi chaqiradi)
}

// ---- PROFIL: WC naqshi (card--profile + stats-grid + matches-list) ----
function elRenderProfile() {
  const p = EL.profile;
  if (!p) return `<div class="card">${ET("el_profile_failed")}</div>`;
  if (!p.registered) {
    return `<div class="card">${ET("el_not_participant")}</div>`;
  }

  const letter = (p.nickname || "?")[0].toUpperCase();
  const groupLabel = p.group_number
    ? (p.position ? `${ET("el_profile_phase")} · #${p.position}` : ET("el_profile_phase"))
    : ET("el_draw_pending");
  const pos = p.position ? `#${p.position}` : "—";

  return `
    <div class="card card--profile">
      <div class="profile-avatar" id="el-avatar">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}${prizeStarsHtml({ user_id: p.user_id })}</h2>
        <span class="profile-league">${escHtml(groupLabel)}</span>
      </div>
      <div class="profile-club-badge">${elClubBadge(p.club_name, 44)}</div>
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
        <span class="stat-card-label">${ET("el_losses")}</span>
      </div>
    </div>

    <div class="section-label">MENING O'YINLARIM</div>
    ${elRenderMatches()}

    <div id="el-po-my-box"></div>`;
}

// Avatar rasmini yuklash (bo'lmasa — harf qoladi, qoida 40)
function elBindProfile(root) {
  const box = root.querySelector("#el-avatar");
  const uid = EL.profile && EL.profile.user_id;
  if (!box || !uid) return;
  const img = new Image();
  img.src = `${API_BASE}/players/${uid}/photo`;
  img.alt = "";
  img.style.cssText = "width:56px;height:56px;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};   // Rasm yo'q — bosh harf qoladi
}

// ---- SOVRINLAR ----
function elRenderPrizes() {
  return `
    <div class="el-trophy-hero">
      <img src="el-trophy.png" alt="${ET("el_cup_title")}" class="el-trophy-img">
      <div class="el-trophy-caption">${ET("el_cup_title")}</div>
      <div id="el-cup-holder" class="el-trophy-sub">${ET("el_cup_sub")}</div>
    </div>
    <div class="section-label">MENING SOVRINLARIM</div>
    <div id="el-prizes-section">
      <div class="card" style="opacity:.7">${ET("el_loading")}</div>
    </div>`;
}

// 2026-07-23 (talab 1): kubok egasi useri — mavsum yakunlangach saqlangan
// el_cup egasi, yakunlanmagan bo'lsa joriy setka chempioni. Topilmasa —
// asl "Final g'olibi sovrin egasi bo'ladi" matni qoladi.
async function elLoadCupHolder() {
  const box = document.getElementById("el-cup-holder");
  if (!box) return;
  try {
    const d = await apiFetch("/el/cup-holder");
    const h = d && d.holder;
    if (!h) return;                       // hali egasi yo'q — asl matn qoladi
    const who = h.username ? "@" + h.username : (h.nickname || "—");
    const seasonPart = h.season ? ` · ${h.season}-mavsum` : "";
    box.innerHTML = `
      <span class="el-cup-holder-name">🏆 ${escHtml(who)}</span>
      <span class="el-cup-holder-sub">${d.finalized ? "kubok egasi" : "chempion"}${escHtml(seasonPart)}</span>`;
  } catch (_) {
    /* xato — asl matn qoladi (qoida #40: jim qolmaymiz, lekin bu ikkilamchi ma'lumot) */
  }
}

async function elBindPrizes() {
  void elLoadCupHolder();          // 2026-07-23: kubok egasi useri (talab 1)
  const uid = EL.profile && EL.profile.user_id;
  const box = document.getElementById("el-prizes-section");
  if (!box) return;
  if (!uid) {
    box.innerHTML = `<div class="card">Ma'lumot yuklanmadi.</div>`;
    return;
  }
  try {
    box.innerHTML = "";
    await loadPrizesInto(uid, "el-prizes-section");   // api.js — DRY (qoida 26)
    if (!box.innerHTML.trim()) {
      box.innerHTML = `<div class="card" style="opacity:.75">${ET("el_no_prizes")}</div>`;
    }
  } catch (_) {
    box.innerHTML = `<div class="card">${ET("el_prizes_failed")}</div>`;
  }
}
