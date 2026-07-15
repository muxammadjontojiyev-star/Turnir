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

const CL_ADMIN = { isSuper: false, loaded: false };

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
        Akkount almashtirish: o'chirilgan akkount o'rniga yangi Telegram ID'ni bog'laydi.
        So'ng kalendarni qayta quring.
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
}

// Kalendarni qayta qurish (ikki doira, to'g'ri tur raqamlari)
// O'chirilgan (users'da yo'q) ishtirokchilar ro'yxatini yuklaydi
async function clLoadOrphans() {
  const box = document.getElementById("cl-orphans-box");
  if (!box) return;
  try {
    const d = await apiFetch("/cl/participants/orphans");
    const list = d.orphans || [];
    if (!list.length) {
      box.innerHTML = `<div style="font-size:12px;opacity:.6">O'chirilgan akkount topilmadi.</div>`;
      return;
    }
    const opts = list.map(o =>
      `<option value="${o.user_id}">Guruh ${o.group_number || "?"} · ${(o.nickname || "—").replace(/"/g, "")} (eski id ${o.user_id})</option>`
    ).join("");
    box.innerHTML = `<select class="modal-input cl-orphan-select" id="cl-orphan-select">
      <option value="">— o'chirilgan ishtirokchini tanlang —</option>${opts}
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
  if (!oldUid) { showToast("O'chirilgan ishtirokchini tanlang"); return; }
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

async function clAdminRebuild(btn) {
  if (!confirm("Kalendar qayta qurilsinmi? Barcha (o'ynalmagan) o'yinlar qaytadan yoziladi.")) return;
  btn.disabled = true;
  btn.textContent = "Qayta qurilmoqda…";
  try {
    const r = await apiFetch("/cl/schedule/rebuild", { method: "POST" });
    showToast(`Kalendar tayyor: ${r.matches} o'yin (${r.groups} guruh)`);
    CL.section = "home";
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.innerHTML = `${ICON.get("recycle", 16)} Kalendarni qayta qurish (uy+mehmon)`;
    showToast("Xato: " + clDrawErrorText(e.message));
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
