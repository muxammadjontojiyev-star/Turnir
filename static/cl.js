// ============================================================
//  cl.js — Chempionlar ligasi (ChL) rejimi
//  Alohida ekran (worldcup.js naqshi). Mavjud liga/WC kodiga TEGMAYDI.
//  Rejim tanlash -> showChampionsLeague() shu yerda.
//
//  Bog'liqliklar (global): APP, apiFetch (api.js), escHtml (app.js),
//  showToast, hideModeSelect, showModeSelect.
//  Backend: GET /cl/qualifiers, /cl/groups, /cl/rating/{n}, /cl/matches/my,
//           POST /cl/match/submit-result, /cl/match/confirm
// ============================================================

const CL = {
  section: "home",     // home | rating | matches
  groups: null,        // /cl/groups javobi
  qualifiers: null,    // /cl/qualifiers javobi (qur'agacha ko'rsatish uchun)
  ratingGroup: 1,      // Reytingda tanlangan guruh (1..8)
  rating: [],
  myMatches: [],
  meParticipant: false,
};

// ---- Kirish nuqtasi ----
function showChampionsLeague() {
  if (typeof hideModeSelect === "function") hideModeSelect();
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));

  let root = document.getElementById("cl-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "cl-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  CL.section = "home";
  void clLoadThenRender();
}

function exitChampionsLeague() {
  const root = document.getElementById("cl-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function clNavigate(section) {
  CL.section = section;
  renderChampionsLeague();
  if (section === "rating") void clLoadRating();
  if (section === "matches") void clLoadMatches();
}

async function clLoadThenRender() {
  try {
    CL.groups = await apiFetch("/cl/groups");
    CL.meParticipant = !!CL.groups.me_participant;
  } catch (_) { CL.groups = null; }
  try {
    CL.qualifiers = await apiFetch("/cl/qualifiers");
  } catch (_) { CL.qualifiers = null; }
  renderChampionsLeague();
}

async function clLoadRating() {
  try {
    const d = await apiFetch(`/cl/rating/${CL.ratingGroup}`);
    CL.rating = d.rating || [];
  } catch (_) { CL.rating = []; }
  renderChampionsLeague();
}

async function clLoadMatches() {
  try {
    const d = await apiFetch("/cl/matches/my");
    CL.myMatches = d.matches || [];
    CL._myId = d.me_id ?? null;
  } catch (_) { CL.myMatches = []; CL._myId = null; }
  renderChampionsLeague();
}

// ---- RENDER ----
function renderChampionsLeague() {
  const root = document.getElementById("cl-root");
  if (!root) return;

  let body = "";
  if (CL.section === "home") body = clRenderHome();
  else if (CL.section === "rating") body = clRenderRating();
  else body = clRenderMatches();

  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="cl-back-btn">←</button>
      <div class="wc-header-title">⭐ Chempionlar ligasi</div>
    </div>
    <div class="wc-tabs" style="display:flex;gap:8px;padding:10px 14px;">
      ${clTabBtn("home", "Guruhlar")}
      ${clTabBtn("rating", "Reyting")}
      ${clTabBtn("matches", "O'yinlarim")}
    </div>
    <div class="cl-body" style="padding:0 14px 90px;">${body}</div>
  `;

  document.getElementById("cl-back-btn").addEventListener("click", exitChampionsLeague);
  root.querySelectorAll("[data-cl-tab]").forEach(b =>
    b.addEventListener("click", () => clNavigate(b.dataset.clTab)));
  clBindSectionEvents(root);
}

function clTabBtn(section, label) {
  const active = CL.section === section ? " active" : "";
  return `<button class="tab-btn${active}" data-cl-tab="${section}">${label}</button>`;
}

// ---- HOME: guruhlar yoki kvalifikantlar ----
function clRenderHome() {
  const g = CL.groups;
  if (!g) return `<div class="card">Ma'lumot yuklanmadi. Qayta urinib ko'ring.</div>`;

  const meBadge = CL.meParticipant
    ? `<div class="card" style="border-color:rgba(245,197,66,.5)">🎟 Siz Chempionlar ligasi ishtirokchisisiz!</div>`
    : "";

  if (!g.drawn) {
    // Qur'agacha: kvalifikantlar ro'yxati (1-mavsum natijasi bo'yicha)
    const qs = (CL.qualifiers && CL.qualifiers.qualifiers) || [];
    if (!qs.length) {
      return `${meBadge}<div class="card">Chempionlar ligasi kvalifikatsiyasi hali aniqlanmagan. Liga mavsumi yakunlangach, 5 liga bo'yicha top-6 va eng yaxshi 2 ta 7-o'rin (jami 32) shu yerda ko'rinadi.</div>`;
    }
    const rows = qs.map(q => `
      <div class="match-item">
        <div>
          <b>${escHtml(q.nickname || "Ishtirokchi")}</b>
          <div style="font-size:12px;opacity:.7">${escHtml(q.league_name || "")} — ${q.position}-o'rin${q.qualified_via === "best7" ? " (eng yaxshi 7-o'rin)" : ""}</div>
        </div>
        <div style="font-size:12px;opacity:.8">${q.points} ochko</div>
      </div>`).join("");
    return `${meBadge}
      <div class="card"><b>Kvalifikantlar (${qs.length}/32)</b>
      <div style="font-size:12.5px;opacity:.75;margin:4px 0 10px">Qur'a hali o'tkazilmagan. Guruhlar qur'adan keyin ko'rinadi.</div>
      ${rows}</div>`;
  }

  // Qur'adan keyin: 8 guruh
  const byGroup = {};
  for (const p of g.participants) {
    if (!p.group_number) continue;
    (byGroup[p.group_number] ||= []).push(p);
  }
  const cards = Object.keys(byGroup).sort((a, b) => a - b).map(n => {
    const items = byGroup[n].map(p => `
      <div class="match-item">
        <b>${escHtml(p.nickname || "")}</b>
        <span style="font-size:12px;opacity:.75">${escHtml(p.club_name || "")}</span>
      </div>`).join("");
    return `<div class="card"><b>Guruh ${n}</b>${items}</div>`;
  }).join("");
  return meBadge + cards;
}

