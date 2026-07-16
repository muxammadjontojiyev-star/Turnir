// ============================================================
//  cl_admin.js — Chempionlar ligasi admin paneli (ChL Profil tabi ichida)
//
//  worldcup_admin.js naqshi (qoida 10 — parallel joylar sinxron):
//    - Bosh admin (config ADMIN_TELEGRAM_IDS) → panel ko'rinadi
//    - Boshqa hamma → panel yashirin
//  Rol serverdan aniqlanadi: GET /admin/whoami (is_super). Kodda ID yo'q.
//
//  Amallar: Qur'a o'tkazish → POST /cl/draw (32 kvalifikant → 8 guruh × 4)
//  Global: apiFetch, showToast, escHtml, CL, clLoadThenRender
// ============================================================

const CL_ADMIN = { isSuper: false, loaded: false, fixId: "", fixInfo: null };

async function clLoadAdminPanel() {
  const panel = document.getElementById("cl-admin-panel");
  if (!panel) return;

  try {
    const who = await apiFetch("/admin/whoami");
    CL_ADMIN.isSuper = !!who.is_super;
  } catch (_) {
    CL_ADMIN.isSuper = false;
  }

  if (!CL_ADMIN.isSuper) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }

  const drawn = !!(CL.groups && CL.groups.drawn);
  const st = CL.state || {};
  const started = !!st.started;
  panel.classList.remove("hidden");
  panel.innerHTML = `
    <div class="card" style="border-color:rgba(245,197,66,.45)">
      <b>${ICON.get("shield", 16)} ChL admin paneli</b>
      <div style="font-size:12.5px;opacity:.75;margin:4px 0 10px">
        ${drawn
          ? "Qur'a o'tkazilgan. Guruhlar va kalendar tayyor."
          : "Qur'a: 32 kvalifikant tasodifiy 8 guruhga (4 tadan) bo'linadi va kalendar tuziladi. Bu amalni ortga qaytarib bo'lmaydi."}
      </div>
      <button class="btn btn--primary" id="cl-admin-draw" ${drawn ? "disabled" : ""}>
        ${ICON.get("dice", 16)} Qur'a o'tkazish
      </button>
      ${drawn ? `
      <div style="font-size:12.5px;opacity:.75;margin:12px 0 8px">
        Kalendarni qayta qurish: guruh tarkibi saqlanadi, o'yinlar ikki doira
        (uy + mehmon, 6 tur) qilib qaytadan yoziladi. Natija kiritilgan bo'lsa ishlamaydi.
      </div>
      <button class="btn" id="cl-admin-rebuild">${ICON.get("recycle", 16)} Kalendarni qayta qurish (uy+mehmon)</button>

      <div style="font-size:12.5px;opacity:.75;margin:14px 0 6px">
        Ishtirokchini almashtirish: guruhdagi istalgan ishtirokchini (⚠️ = o'chirilgan
        akkount) yangi Telegram ID'ga bog'laydi. So'ng kalendarni qayta quring.
      </div>
      <div id="cl-orphans-box" style="margin-bottom:6px"></div>
      <input class="modal-input" id="cl-new-tg" type="number" inputmode="numeric"
             placeholder="Yangi Telegram ID" style="margin-bottom:8px">
      <button class="btn" id="cl-admin-reassign">👤 Akkountni almashtirish</button>

      <div style="font-size:12.5px;opacity:.75;margin:12px 0 8px">
        ${started
          ? `O'yinlar boshlangan. Joriy tur: <b>${st.current_matchday}</b> / ${st.total_matchdays}. Har kuni 23:30 (Toshkent) da joriy tur yopiladi (kiritilmagan o'yinlar 0:0) va keyingisi ochiladi.`
          : "O'yinlarni boshlash: 1-tur ochiladi. Keyingi turlar har kuni 23:30 da avtomatik ochiladi."}
      </div>
      <button class="btn btn--primary" id="cl-admin-start" ${started ? "disabled" : ""}>
        ${ICON.get("play", 16)} O'yinlarni boshlash
      </button>` : ""}

      ${drawn ? clAdminFixForm() : ""}
    </div>`;

  if (typeof applyIcons === "function") applyIcons(panel);

  const btn = document.getElementById("cl-admin-draw");
  if (btn && !drawn) btn.addEventListener("click", () => void clAdminDraw(btn));

  const rbtn = document.getElementById("cl-admin-rebuild");
  if (rbtn) rbtn.addEventListener("click", () => void clAdminRebuild(rbtn));

  const rasgn = document.getElementById("cl-admin-reassign");
  if (rasgn) rasgn.addEventListener("click", () => void clAdminReassign(rasgn));

  if (document.getElementById("cl-orphans-box")) void clLoadOrphans();

  const sbtn = document.getElementById("cl-admin-start");
  if (sbtn && !started) sbtn.addEventListener("click", () => void clAdminStart(sbtn));

  // Match ID orqali tuzatish (liga naqshi)
  const fixId = document.getElementById("cl-fix-match-id");
  if (fixId) fixId.addEventListener("input", (e) => clFixIdChanged(e.target.value));
  const fixSubmit = document.getElementById("cl-fix-submit");
  if (fixSubmit) fixSubmit.addEventListener("click", () => void clAdminFixSubmit(fixSubmit));
}

