// ============================================================
//  division.js — Divizion (3-tab) ekrani
//  Alohida ekran (cl.js/worldcup.js naqshi). Mavjud kodga TEGMAYDI.
//  Sahifalar: Asosiy | Reyting | Profil | Sovrinlar
//
//  Bog'liqliklar (global): APP, apiFetch (api.js), escHtml (api.js), showToast,
//  hideModeSelect, showModeSelect.
//  Backend: /div/status, /div/register, /div/rating,
//           /div/match/submit-result, /div/match/confirm, /div/chat/{id}
// ============================================================

const DIV = {
  section: "home",   // home | rating | profile | prizes | admin
  status: null,      // /div/status javobi
  rating: [],
  adminMatches: [],  // admin panel ro'yxati
};

// ---- Kirish nuqtasi ----
function showDivision() {
  if (typeof hideModeSelect === "function") hideModeSelect();
  document.querySelector(".bottom-nav")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));

  let root = document.getElementById("div-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "div-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  DIV.section = "home";
  void divLoadStatus();
}

function exitDivision() {
  if (typeof closeWebChat === "function") closeWebChat();
  const root = document.getElementById("div-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function divNavigate(section) {
  DIV.section = section;
  renderDivision();
  if (section === "rating") void divLoadRating();
  if (section === "home" || section === "profile") void divLoadStatus();
  if (section === "admin") void divLoadAdminMatches();
}

async function divLoadStatus() {
  try {
    DIV.status = await apiFetch("/div/status");
  } catch (_) { DIV.status = null; }
  renderDivision();
}

async function divLoadRating() {
  try {
    const d = await apiFetch("/div/rating");
    DIV.rating = d.rating || [];
    DIV.ratingMeId = d.me_id;
  } catch (_) { DIV.rating = []; }
  renderDivision();
}

// ---- RENDER ----
function renderDivision() {
  const root = document.getElementById("div-root");
  if (!root) return;

  let body = "";
  if (DIV.section === "home") body = divRenderHome();
  else if (DIV.section === "rating") body = divRenderRating();
  else if (DIV.section === "profile") body = divRenderProfile();
  else if (DIV.section === "admin") body = divRenderAdmin();
  else body = divRenderPrizes();

  const adminNav = DIV.status?.is_admin ? `
      <button class="wc-nav-item ${DIV.section === "admin" ? "active" : ""}" data-div-tab="admin">
        <span class="nav-icon" data-icon="clipboard"></span>
        <span class="nav-label">Admin</span>
      </button>` : "";

  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="div-back-btn">←</button>
      <div class="wc-header-title">Divizion</div>
    </div>
    <div class="wc-body" style="padding-bottom:90px;">${body}</div>
    <nav class="wc-nav">
      <button class="wc-nav-item ${DIV.section === "home" ? "active" : ""}" data-div-tab="home">
        <span class="nav-icon" data-icon="home"></span>
        <span class="nav-label">Asosiy</span>
      </button>
      <button class="wc-nav-item ${DIV.section === "rating" ? "active" : ""}" data-div-tab="rating">
        <span class="nav-icon" data-icon="trophy"></span>
        <span class="nav-label">Reyting</span>
      </button>
      <button class="wc-nav-item ${DIV.section === "profile" ? "active" : ""}" data-div-tab="profile">
        <span class="nav-icon" data-icon="user"></span>
        <span class="nav-label">Profil</span>
      </button>
      <button class="wc-nav-item ${DIV.section === "prizes" ? "active" : ""}" data-div-tab="prizes">
        <span class="nav-icon" data-icon="gift"></span>
        <span class="nav-label">Sovrinlar</span>
      </button>${adminNav}
    </nav>
  `;

  if (typeof applyIcons === "function") applyIcons(root);
  document.getElementById("div-back-btn").addEventListener("click", exitDivision);
  root.querySelectorAll("[data-div-tab]").forEach(b =>
    b.addEventListener("click", () => divNavigate(b.dataset.divTab)));
  divBindSectionEvents(root);
}


// ---- ASOSIY: ro'yxat oynasi + bugungi ro'yxat ----
function divRenderHome() {
  const s = DIV.status;
  if (!s) return `<div class="card">Ma'lumot yuklanmadi. Qayta urinib ko'ring.</div>`;

  const win = s.window || {};
  let regBlock;
  if (s.me_registered) {
    regBlock = `<div class="card" style="border-color:rgba(49,208,170,.5)">✅ Siz bugungi ro'yxatdasiz. Qur'a soat 19:00 dan keyin o'tkaziladi va natija telegram orqali yuboriladi.</div>`;
  } else if (win.open) {
    regBlock = `
      <div class="card">
        <b>Ro'yxat ochiq (17:00–19:00)</b>
        <div style="font-size:12.5px;opacity:.75;margin:4px 0 10px">Hozir: ${escHtml(win.now || "")}. Qur'a 19:00 dan keyin, o'yin deadline'i — 23:30.</div>
        <button class="btn btn--primary" id="div-btn-register" style="width:100%">📝 Ro'yxatdan o'tish</button>
      </div>`;
  } else {
    regBlock = `<div class="card">⏳ Ro'yxat yopiq. Har kuni <b>17:00–19:00</b> (Toshkent) oralig'ida ochiladi. Hozir: ${escHtml(win.now || "")}.</div>`;
  }

  const regs = s.registrations || [];
  const list = regs.length
    ? regs.map((r, i) => `
        <div class="match-item">
          <b>${i + 1}. ${escHtml(r.nickname || "Ishtirokchi")}</b>
          ${r.username ? `<span style="font-size:12px;opacity:.7">@${escHtml(r.username)}</span>` : ""}
        </div>`).join("")
    : `<div style="font-size:13px;opacity:.7">Bugun hali hech kim ro'yxatdan o'tmagan.</div>`;

  return `${regBlock}
    <div class="card"><b>Bugungi ishtirokchilar (${regs.length})</b><div style="margin-top:8px">${list}</div></div>`;
}

