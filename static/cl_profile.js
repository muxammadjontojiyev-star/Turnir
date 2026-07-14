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

// ---- PROFIL: kartochka + pastda o'yinlarim ----
function clRenderProfile() {
  const p = CL.profile;
  if (!p) return `<div class="card">Profil yuklanmadi. Qayta urinib ko'ring.</div>`;

  if (!p.registered) {
    return `<div class="card">Siz Chempionlar ligasi ishtirokchisi emassiz.</div>`;
  }

  const letter = (p.nickname || "?")[0].toUpperCase();
  const avatar = `
    <div class="cl-avatar" id="cl-avatar">${escHtml(letter)}</div>`;

  const groupLine = p.group_number
    ? `Guruh ${p.group_number}${p.position ? ` · ${p.position}-o'rin` : ""}`
    : `Qur'a kutilmoqda`;

  const stats = p.group_number ? `
    <div class="cl-stats">
      <div><b>${p.played}</b><span>O</span></div>
      <div><b>${p.wins}</b><span>G'</span></div>
      <div><b>${p.draws}</b><span>D</span></div>
      <div><b>${p.losses}</b><span>M</span></div>
      <div><b>${p.goal_difference > 0 ? "+" : ""}${p.goal_difference}</b><span>GF</span></div>
      <div><b>${p.points}</b><span>Ochko</span></div>
    </div>` : "";

  return `
    <div class="card cl-profile-card">
      <div style="display:flex;align-items:center;gap:12px">
        ${avatar}
        <div>
          <b style="font-size:16px">${escHtml(p.nickname || "Ishtirokchi")}</b>
          <div style="font-size:12.5px;opacity:.75">${escHtml(p.club_name || "Klub tanlanmagan")}</div>
          <div style="font-size:12px;opacity:.65">${escHtml(groupLine)}</div>
        </div>
      </div>
      ${stats}
    </div>
    <div style="font-size:13px;opacity:.75;margin:12px 2px 6px"><b>O'yinlarim</b></div>
    ${clRenderMatches()}`;
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
    <div class="card">
      <b>Sovrinlarim</b>
      <div style="font-size:12.5px;opacity:.7;margin-top:4px">
        Liga va Jahon chempionati bo'yicha qo'lga kiritilgan sovrinlar.
      </div>
    </div>
    <div id="cl-prizes-section">
      <div class="card" style="opacity:.7">Yuklanmoqda…</div>
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
      box.innerHTML = `<div class="card" style="opacity:.75">Hozircha sovrinlar yo'q.</div>`;
    }
  } catch (_) {
    box.innerHTML = `<div class="card">Sovrinlarni yuklab bo'lmadi.</div>`;
  }
}
