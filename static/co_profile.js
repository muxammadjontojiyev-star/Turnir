// ============================================================
//  co_profile.js — KL "Profil" va "Sovrinlar" sahifalari
//  co.js ning davomi (qoida 21: fayl 200-300 qatordan oshmasin).
//  Global: CO, apiFetch, escHtml, showToast, API_BASE, loadPrizesInto (api.js)
//  Backend: GET /co/profile, GET /players/{user_id}/photo, GET /users/{id}/prizes
// ============================================================

async function coLoadProfile() {
  try {
    // 2026-07-23: yulduzchalar profil bilan birga yangilanadi (yangi kubok ★ ko'rinsin)
    const [prof] = await Promise.all([
      apiFetch("/co/profile"),
      (typeof loadPrizeStars === "function") ? loadPrizeStars() : Promise.resolve(),
    ]);
    CO.profile = prof;
  } catch (_) {
    CO.profile = null;
  }
  await coLoadMatches();   // Profil ostida o'yinlar ko'rinadi (renderni o'zi chaqiradi)
}

// ---- PROFIL: WC naqshi (card--profile + stats-grid + matches-list) ----
function coRenderProfile() {
  const p = CO.profile;
  if (!p) return `<div class="card">${COT("co_profile_failed")}</div>`;
  if (!p.registered) {
    return `<div class="card">${COT("co_not_participant")}</div>`;
  }

  const letter = (p.nickname || "?")[0].toUpperCase();
  const groupLabel = p.group_number
    ? (p.position ? `${COT("co_profile_phase")} · #${p.position}` : COT("co_profile_phase"))
    : COT("co_draw_pending");
  const pos = p.position ? `#${p.position}` : "—";

  return `
    <div class="card card--profile">
      <div class="profile-avatar" id="co-avatar">${escHtml(letter)}</div>
      <div class="profile-info">
        <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}${prizeStarsHtml({ user_id: p.user_id })}</h2>
        <span class="profile-league">${escHtml(groupLabel)}</span>
      </div>
      <div class="profile-club-badge">${coClubBadge(p.club_name, 44)}</div>
    </div>
    ${typeof adminContactsBoxHtml === "function" ? adminContactsBoxHtml("co") : ""}

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
        <span class="stat-card-label">${COT("co_losses")}</span>
      </div>
    </div>

    <div class="section-label">MENING O'YINLARIM</div>
    ${coRenderMatches()}

    <div id="co-po-my-box"></div>`;
}

// Avatar rasmini yuklash (bo'lmasa — harf qoladi, qoida 40)
function coBindProfile(root) {
  const box = root.querySelector("#co-avatar");
  const uid = CO.profile && CO.profile.user_id;
  if (!box || !uid) return;
  const img = new Image();
  img.src = `${API_BASE}/players/${uid}/photo`;
  img.alt = "";
  img.style.cssText = "width:56px;height:56px;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};   // Rasm yo'q — bosh harf qoladi
}

// ---- SOVRINLAR ----
function coRenderPrizes() {
  return `
    <div class="co-trophy-hero">
      <img src="co-trophy.png?v=2" alt="${COT("co_cup_title")}" class="co-trophy-img">
      <div class="co-trophy-caption">${COT("co_cup_title")}</div>
      <div id="co-cup-holder" class="co-trophy-sub">${COT("co_cup_sub")}</div>
    </div>
    <div class="section-label">MENING SOVRINLARIM</div>
    <div id="co-prizes-section">
      <div class="card" style="opacity:.7">${COT("co_loading")}</div>
    </div>`;
}

// 2026-07-23 (talab 1): kubok egasi useri — mavsum yakunlangach saqlangan
// co_cup egasi, yakunlanmagan bo'lsa joriy setka chempioni. Topilmasa —
// asl "Final g'olibi sovrin egasi bo'ladi" matni qoladi.
async function coLoadCupHolder() {
  const box = document.getElementById("co-cup-holder");
  if (!box) return;
  try {
    const d = await apiFetch("/co/cup-holder");
    const h = d && d.holder;
    if (!h) return;                       // hali egasi yo'q — asl matn qoladi
    const who = h.username ? "@" + h.username : (h.nickname || "—");
    const seasonPart = h.season ? ` · ${h.season}-mavsum` : "";
    box.innerHTML = `
      <span class="co-cup-holder-name">🏆 ${escHtml(who)}</span>
      <span class="co-cup-holder-sub">${d.finalized ? "kubok egasi" : "chempion"}${escHtml(seasonPart)}</span>`;
  } catch (_) {
    /* xato — asl matn qoladi (qoida #40: jim qolmaymiz, lekin bu ikkilamchi ma'lumot) */
  }
}

async function coBindPrizes() {
  void coLoadCupHolder();          // 2026-07-23: kubok egasi useri (talab 1)
  const uid = CO.profile && CO.profile.user_id;
  const box = document.getElementById("co-prizes-section");
  if (!box) return;
  if (!uid) {
    box.innerHTML = `<div class="card">Ma'lumot yuklanmadi.</div>`;
    return;
  }
  try {
    box.innerHTML = "";
    await loadPrizesInto(uid, "co-prizes-section");   // api.js — DRY (qoida 26)
    if (!box.innerHTML.trim()) {
      box.innerHTML = `<div class="card" style="opacity:.75">${COT("co_no_prizes")}</div>`;
    }
  } catch (_) {
    box.innerHTML = `<div class="card">${COT("co_prizes_failed")}</div>`;
  }
}