// ---- REYTING: umumiy achko jadvali (+15/+10/-10) ----
function divRenderRating() {
  const rows = (DIV.rating || []).map((p, i) => {
    const me = DIV.ratingMeId && p.user_id === DIV.ratingMeId ? ` class="is-me"` : "";
    return `
      <tr${me}>
        <td class="rank-${i + 1}">${i + 1}</td>
        <td>${escHtml(p.nickname || "")}</td>
        <td>${p.played}</td><td>${p.wins}/${p.draws}/${p.losses}</td>
        <td><b>${p.points}</b></td>
      </tr>`;
  }).join("");
  return `
    <div class="card card--table">
      <div style="font-size:12px;opacity:.7;margin-bottom:8px">G'alaba +15 · Durang +10 · Mag'lubiyat −10</div>
      <table class="rating-table">
        <thead><tr><th>#</th><th>O'yinchi</th><th>O</th><th>G/D/M</th><th>Achko</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5">Hozircha natijalar yo'q</td></tr>`}</tbody>
      </table>
    </div>`;
}

// ---- PROFIL: liga uslubida (statistika + o'yinlar tarixi + raqib) ----
function divStatusLabelShort(st) {
  return ({ pending: "KUTILMOQDA", awaiting_confirmation: "TASDIQ KUTILMOQDA",
            admin_pending: "ADMIN TASDIG'I", confirmed: "TASDIQLANDI" })[st] || st;
}

function divRenderProfile() {
  const s = DIV.status;
  if (!s) return `<div class="card">Ma'lumot yuklanmadi.</div>`;

  const st = s.stats || { wins: 0, draws: 0, losses: 0, win_rate: 0 };

  // 1) Bugungi raqib kartasi (raqib — hisob — men)
  let oppCard = "";
  const m = s.my_match;
  if (m && m.is_bye) {
    oppCard = `<div class="card" style="border-color:rgba(245,197,66,.5)">🎉 Bugun ishtirokchilar soni toq bo'lgani uchun sizga <b>avtomatik g'alaba (+15 achko)</b> berildi!</div>`;
  } else if (m) {
    const opp = m.opponent || {};
    const oppInitial = (opp.nickname || "?").charAt(0).toUpperCase();
    // Raqib telegram rasmi (bo'lmasa — ism harfi). Liga bilan bir xil endpoint.
    const oppPhoto = opp.user_id
      ? `<img src="${API_BASE}/players/${opp.user_id}/photo" alt=""
             style="width:52px;height:52px;border-radius:50%;object-fit:cover"
             onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
         <div style="display:none;width:52px;height:52px;border-radius:50%;
             align-items:center;justify-content:center;font-size:22px;font-weight:800;
             background:linear-gradient(140deg,#7c5cff,#31d0aa);color:#fff">${escHtml(oppInitial)}</div>`
      : `<div style="width:52px;height:52px;border-radius:50%;display:flex;
             align-items:center;justify-content:center;font-size:22px;font-weight:800;
             background:linear-gradient(140deg,#7c5cff,#31d0aa);color:#fff">${escHtml(oppInitial)}</div>`;

    // Hisob tartibi: RAQIB — hisob — MEN (2-talab)
    const myName = (m.player1_id === s.me_id) ? m.player1_name : m.player2_name;
    let oppScore = "—", myScore = "—";
    if (m.score1 !== null && m.score1 !== undefined) {
      const p1IsMe = (m.player1_id === s.me_id);
      myScore = p1IsMe ? m.score1 : m.score2;
      oppScore = p1IsMe ? m.score2 : m.score1;
    }

    let actions = "";
    if (m.status === "pending") {
      actions = `<button class="btn btn--primary" id="div-btn-open-result" style="width:100%;margin-top:10px">Natija kiritish</button>`;
    } else if (m.status === "awaiting_confirmation") {
      actions = (m.submitted_by !== s.me_id)
        ? `<div style="display:flex;gap:8px;margin-top:10px">
             <button class="btn btn--primary" id="div-btn-confirm" style="flex:1">✅ Tasdiqlash</button>
             <button class="btn btn--ghost" id="div-btn-reject" style="flex:1">❌ Rad etish</button>
           </div>`
        : `<div style="font-size:12px;opacity:.7;margin-top:8px">Raqib tasdig'i kutilmoqda…</div>`;
    } else if (m.status === "admin_pending") {
      actions = `<div style="font-size:12px;opacity:.7;margin-top:8px">Admin tasdig'i kutilmoqda…</div>`;
    } else if (m.status === "confirmed") {
      actions = `<div style="font-size:12.5px;margin-top:8px">✅ Natija tasdiqlangan.</div>`;
    }

    oppCard = `
      <div class="card">
        <div style="display:flex;align-items:center;gap:12px">
          ${oppPhoto}
          <div style="min-width:0;flex:1">
            <div style="font-size:12px;opacity:.65">Bugungi raqibingiz</div>
            <div style="font-size:17px;font-weight:800">${escHtml(opp.nickname || "Ishtirokchi")}</div>
            ${opp.username ? `<div style="font-size:12px;opacity:.7">@${escHtml(opp.username)}</div>` : ""}
          </div>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;gap:14px;margin:12px 0;font-weight:800">
          <span style="opacity:.8;font-size:13px">${escHtml(opp.nickname || "Raqib")}</span>
          <span style="font-size:22px">${oppScore} : ${myScore}</span>
          <span style="opacity:.8;font-size:13px">${escHtml(myName || "Siz")}</span>
        </div>
        <button class="btn btn--ghost" id="div-btn-opponent" style="width:100%">👤 Raqib bilan bog'lanish</button>
        ${actions}
      </div>`;
  } else {
    oppCard = `<div class="card">Bugun sizda o'yin yo'q. Qur'a natijasi 19:00 dan keyin shu yerda ko'rinadi (ro'yxatdan o'tgan bo'lsangiz).</div>`;
  }

  // 2) STATISTIKA — liga uslubi (o'rin o'rniga G'alaba foizi)
  const statsGrid = `
    <div class="section-label">STATISTIKA</div>
    <div class="stats-grid">
      <div class="stat-card stat-card--primary">
        <span class="stat-card-value neon-cyan">${st.win_rate}%</span>
        <span class="stat-card-label">G'alaba foizi</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-cyan">${st.wins}</span>
        <span class="stat-card-label">G'alaba</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value">${st.draws}</span>
        <span class="stat-card-label">Durang</span>
      </div>
      <div class="stat-card">
        <span class="stat-card-value neon-red">${st.losses}</span>
        <span class="stat-card-label">Mag'lubiyat</span>
      </div>
    </div>`;

  // 3) MENING O'YINLARIM — tarix
  const hist = s.history || [];
  const histRows = hist.map((h, i) => {
    if (h.is_bye) {
      return `<div class="match-item">
        <span style="opacity:.6">${i + 1}</span>
        <b style="flex:1;text-align:center">🎉 Avto g'alaba (toq)</b>
        <span class="status-badge status--confirmed">+15</span>
      </div>`;
    }
    const hasScore = (h.my_score !== null && h.my_score !== undefined);
    const score = hasScore ? `${h.opp_score} : ${h.my_score}` : "— : —";
    return `<div class="match-item">
      <span style="opacity:.6">${i + 1}</span>
      <b style="flex:1">${escHtml(h.opp_name || "Raqib")}</b>
      <span style="font-weight:800;margin:0 8px">${score}</span>
      <span class="status-badge status--${h.status === "confirmed" ? "confirmed" : "awaiting"}" style="font-size:10px">${divStatusLabelShort(h.status)}</span>
    </div>`;
  }).join("");
  const historyBlock = `
    <div class="section-label">MENING O'YINLARIM</div>
    ${hist.length ? `<div class="card">${histRows}</div>`
                  : `<div class="card" style="opacity:.7;font-size:13px">Hozircha o'yinlar yo'q.</div>`}`;

  return oppCard + statsGrid + historyBlock;
}

