// =============================================================
//  mshot_incoming.js — «Raqibingiz natijani skrinshot bilan yozdi» kartochkasi (2026-11-06).
//  Ilova ochilganda va har MSI_POLL_MS da tekshiriladi (ilova ko'rinib turganda). «To'g'ri» — yopiladi,
//  «E'tiroz» — adminga (POST /mshot/{id}/dispute). Muddati — server (DISPUTE_HOURS).
//  Global: apiFetch, escHtml, showToast, msT, msErr.
// =============================================================

const MSI_POLL_MS = 5 * 60 * 1000;
const MSI_START_MS = 2500;
const MSI_SEEN_KEY = "mshot_seen_v1";
const MSI = { items: [], busy: false };

function msiSeen() {
  try { return JSON.parse(localStorage.getItem(MSI_SEEN_KEY) || "[]"); } catch (_) { return []; }
}
function msiMarkSeen(id) {
  try { localStorage.setItem(MSI_SEEN_KEY, JSON.stringify([...new Set([...msiSeen(), id])].slice(-50))); } catch (_) {}
}

function msiRender() {
  document.getElementById("msi-box")?.remove();
  const seen = msiSeen();
  const it = MSI.items.find(x => !seen.includes(x.id));
  if (!it) return;
  const h = Math.max(1, Math.ceil((Number(it.left_s) || 0) / 3600));
  const box = document.createElement("div");
  box.id = "msi-box";
  box.className = "msi-box";
  box.innerHTML = `<div class="msi-title">${escHtml(msT("ms_in_title"))} · ${escHtml(msT(`ms_mode_${it.mode}`))}</div>
    <div class="msi-text">${escHtml(msT("ms_in_text", { who: it.nickname || "", score: `${it.my_goals}:${it.their_goals}` }))}</div>
    <div class="msi-left">${escHtml(msT("ms_in_left", { h }))}</div>
    <div class="msi-acts">
      <button class="btn btn--ghost" data-msi="ok" data-msi-id="${Number(it.id)}">${escHtml(msT("ms_in_ok"))}</button>
      <button class="btn btn--danger" data-msi="dispute" data-msi-id="${Number(it.id)}">${escHtml(msT("ms_in_dispute"))}</button>
    </div>`;
  document.body.appendChild(box);
}

async function msiLoad() {
  if (document.hidden) return;
  try {
    const r = await apiFetch("/mshot/incoming");
    MSI.items = r.items || [];
    msiRender();
  } catch (_) { /* jim — asosiy ilovaga xalaqit bermasin */ }
}

document.addEventListener("click", async (e) => {
  const b = e.target.closest ? e.target.closest("[data-msi]") : null;
  if (!b || MSI.busy) return;
  const id = Number(b.dataset.msiId);
  if (b.dataset.msi === "ok") { msiMarkSeen(id); msiRender(); return; }
  if (!window.confirm(msT("ms_in_q"))) return;
  MSI.busy = true; b.disabled = true;
  try {
    await apiFetch(`/mshot/${id}/dispute`, { method: "POST" });
    showToast(msT("ms_in_sent"));
    msiMarkSeen(id);
    MSI.items = MSI.items.filter(x => x.id !== id);
    msiRender();
  } catch (err) { showToast(msErr(err)); b.disabled = false; }
  finally { MSI.busy = false; }
});

setTimeout(() => { void msiLoad(); setInterval(msiLoad, MSI_POLL_MS); }, MSI_START_MS);
