// ============================================================
//  cl_player.js — Reytingdagi ishtirokchiga bosilganda ochiladigan PROFIL modali.
//
//  Ma'lumot manbai: CL.rating (GET /cl/rating/{n} javobi) — yangi so'rov yo'q
//  (qoida #24/#49: ortiqcha zapros qilinmaydi). Avatar: /players/{id}/photo.
//  Global: CL, escHtml, clClubBadge (cl.js), API_BASE, ICON.
// ============================================================

function clOpenPlayerModal(userId) {
  const rows = CL.rating || [];   // /cl/rating/{n} → massiv
  const idx = rows.findIndex(r => r.user_id === userId);
  if (idx < 0) return;
  const p = rows[idx];

  let modal = document.getElementById("modal-cl-player");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-cl-player";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }

  const letter = (p.nickname || "?")[0].toUpperCase();
  const gd = p.goal_difference > 0 ? `+${p.goal_difference}` : p.goal_difference;

  modal.innerHTML = `
    <div class="modal-box">
      <button class="modal-close" id="cl-pm-close">${ICON.get("close", 18)}</button>
      <div class="cl-pm-head">
        <div class="profile-avatar" id="cl-pm-avatar">${escHtml(letter)}</div>
        <div>
          <h2 class="profile-nickname">${escHtml(p.nickname || "Ishtirokchi")}</h2>
          <div class="cl-rating-user">${p.username ? "@" + escHtml(p.username) : "—"}</div>
          <div style="font-size:12px;opacity:.7">
            ${escHtml(p.club_name || "Klub tanlanmagan")} · Guruh ${CL.ratingGroup} · ${idx + 1}-o'rin
          </div>
        </div>
        <div style="margin-left:auto">${clClubBadge(p.club_name, 44)}</div>
      </div>
      <div class="cl-pm-stats">
        <div class="cl-pm-stat"><b>${p.played}</b><span>O'YIN</span></div>
        <div class="cl-pm-stat"><b>${p.wins}</b><span>G'ALABA</span></div>
        <div class="cl-pm-stat"><b>${p.draws}</b><span>DURANG</span></div>
        <div class="cl-pm-stat"><b>${p.losses}</b><span>MAG'LUB</span></div>
        <div class="cl-pm-stat"><b>${p.goals_for}</b><span>GOL</span></div>
        <div class="cl-pm-stat"><b>${p.goals_against}</b><span>O'TKAZGAN</span></div>
        <div class="cl-pm-stat"><b>${gd}</b><span>FARQ</span></div>
        <div class="cl-pm-stat"><b>${p.points}</b><span>OCHKO</span></div>
      </div>
    </div>`;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  // Avatar rasmi (bo'lmasa — bosh harf qoladi, qoida #40)
  const box = document.getElementById("cl-pm-avatar");
  const img = new Image();
  img.src = `${API_BASE}/players/${userId}/photo`;
  img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:50%;";
  img.onload = () => { box.textContent = ""; box.appendChild(img); };
  img.onerror = () => {};

  const close = () => modal.classList.add("hidden");
  document.getElementById("cl-pm-close").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
}