// Liga uslubidagi raqib VS-oynasi: "Chatni ochish" (webapp chat) + "Raqib chatiga yozish" (t.me)
function divOpenOpponentModal() {
  const s = DIV.status;
  const m = s?.my_match;
  if (!m || m.is_bye) return;
  const opp = m.opponent || {};
  const t = APP.t || {};

  let modal = document.getElementById("modal-div-opponent");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-div-opponent";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  // Bot chati doim mavjud (bye bo'lmasa) — foydalanuvchi so'roviga ko'ra
  const webChatBtn = `<button class="opp-chat-btn opp-webchat-btn" id="div-opp-webchat">${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}</button>`;
  const tgBtn = (opp.username || opp.telegram_id)
    ? `<button class="opp-chat-btn" id="div-opp-tg">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;

  const myName = (m.player1_id === s.me_id) ? m.player1_name : m.player2_name;
  const myUsername = (m.player1_id === s.me_id) ? m.player1_username : m.player2_username;
  const myUserId = s.me_id;
  // Telegram rasm (bo'lmasa — ism harfi). Liga bilan bir xil /players/{id}/photo.
  const avatarHtml = (userId, name) => {
    const initial = (name || "?").charAt(0).toUpperCase();
    const fallback = `<div class="div-vs-avatar-fallback">${escHtml(initial)}</div>`;
    if (!userId) return fallback;
    return `<img class="div-vs-avatar" src="${API_BASE}/players/${userId}/photo" alt=""
              onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
            <div class="div-vs-avatar-fallback" style="display:none">${escHtml(initial)}</div>`;
  };
  const side = (userId, name, username) => `
    <div class="opp-side">
      <div class="div-vs-avatar-wrap">${avatarHtml(userId, name)}</div>
      <div class="opp-club">${escHtml(name || "—")}</div>
      <div class="opp-user">${username ? "@" + escHtml(username) : "—"}</div>
    </div>`;

  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="div-opp-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">
        ${side(myUserId, myName, myUsername)}
        <div class="opp-vs-sep">VS</div>
        ${side(opp.user_id, opp.nickname, opp.username)}
      </div>
      ${webChatBtn}
      ${tgBtn}
    </div>`;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  document.getElementById("div-opp-close").addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });

  document.getElementById("div-opp-webchat")?.addEventListener("click", () => {
    modal.classList.add("hidden");
    // Liga webchat modalining o'zi — faqat Divizion API prefiksi bilan (DRY)
    openWebChat(m.id, opp.nickname || "Raqib", "/div/matches");
  });
  document.getElementById("div-opp-tg")?.addEventListener("click", () => {
    const tg = window.Telegram?.WebApp;
    if (opp.username) {
      const link = `https://t.me/${String(opp.username).replace(/^@/, "")}`;
      if (tg?.openTelegramLink) { try { tg.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); } }
      else window.open(link, "_blank");
    } else if (opp.telegram_id) {
      const link = `tg://user?id=${opp.telegram_id}`;
      if (tg?.openLink) { try { tg.openLink(link); } catch (_) { window.open(link, "_blank"); } }
      else window.open(link, "_blank");
    }
  });
}