// ---- RATING ----
function clRenderRating() {
  let selector = `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;">`;
  for (let n = 1; n <= 8; n++) {
    const active = CL.ratingGroup === n ? " active" : "";
    selector += `<button class="tab-btn${active}" data-cl-group="${n}">G${n}</button>`;
  }
  selector += `</div>`;

  const rows = (CL.rating || []).map((p, i) => `
    <tr>
      <td class="rank-${i + 1}">${i + 1}</td>
      <td>${escHtml(p.nickname || "")}<div style="font-size:11px;opacity:.65">${escHtml(p.club_name || "")}</div></td>
      <td>${p.played}</td><td>${p.goal_difference > 0 ? "+" : ""}${p.goal_difference}</td>
      <td><b>${p.points}</b></td>
    </tr>`).join("");

  return `${selector}
    <div class="card card--table">
      <table class="rating-table">
        <thead><tr><th>#</th><th>O'yinchi</th><th>O</th><th>GF</th><th>Ochko</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5">Hozircha natijalar yo'q</td></tr>`}</tbody>
      </table>
    </div>`;
}

// ---- MATCHES ----
function clRenderMatches() {
  if (!CL.meParticipant) {
    return `<div class="card">Siz Chempionlar ligasi ishtirokchisi emassiz.</div>`;
  }
  const ms = CL.myMatches || [];
  if (!ms.length) {
    return `<div class="card">Hozircha o'yinlar yo'q (qur'a kutilmoqda).</div>`;
  }
  return ms.map(m => {
    const score = (m.score1 !== null && m.score1 !== undefined)
      ? `${m.score1} : ${m.score2}` : "— : —";
    let actions = "";
    if (m.status === "pending") {
      actions = `
        <div style="display:flex;gap:6px;align-items:center;margin-top:8px">
          <input class="score-input" id="cl-s1-${m.id}" type="number" min="0" value="0">
          <span>:</span>
          <input class="score-input" id="cl-s2-${m.id}" type="number" min="0" value="0">
          <button class="btn btn--primary" data-cl-submit="${m.id}">Kiritish</button>
        </div>`;
    } else if (m.status === "awaiting_confirmation") {
      actions = m.submitted_by && !clIsMe(m.submitted_by)
        ? `<div style="display:flex;gap:6px;margin-top:8px">
             <button class="btn btn--primary" data-cl-confirm="${m.id}">✅ Tasdiqlash</button>
             <button class="btn" data-cl-reject="${m.id}">❌ Rad etish</button>
           </div>`
        : `<div style="font-size:12px;opacity:.7;margin-top:6px">Raqib tasdig'i kutilmoqda…</div>`;
    } else if (m.status === "admin_pending") {
      actions = `<div style="font-size:12px;opacity:.7;margin-top:6px">Admin tasdig'i kutilmoqda…</div>`;
    }
    return `
      <div class="card">
        <div style="font-size:12px;opacity:.65">Guruh ${m.group_number} · ${m.matchday}-tur · ${clStatusLabel(m.status)}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px">
          <b>${escHtml(m.player1_name)}</b>
          <span style="font-weight:800">${score}</span>
          <b>${escHtml(m.player2_name)}</b>
        </div>
        ${actions}
      </div>`;
  }).join("");
}

function clIsMe(userId) {
  // me_id backend'dan keladi (/cl/matches/my) — taxmin qilinmaydi
  return CL._myId !== null && CL._myId !== undefined && userId === CL._myId;
}

function clStatusLabel(s) {
  return ({ pending: "Kutilmoqda", awaiting_confirmation: "Tasdiq kutilmoqda",
            confirmed: "Tasdiqlangan", admin_pending: "Admin tasdig'i" })[s] || s;
}

// ---- Eventlar ----
function clBindSectionEvents(root) {
  root.querySelectorAll("[data-cl-group]").forEach(b =>
    b.addEventListener("click", () => {
      CL.ratingGroup = Number(b.dataset.clGroup);
      void clLoadRating();
    }));

  root.querySelectorAll("[data-cl-submit]").forEach(b =>
    b.addEventListener("click", async () => {
      const id = b.dataset.clSubmit;
      const s1 = Number(document.getElementById(`cl-s1-${id}`).value || 0);
      const s2 = Number(document.getElementById(`cl-s2-${id}`).value || 0);
      b.disabled = true; // ikki marta bosishdan himoya (qoida #38/#40)
      try {
        await apiFetch(`/cl/match/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`, { method: "POST" });
        showToast("Natija kiritildi ✅");
        CL._myId = undefined;
        await clLoadMatches();
      } catch (e) {
        b.disabled = false;
        showToast("Xato: " + e.message);
      }
    }));

  const act = async (id, accept) => {
    try {
      await apiFetch(`/cl/match/confirm?match_id=${id}&accept=${accept}`, { method: "POST" });
      showToast(accept ? "Tasdiqlandi ✅" : "Rad etildi");
      CL._myId = undefined;
      await clLoadMatches();
    } catch (e) {
      showToast("Xato: " + e.message);
    }
  };
  root.querySelectorAll("[data-cl-confirm]").forEach(b =>
    b.addEventListener("click", () => act(b.dataset.clConfirm, true)));
  root.querySelectorAll("[data-cl-reject]").forEach(b =>
    b.addEventListener("click", () => act(b.dataset.clReject, false)));
}
