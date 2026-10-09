/**
 * cl_season.js — ChL'ni LIGADAN MUSTAQIL boshlash (2026-10-09).
 * Liga mavsumini yakunlash ChL'ga tegmaydi; yangi ChL faqat bosh admin
 * "Yangi ChL mavsumini boshlash" tugmasi bilan ochiladi (POST /season/cl/start).
 * Global: apiFetch, showToast, escHtml, clLoadThenRender (cl_admin.js / api.js).
 */

const CL_SEASON_REASONS = {
  cl_not_finished: "Joriy ChL hali yakunlanmagan — avval \"ChL mavsumini yakunlash\"",
  no_qualifiers:   "Yangi kvalifikantlar yo'q — avval liga mavsumini yakunlang",
  already_started: "Bu kvalifikantlar bilan ChL allaqachon boshlangan",
};

// Panel chizilgach chaqiriladi: holatni yuklab, matn va tugmani yangilaydi.
async function clSeasonInit() {
  const box = document.getElementById("cl-season-info");
  const btn = document.getElementById("cl-admin-season-start");
  if (!box || !btn) return;
  try {
    const d = await apiFetch("/season/cl/info");
    const next = d.next_from_season != null ? `${d.next_from_season}-liga mavsumi` : "yo'q";
    box.innerHTML =
      `Faol ChL kaliti: <b>${escHtml(d.active_season)}</b> · liga mavsumi: <b>${escHtml(d.league_season)}</b>` +
      ` · keyingi kvalifikantlar: <b>${escHtml(next)}</b>` +
      (d.can_start ? "" : `<br>${escHtml(CL_SEASON_REASONS[d.reason] || d.reason || "")}`);
    btn.disabled = !d.can_start;
    btn.onclick = () => void clSeasonStart(btn);
  } catch (e) {
    box.textContent = "Holatni yuklab bo'lmadi: " + e.message;
    btn.disabled = true;
  }
}

async function clSeasonStart(btn) {
  if (!confirm("Yangi ChL mavsumi boshlansinmi?\n\nEng oxirgi liga kvalifikantlari "
             + "yangi ChL ishtirokchilari bo'ladi. Keyin qur'a o'tkazasiz.")) return;
  btn.disabled = true;
  const prev = btn.textContent;
  btn.textContent = "Boshlanmoqda…";
  try {
    const r = await apiFetch("/season/cl/start", { method: "POST" });
    showToast(`✅ Yangi ChL boshlandi (${r.from_season}-mavsum kvalifikantlari)`);
    await clLoadThenRender();
  } catch (e) {
    btn.textContent = prev;
    showToast("❌ " + (CL_SEASON_REASONS[e.message] || e.message));
    void clSeasonInit();
  }
}