// Liga uslubidagi natija kiritish modali (score-input-row markup)
function divOpenResultModal() {
  const s = DIV.status;
  const m = s?.my_match;
  if (!m || m.is_bye || m.status !== "pending") return;
  const t = APP.t || {};
  const opp = m.opponent || {};
  const myName = (m.player1_id === s.me_id) ? m.player1_name : m.player2_name;

  let modal = document.getElementById("modal-div-result");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-div-result";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">${escHtml(t.submit_result || "Natija kiritish")}</div>
      <div class="score-input-row">
        <div class="score-input-group">
          <div class="score-logo-input">
            <span class="div-avatar-mini" title="${escHtml(myName || "Siz")}">${escHtml((myName || "S").charAt(0).toUpperCase())}</span>
            <input id="div-input-score1" class="score-input" type="number" min="0" max="99" value="0" />
          </div>
        </div>
        <span class="score-separator">:</span>
        <div class="score-input-group">
          <div class="score-logo-input">
            <input id="div-input-score2" class="score-input" type="number" min="0" max="99" value="0" />
            <span class="div-avatar-mini div-avatar-mini--opp" title="${escHtml(opp.nickname || "Raqib")}">${escHtml((opp.nickname || "R").charAt(0).toUpperCase())}</span>
          </div>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:12px;opacity:.7;margin-top:6px">
        <span>${escHtml(myName || "Siz")}</span><span>${escHtml(opp.nickname || "Raqib")}</span>
      </div>
      <div class="modal-actions">
        <button class="btn btn--ghost" id="div-result-cancel">${escHtml(t.cancel || "Bekor")}</button>
        <button class="btn btn--primary btn--glow" id="div-result-submit">${escHtml(t.submit || "Yuborish")}</button>
      </div>
    </div>`;
  modal.classList.remove("hidden");

  const close = () => modal.classList.add("hidden");
  document.getElementById("div-result-cancel").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
  document.getElementById("div-result-submit").addEventListener("click", async (e) => {
    const s1 = Number(document.getElementById("div-input-score1").value || 0);
    const s2 = Number(document.getElementById("div-input-score2").value || 0);
    // Hisob doim player1:player2 tartibida saqlanadi — men player2 bo'lsam almashtiramiz
    const [a, b] = (m.player1_id === s.me_id) ? [s1, s2] : [s2, s1];
    e.target.disabled = true;
    try {
      await apiFetch(`/div/match/submit-result?match_id=${m.id}&score1=${a}&score2=${b}`, { method: "POST" });
      close();
      showToast("Natija kiritildi ✅");
      await divLoadStatus();
    } catch (err) {
      e.target.disabled = false;
      showToast("Xato: " + err.message);
    }
  });
}

// ---- SOVRINLAR: hozircha bo'sh (rasm keyin qo'shiladi) ----
function divRenderPrizes() {
  return `<div class="card" style="text-align:center;padding:26px 16px">
    <div style="font-size:34px">🎁</div>
    <div style="font-weight:700;margin-top:6px">Divizion sovrinlari</div>
    <div style="font-size:13px;opacity:.7;margin-top:4px">Tez orada e'lon qilinadi.</div>
  </div>`;
}

// ---- Eventlar ----
function divBindSectionEvents(root) {
  root.querySelector("#div-btn-register")?.addEventListener("click", async (e) => {
    e.target.disabled = true; // ikki marta bosishdan himoya (qoida #38/#40)
    try {
      await apiFetch("/div/register", { method: "POST" });
      showToast("Ro'yxatdan o'tdingiz ✅");
      await divLoadStatus();
    } catch (err) {
      e.target.disabled = false;
      showToast(err.message === "window_closed"
        ? "Ro'yxat vaqti tugagan (17:00–19:00)" : "Xato: " + err.message);
    }
  });

  root.querySelector("#div-btn-opponent")?.addEventListener("click", divOpenOpponentModal);
  root.querySelector("#div-btn-open-result")?.addEventListener("click", divOpenResultModal);

  const act = async (accept) => {
    const m = DIV.status?.my_match;
    if (!m) return;
    try {
      await apiFetch(`/div/match/confirm?match_id=${m.id}&accept=${accept}`, { method: "POST" });
      showToast(accept ? "Tasdiqlandi ✅" : "Rad etildi");
      await divLoadStatus();
    } catch (err) {
      showToast("Xato: " + err.message);
    }
  };
  root.querySelector("#div-btn-confirm")?.addEventListener("click", () => act(true));
  root.querySelector("#div-btn-reject")?.addEventListener("click", () => act(false));

  // Admin panel eventlari
  root.querySelectorAll("[data-div-admin-edit]").forEach(b =>
    b.addEventListener("click", () => divAdminEdit(Number(b.dataset.divAdminEdit))));
  root.querySelectorAll("[data-div-admin-cancel]").forEach(b =>
    b.addEventListener("click", async () => {
      const id = Number(b.dataset.divAdminCancel);
      if (!confirm("Natija bekor qilinsinmi? O'yin qayta ochiladi va ishtirokchilar natijani yana kiritishi mumkin bo'ladi.")) return;
      try {
        await apiFetch(`/div/admin/match/cancel?match_id=${id}`, { method: "POST" });
        showToast("Natija bekor qilindi — o'yin qayta ochildi 🔄");
        await divLoadAdminMatches();
      } catch (err) { showToast("Xato: " + err.message); }
    }));

  // Katta hisob (admin_pending) qarori — liga admin oqimi kabi
  const resolveBig = async (id, accept) => {
    try {
      await apiFetch(`/div/admin/match/resolve?match_id=${id}&accept=${accept}`, { method: "POST" });
      showToast(accept ? "Natija tasdiqlandi ✅" : "Rad etildi — o'yin qayta ochildi 🔄");
      await divLoadAdminMatches();
    } catch (err) { showToast("Xato: " + err.message); }
  };
  root.querySelectorAll("[data-div-admin-approve]").forEach(b =>
    b.addEventListener("click", () => resolveBig(Number(b.dataset.divAdminApprove), true)));
  root.querySelectorAll("[data-div-admin-reject]").forEach(b =>
    b.addEventListener("click", () => resolveBig(Number(b.dataset.divAdminReject), false)));
}

// ---- ADMIN PANEL (faqat bosh admin) ----
async function divLoadAdminMatches() {
  try {
    const d = await apiFetch("/div/admin/matches");
    DIV.adminMatches = d.matches || [];
  } catch (_) { DIV.adminMatches = []; }
  renderDivision();
}

function divAdminStatusLabel(st) {
  return ({ pending: "⏳ Kutilmoqda", awaiting_confirmation: "🤝 Tasdiq kutilmoqda",
            confirmed: "✅ Tasdiqlangan", admin_pending: "👑 Katta hisob — admin qarori" })[st] || st;
}

function divRenderAdmin() {
  const ms = DIV.adminMatches || [];
  if (!ms.length) {
    return `<div class="card">Bugun o'yinlar yo'q (qur'a hali o'tkazilmagan bo'lishi mumkin).</div>`;
  }
  return `<div class="card" style="font-size:12.5px;opacity:.75">Liga admin paneli kabi: ✏️ natijani o'zgartirish (darhol tasdiqlanadi), 🚫 natijani bekor qilish (o'yin qayta ochiladi — ishtirokchilar yana kiritadi), katta hisobda ✅/❌ qaror.</div>` +
    ms.map(m => {
      const p2 = m.player2_id ? escHtml(m.player2_name || "") : "<i>(toq — avto g'alaba)</i>";
      const hasScore = (m.score1 !== null && m.score1 !== undefined);
      const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";
      const isBye = !m.player2_id;

      let buttons = "";
      if (!isBye) {
        if (m.status === "admin_pending") {
          // Liga admin oqimi: katta hisob — tasdiqlash yoki rad etish
          buttons = `
            <button class="btn btn--primary" data-div-admin-approve="${m.id}" style="flex:1">✅ Tasdiqlash</button>
            <button class="btn btn--ghost" data-div-admin-reject="${m.id}" style="flex:1">❌ Rad etish</button>`;
        } else {
          buttons = `<button class="btn btn--primary" data-div-admin-edit="${m.id}" style="flex:1">✏️ Natijani o'zgartirish</button>`;
          if (hasScore || m.status !== "pending") {
            buttons += `<button class="btn btn--ghost" data-div-admin-cancel="${m.id}" style="flex:1">🚫 Natijani bekor qilish</button>`;
          }
        }
      }
      return `
        <div class="card">
          <div style="font-size:12px;opacity:.65">#${m.id} · ${divAdminStatusLabel(m.status)}</div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;gap:8px">
            <b style="min-width:0;overflow:hidden;text-overflow:ellipsis">${escHtml(m.player1_name || "")}</b>
            <span style="font-weight:800;white-space:nowrap">${score}</span>
            <b style="min-width:0;overflow:hidden;text-overflow:ellipsis;text-align:right">${p2}</b>
          </div>
          ${buttons ? `<div style="display:flex;gap:8px;margin-top:10px">${buttons}</div>` : ""}
        </div>`;
    }).join("");
}

