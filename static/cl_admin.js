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
  panel.classList.remove("hidden");
  panel.innerHTML = `
    <div class="card" style="border-color:rgba(245,197,66,.45)">
      <b>⚙️ ChL admin paneli</b>
      <div style="font-size:12.5px;opacity:.75;margin:4px 0 10px">
        ${drawn
          ? "Qur'a o'tkazilgan. Guruhlar va kalendar tayyor."
          : "Qur'a: 32 kvalifikant tasodifiy 8 guruhga (4 tadan) bo'linadi va kalendar tuziladi. Bu amalni ortga qaytarib bo'lmaydi."}
      </div>
      <button class="btn btn--primary" id="cl-admin-draw" ${drawn ? "disabled" : ""}>
        🎲 Qur'a o'tkazish
      </button>
      ${drawn ? `
      <div style="font-size:12.5px;opacity:.75;margin:12px 0 8px">
        Kalendarni qayta qurish: guruh tarkibi saqlanadi, o'yinlar ikki doira
        (uy + mehmon, 6 tur) qilib qaytadan yoziladi. Natija kiritilgan bo'lsa ishlamaydi.
      </div>
      <button class="btn" id="cl-admin-rebuild">🔁 Kalendarni qayta qurish (uy+mehmon)</button>` : ""}
    </div>`;

  const btn = document.getElementById("cl-admin-draw");
  if (btn && !drawn) btn.addEventListener("click", () => void clAdminDraw(btn));

  const rbtn = document.getElementById("cl-admin-rebuild");
  if (rbtn) rbtn.addEventListener("click", () => void clAdminRebuild(rbtn));
}

// Kalendarni qayta qurish (ikki doira, to'g'ri tur raqamlari)
async function clAdminRebuild(btn) {
  if (!confirm("Kalendar qayta qurilsinmi? Barcha (o'ynalmagan) o'yinlar qaytadan yoziladi.")) return;
  btn.disabled = true;
  btn.textContent = "Qayta qurilmoqda…";
  try {
    const r = await apiFetch("/cl/schedule/rebuild", { method: "POST" });
    showToast(`Kalendar tayyor ✅ ${r.matches} o'yin (${r.groups} guruh)`);
    CL.section = "home";
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "🔁 Kalendarni qayta qurish (uy+mehmon)";
    showToast("Xato: " + clDrawErrorText(e.message));
  }
}

async function clAdminDraw(btn) {
  if (!confirm("Qur'a o'tkazilsinmi? Bu amalni ortga qaytarib bo'lmaydi.")) return;
  btn.disabled = true;                       // ikki marta bosishdan himoya (qoida 38)
  btn.textContent = "Qur'a o'tkazilmoqda…";  // vizual javob (qoida 40)
  try {
    const r = await apiFetch("/cl/draw", { method: "POST" });
    showToast(`Qur'a o'tkazildi ✅ ${r.groups} guruh, ${r.matches} o'yin`);
    CL.section = "home";
    await clLoadThenRender();
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "🎲 Qur'a o'tkazish";
    showToast("Xato: " + clDrawErrorText(e.message));
  }
}

function clDrawErrorText(reason) {
  return ({
    already_drawn: "qur'a allaqachon o'tkazilgan",
    no_participants: "kvalifikantlar topilmadi",
    not_drawn: "avval qur'a o'tkazing",
    results_exist: "natija kiritilgan o'yinlar bor — kalendar qayta qurilmaydi",
  })[reason] || reason;
}
