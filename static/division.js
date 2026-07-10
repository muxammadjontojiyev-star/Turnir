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
  section: "home",   // home | rating | profile | prizes
  status: null,      // /div/status javobi
  rating: [],
  chatMsgs: [],
  chatTimer: null,   // chat polling
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
  divStopChatPolling();
  const root = document.getElementById("div-root");
  if (root) root.classList.add("hidden");
  if (typeof showModeSelect === "function") showModeSelect();
}

function divNavigate(section) {
  if (section !== "profile") divStopChatPolling();
  DIV.section = section;
  renderDivision();
  if (section === "rating") void divLoadRating();
  if (section === "home" || section === "profile") void divLoadStatus();
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
  else body = divRenderPrizes();

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
      </button>
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

// ---- PROFIL: bugungi raqib + natija + chat ----
function divRenderProfile() {
  const s = DIV.status;
  if (!s) return `<div class="card">Ma'lumot yuklanmadi.</div>`;
  const m = s.my_match;
  if (!m) {
    return `<div class="card">Bugun sizda o'yin yo'q. Qur'a natijasi 19:00 dan keyin shu yerda ko'rinadi (ro'yxatdan o'tgan bo'lsangiz).</div>`;
  }
  if (m.is_bye) {
    return `<div class="card" style="border-color:rgba(245,197,66,.5)">🎉 Bugun ishtirokchilar soni toq bo'lgani uchun sizga <b>avtomatik g'alaba (+15 achko)</b> berildi!</div>`;
  }

  const opp = m.opponent || {};
  const initial = (opp.nickname || "?").charAt(0).toUpperCase();
  const tgLink = opp.username
    ? `<a class="btn" href="https://t.me/${escHtml(opp.username)}" target="_blank">✈️ Telegram chat</a>`
    : `<div style="font-size:12px;opacity:.7">Raqibning telegram username'i yo'q — bot chatidan foydalaning.</div>`;

  // Natija bloki (holatga qarab)
  const score = (m.score1 !== null && m.score1 !== undefined) ? `${m.score1} : ${m.score2}` : "— : —";
  let resultBlock = "";
  if (m.status === "pending") {
    resultBlock = `
      <div style="display:flex;gap:6px;align-items:center;margin-top:10px">
        <input class="score-input" id="div-s1" type="number" min="0" value="0">
        <span>:</span>
        <input class="score-input" id="div-s2" type="number" min="0" value="0">
        <button class="btn btn--primary" id="div-btn-submit">Natija kiritish</button>
      </div>
      <div style="font-size:11.5px;opacity:.65;margin-top:6px">Hisob: siz (${escHtml(divMyName(m))}) : raqib. Deadline — 23:30.</div>`;
  } else if (m.status === "awaiting_confirmation") {
    resultBlock = (m.submitted_by !== s.me_id)
      ? `<div style="display:flex;gap:6px;margin-top:10px">
           <button class="btn btn--primary" id="div-btn-confirm">✅ Tasdiqlash</button>
           <button class="btn" id="div-btn-reject">❌ Rad etish</button>
         </div>`
      : `<div style="font-size:12px;opacity:.7;margin-top:8px">Raqib tasdig'i kutilmoqda…</div>`;
  } else if (m.status === "admin_pending") {
    resultBlock = `<div style="font-size:12px;opacity:.7;margin-top:8px">Admin tasdig'i kutilmoqda…</div>`;
  } else if (m.status === "confirmed") {
    resultBlock = `<div style="font-size:12.5px;margin-top:8px">✅ Natija tasdiqlangan.</div>`;
  }

  // Bot chati
  const msgs = (DIV.chatMsgs || []).map(msg => {
    const mine = msg.sender_id === s.me_id;
    return `<div style="text-align:${mine ? "right" : "left"};margin:4px 0">
      <span style="display:inline-block;max-width:80%;padding:6px 10px;border-radius:12px;
        background:${mine ? "rgba(124,92,255,.35)" : "rgba(255,255,255,.08)"};font-size:13px">
        ${escHtml(msg.text)}</span></div>`;
  }).join("");

  return `
    <div class="card card--profile">
      <div style="display:flex;align-items:center;gap:12px">
        <div class="profile-avatar" style="width:52px;height:52px;border-radius:50%;
          display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;
          background:linear-gradient(140deg,#7c5cff,#31d0aa);color:#fff">${escHtml(initial)}</div>
        <div>
          <div style="font-size:12px;opacity:.65">Bugungi raqibingiz</div>
          <div style="font-size:17px;font-weight:800">${escHtml(opp.nickname || "Ishtirokchi")}</div>
          ${opp.username ? `<div style="font-size:12px;opacity:.7">@${escHtml(opp.username)}</div>` : ""}
        </div>
      </div>
      <div style="text-align:center;font-size:22px;font-weight:800;margin:12px 0">${score}</div>
      ${resultBlock}
      <div style="margin-top:10px">${tgLink}</div>
    </div>
    <div class="card">
      <b>💬 Bot chati</b>
      <div id="div-chat-box" style="max-height:220px;overflow-y:auto;margin:8px 0">${msgs || `<div style="font-size:12.5px;opacity:.6">Hozircha xabarlar yo'q. Raqibingizga yozing!</div>`}</div>
      <div style="display:flex;gap:6px">
        <input class="modal-input" id="div-chat-input" placeholder="Xabar yozing…" maxlength="500" style="flex:1">
        <button class="btn btn--primary" id="div-chat-send">➤</button>
      </div>
    </div>`;
}

function divMyName(m) {
  const s = DIV.status;
  return m.player1_id === s.me_id ? (m.player1_name || "siz") : (m.player2_name || "siz");
}

// ---- SOVRINLAR: hozircha bo'sh (rasm keyin qo'shiladi) ----
function divRenderPrizes() {
  return `<div class="card" style="text-align:center;padding:26px 16px">
    <div style="font-size:34px">🎁</div>
    <div style="font-weight:700;margin-top:6px">Divizion sovrinlari</div>
    <div style="font-size:13px;opacity:.7;margin-top:4px">Tez orada e'lon qilinadi.</div>
  </div>`;
}

// ---- Chat polling (profil ochiq bo'lsa har 5s) ----
async function divLoadChat() {
  const m = DIV.status?.my_match;
  if (!m || m.is_bye) return;
  try {
    const d = await apiFetch(`/div/chat/${m.id}`);
    const changed = JSON.stringify(d.messages) !== JSON.stringify(DIV.chatMsgs);
    DIV.chatMsgs = d.messages || [];
    if (changed && DIV.section === "profile") {
      // Yozilayotgan matn yo'qolmasin (qayta chizishda saqlab qolamiz)
      const typed = document.getElementById("div-chat-input")?.value || "";
      renderDivision();
      const input = document.getElementById("div-chat-input");
      if (input && typed) input.value = typed;
      const box = document.getElementById("div-chat-box");
      if (box) box.scrollTop = box.scrollHeight;
    }
  } catch (_) {}
}

function divStartChatPolling() {
  divStopChatPolling();
  DIV.chatTimer = setInterval(divLoadChat, 5000);
  void divLoadChat();
}

function divStopChatPolling() {
  if (DIV.chatTimer) { clearInterval(DIV.chatTimer); DIV.chatTimer = null; }
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

  root.querySelector("#div-btn-submit")?.addEventListener("click", async (e) => {
    const m = DIV.status?.my_match;
    if (!m) return;
    const s1 = Number(document.getElementById("div-s1").value || 0);
    const s2 = Number(document.getElementById("div-s2").value || 0);
    // Hisob player1:player2 tartibida saqlanadi — men player2 bo'lsam almashtiramiz
    const [a, b] = (m.player1_id === DIV.status.me_id) ? [s1, s2] : [s2, s1];
    e.target.disabled = true;
    try {
      await apiFetch(`/div/match/submit-result?match_id=${m.id}&score1=${a}&score2=${b}`, { method: "POST" });
      showToast("Natija kiritildi ✅");
      await divLoadStatus();
    } catch (err) {
      e.target.disabled = false;
      showToast("Xato: " + err.message);
    }
  });

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

  root.querySelector("#div-chat-send")?.addEventListener("click", async () => {
    const input = document.getElementById("div-chat-input");
    const m = DIV.status?.my_match;
    if (!m || !input || !input.value.trim()) return;
    const text = input.value.trim();
    input.value = "";
    try {
      await apiFetch(`/div/chat/${m.id}`, {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      await divLoadChat();
    } catch (err) {
      showToast("Xabar yuborilmadi: " + err.message);
    }
  });

  // Profil ochiq bo'lsa chatni jonli yangilab turamiz
  if (DIV.section === "profile" && DIV.status?.my_match && !DIV.status.my_match.is_bye) {
    if (!DIV.chatTimer) divStartChatPolling();
  }
}