// --- ChL "Match ID orqali tuzatish" (liga divAdminFixForm naqshi, ranglar ChL) ---
function clAdminFixForm() {
  const info = CL_ADMIN.fixInfo;
  let preview = "";
  if (info === "notfound") {
    preview = `<div style="font-size:12px;color:#ff6b6b;margin:6px 0">O'yin topilmadi</div>`;
  } else if (info) {
    const p1 = info.player1_username ? "@" + info.player1_username : (info.player1_name || "—");
    const p2 = info.player2_username ? "@" + info.player2_username : (info.player2_name || "—");
    const cur = (info.score1 != null) ? `${info.score1} : ${info.score2}` : "— : —";
    const badge = (club) => (typeof clClubBadge === "function") ? clClubBadge(club, 30) : "";
    preview = `
      <div class="card" style="margin:8px 0;padding:10px 12px">
        <div style="opacity:.65;font-size:11.5px">#${info.id} · Guruh ${info.group_number} · ${info.matchday}-tur</div>
        <div style="display:flex;align-items:center;justify-content:center;gap:12px;margin-top:6px">
          ${badge(info.player1_club)}
          <span style="font-weight:800;white-space:nowrap;font-size:16px">${cur}</span>
          ${badge(info.player2_club)}
        </div>
        <div style="display:flex;justify-content:space-between;font-size:11.5px;opacity:.75;margin-top:4px">
          <span>${escHtml(p1)}</span><span>${escHtml(p2)}</span>
        </div>
      </div>`;
  }
  const disabled = !info || info === "notfound";
  return `
    <div class="section-label" style="margin-top:16px">MATCH ID ORQALI TUZATISH</div>
    <input id="cl-fix-match-id" class="modal-input" type="number" min="1"
           placeholder="Match ID" value="${CL_ADMIN.fixId || ""}" style="margin-bottom:6px" />
    ${preview}
    <div class="score-input-row" style="display:flex;align-items:center;justify-content:center;gap:10px;margin:6px 0">
      <input id="cl-fix-score1" class="score-input" type="number" min="0" max="99"
             value="${info && info !== "notfound" && info.score1 != null ? info.score1 : 0}" />
      <span class="score-separator">:</span>
      <input id="cl-fix-score2" class="score-input" type="number" min="0" max="99"
             value="${info && info !== "notfound" && info.score2 != null ? info.score2 : 0}" />
    </div>
    <button class="btn btn--primary" id="cl-fix-submit" ${disabled ? "disabled" : ""}
            style="opacity:${disabled ? ".45" : "1"}">Tuzatish</button>`;
}