// Admin: natijani o'rnatish/tuzatish modali (liga natija modali uslubida)
function divAdminEdit(matchId) {
  const m = (DIV.adminMatches || []).find(x => x.id === matchId);
  if (!m) return;
  let modal = document.getElementById("modal-div-admin-result");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-div-admin-result";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">✏️ Natijani o'zgartirish</div>
      <div style="display:flex;justify-content:space-between;font-size:12.5px;opacity:.75;margin-bottom:6px">
        <span>${escHtml(m.player1_name || "")}</span><span>${escHtml(m.player2_name || "")}</span>
      </div>
      <div class="score-input-row">
        <div class="score-input-group">
          <input id="div-admin-score1" class="score-input" type="number" min="0" max="99" value="${m.score1 ?? 0}" />
        </div>
        <span class="score-separator">:</span>
        <div class="score-input-group">
          <input id="div-admin-score2" class="score-input" type="number" min="0" max="99" value="${m.score2 ?? 0}" />
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn--ghost" id="div-admin-cancel-btn">Bekor</button>
        <button class="btn btn--primary btn--glow" id="div-admin-save-btn">Saqlash</button>
      </div>
    </div>`;
  modal.classList.remove("hidden");
  const close = () => modal.classList.add("hidden");
  document.getElementById("div-admin-cancel-btn").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });
  document.getElementById("div-admin-save-btn").addEventListener("click", async (e) => {
    const s1 = Number(document.getElementById("div-admin-score1").value || 0);
    const s2 = Number(document.getElementById("div-admin-score2").value || 0);
    e.target.disabled = true;
    try {
      await apiFetch(`/div/admin/match/set-result?match_id=${matchId}&score1=${s1}&score2=${s2}`, { method: "POST" });
      close();
      showToast("Natija saqlandi ✅");
      await divLoadAdminMatches();
    } catch (err) {
      e.target.disabled = false;
      showToast("Xato: " + err.message);
    }
  });
}
