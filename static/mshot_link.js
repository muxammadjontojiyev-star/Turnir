// =============================================================
//  mshot_link.js — «Bu sizning ikkinchi akkauntingizmi?» (2026-11-06, ef_nick_link.py; faqat shu mavsum).
//  Boshqa Telegram akkaunt mening eFootball niknamemni kiritsa — menga kartochka: «Ha, meniki» / «Yo'q».
//  API: GET /ef-nick/links, POST /ef-nick/links/{id} {accept}. Global: apiFetch, escHtml, showToast, msT, msErr.
// =============================================================

const MSL_POLL_MS = 5 * 60 * 1000;
const MSL_START_MS = 3000;
const MSL = { items: [], busy: false };

function mslRender() {
  document.getElementById("msl-box")?.remove();
  const it = MSL.items[0];
  if (!it) return;
  const who = it.username ? "@" + it.username : (it.nickname || "");
  const box = document.createElement("div");
  box.id = "msl-box";
  box.className = "msi-box msl-box";
  box.innerHTML = `<div class="msi-title">🔗 ${escHtml(msT("ms_link_title"))}</div>
    <div class="msi-text">${escHtml(msT("ms_link_text", { who }))}</div>
    <div class="msi-acts">
      <button class="btn btn--ghost" data-msl="0" data-msl-id="${Number(it.id)}">${escHtml(msT("ms_link_no"))}</button>
      <button class="btn btn--primary" data-msl="1" data-msl-id="${Number(it.id)}">${escHtml(msT("ms_link_yes"))}</button>
    </div>`;
  document.body.appendChild(box);
}

async function mslLoad() {
  if (document.hidden) return;
  try { MSL.items = (await apiFetch("/ef-nick/links")).items || []; mslRender(); } catch (_) { /* jim */ }
}

document.addEventListener("click", async (e) => {
  const b = e.target.closest ? e.target.closest("[data-msl]") : null;
  if (!b || MSL.busy) return;
  const accept = b.dataset.msl === "1";
  if (!accept && !window.confirm(msT("ms_link_no_q"))) return;
  MSL.busy = true; b.disabled = true;
  try {
    await apiFetch(`/ef-nick/links/${Number(b.dataset.mslId)}`, { method: "POST", body: JSON.stringify({ accept }) });
    showToast(msT(accept ? "ms_link_done_yes" : "ms_link_done_no"));
    MSL.items = MSL.items.filter(x => x.id !== Number(b.dataset.mslId));
    mslRender();
  } catch (err) { showToast(msErr(err)); b.disabled = false; }
  finally { MSL.busy = false; }
});

setTimeout(() => { void mslLoad(); setInterval(mslLoad, MSL_POLL_MS); }, MSL_START_MS);