let _clFixTimer = null;
function clFixIdChanged(raw) {
  clearTimeout(_clFixTimer);
  CL_ADMIN.fixId = raw;
  const id = parseInt(raw, 10);
  if (!id || id <= 0) { CL_ADMIN.fixInfo = null; clRerenderPanel(); return; }
  _clFixTimer = setTimeout(async () => {
    try {
      CL_ADMIN.fixInfo = await apiFetch(`/cl/admin/match/${id}/info`);
    } catch (_) {
      CL_ADMIN.fixInfo = "notfound";
    }
    clRerenderPanel();
  }, 350);
}

// Panelni qayta chizadi va ID inputga fokusni tiklaydi (qoida #40)
function clRerenderPanel() {
  void clLoadAdminPanel().then(() => {
    const el = document.getElementById("cl-fix-match-id");
    if (el) { el.focus(); const v = el.value; el.value = ""; el.value = v; }
  });
}

async function clAdminFixSubmit(btn) {
  const id = parseInt(CL_ADMIN.fixId, 10);
  const s1 = Number(document.getElementById("cl-fix-score1").value || 0);
  const s2 = Number(document.getElementById("cl-fix-score2").value || 0);
  if (!id) { showToast("Match ID kiriting"); return; }
  if (!confirm(`#${id} natijasi ${s1}:${s2} qilib tuzatilsinmi?`)) return;
  btn.disabled = true;
  btn.textContent = "Tuzatilmoqda…";
  try {
    await apiFetch(`/cl/admin/match/set-result?match_id=${id}&score1=${s1}&score2=${s2}`,
                   { method: "POST" });
    showToast("Natija tuzatildi");
    CL_ADMIN.fixId = "";
    CL_ADMIN.fixInfo = null;
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Tuzatish";
    const msg = { match_not_found: "o'yin topilmadi" }[e.message] || e.message;
    showToast("Xato: " + msg);
  }
}

// Kalendarni qayta qurish (ikki doira, to'g'ri tur raqamlari)
// Barcha ishtirokchilar ro'yxatini yuklaydi (admin almashtirish uchun)
async function clLoadOrphans() {
  const box = document.getElementById("cl-orphans-box");
  if (!box) return;
  try {
    const d = await apiFetch("/cl/participants/all");
    const list = d.participants || [];
    if (!list.length) {
      box.innerHTML = `<div style="font-size:12px;opacity:.6">Ishtirokchilar topilmadi.</div>`;
      return;
    }
    const opts = list.map(o => {
      const mark = o.orphan ? "⚠️ " : "";
      const label = `${mark}G${o.group_number || "?"} · ${(o.nickname || "—").replace(/"/g, "")}`;
      return `<option value="${o.user_id}">${label}</option>`;
    }).join("");
    box.innerHTML = `<select class="modal-input cl-orphan-select" id="cl-orphan-select">
      <option value="">— almashtiriladigan ishtirokchini tanlang —</option>${opts}
    </select>`;
  } catch (_) {
    box.innerHTML = `<div style="font-size:12px;opacity:.6">Ro'yxat yuklanmadi.</div>`;
  }
}

// Akkount almashtirish (tanlangan participant → yangi Telegram ID)
async function clAdminReassign(btn) {
  const sel = document.getElementById("cl-orphan-select");
  const oldUid = sel ? Number(sel.value || 0) : 0;
  const newTg = Number(document.getElementById("cl-new-tg").value || 0);
  if (!oldUid) { showToast("Almashtiriladigan ishtirokchini tanlang"); return; }
  if (!newTg) { showToast("Yangi Telegram ID kiriting"); return; }
  if (!confirm(`Tanlangan ishtirokchi yangi akkountga (${newTg}) bog'lansinmi?`)) return;
  btn.disabled = true;
  const prev = btn.innerHTML;
  btn.textContent = "Bog'lanmoqda…";
  try {
    const r = await apiFetch("/cl/participant/reassign", {
      method: "POST",
      body: JSON.stringify({ old_user_id: oldUid, new_telegram_id: newTg }),
    });
    showToast(`Bog'landi: ${r.matches_updated} o'yin yangilandi. Endi kalendarni qayta quring.`);
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = prev;
    const msg = {
      new_user_not_found: "yangi akkount botda topilmadi (avval /start bossin)",
      nothing_to_reassign: "bu id topilmadi",
      new_already_participant: "yangi akkount allaqachon ishtirokchi",
    }[e.message] || e.message;
    showToast("Xato: " + msg);
  }
}

async function clAdminRebuild(btn, force = false) {
  const msg = force
    ? "MAJBURIY qayta qurish? Kiritilgan natijalar saqlanadi, buzuq turlar tuzatiladi."
    : "Kalendar qayta qurilsinmi? Barcha (o'ynalmagan) o'yinlar qaytadan yoziladi.";
  if (!confirm(msg)) return;
  btn.disabled = true;
  btn.textContent = "Qayta qurilmoqda…";
  try {
    const r = await apiFetch("/cl/schedule/rebuild", {
      method: "POST",
      body: JSON.stringify({ force }),
    });
    showToast(`Kalendar tayyor: ${r.matches} o'yin (${r.groups} guruh)`);
    CL.section = "home";
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("recycle", 16)} Kalendarni qayta qurish (uy+mehmon)`;
    if (e.message === "results_exist") {
      // Natija bor — majburiy (natijalarni saqlab) qurishni taklif qilamiz
      if (confirm("Natija kiritilgan o'yinlar bor. Ularni SAQLAB, buzuq kalendarni "
                  + "tuzataymi? (natijalar yangi turlarga ko'chiriladi)")) {
        return clAdminRebuild(btn, true);
      }
    } else {
      showToast("Xato: " + clDrawErrorText(e.message));
    }
  }
}

async function clAdminDraw(btn) {
  if (!confirm("Qur'a o'tkazilsinmi? Bu amalni ortga qaytarib bo'lmaydi.")) return;
  btn.disabled = true;                       // ikki marta bosishdan himoya (qoida 38)
  btn.textContent = "Qur'a o'tkazilmoqda…";  // vizual javob (qoida 40)
  try {
    const r = await apiFetch("/cl/draw", { method: "POST" });
    showToast(`Qur'a o'tkazildi: ${r.groups} guruh, ${r.matches} o'yin`);
    CL.section = "home";
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("dice", 16)} Qur'a o'tkazish`;
    showToast("Xato: " + clDrawErrorText(e.message));
  }
}

// Turlarni boshlash (1-tur ochiladi)
async function clAdminStart(btn) {
  if (!confirm("O'yinlar boshlansinmi? 1-tur ochiladi.")) return;
  btn.disabled = true;
  btn.textContent = "Boshlanmoqda…";
  try {
    const r = await apiFetch("/cl/rounds/start", { method: "POST" });
    showToast(`Boshlandi: ${r.current_matchday}-tur ochildi`);
    CL.section = "profile";
    await clLoadProfile();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("play", 16)} O'yinlarni boshlash`;
    showToast("Xato: " + clDrawErrorText(e.message));
  }
}

function clDrawErrorText(reason) {
  return ({
    already_drawn: "qur'a allaqachon o'tkazilgan",
    no_participants: "kvalifikantlar topilmadi",
    not_drawn: "avval qur'a o'tkazing",
    results_exist: "natija kiritilgan o'yinlar bor — kalendar qayta qurilmaydi",
    already_started: "o'yinlar allaqachon boshlangan",
    matchday_locked: "bu tur hali ochilmagan",
  })[reason] || reason;
}
