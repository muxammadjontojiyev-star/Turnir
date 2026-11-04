// =============================================================
//  player_card_edit.js — «⚙️ Kartani sozlash» oynasi (2026-11-04): pozitsiya va davlat (bayroq) tanlash.
//  API: GET /pcard/options, POST /pcard/me {position, country}. Davlat nomi — Intl.DisplayNames
//  (foydalanuvchi tilida), bo'lmasa — kod. Global: pcardHtml, pcT, pcFlag, pcRemember, pcRefreshMine
//  (player_card.js), APP, apiFetch, escHtml, showToast.
// =============================================================

const PCE = { opts: null, uid: null, pos: null, cc: null, busy: false };

function pceCountryName(cc) {
  try { return new Intl.DisplayNames([APP.lang || "uz", "en"], { type: "region" }).of(cc) || cc; }
  catch (_) { return cc; }
}

function pceHtml() {
  const o = PCE.opts;
  const chip = (v, label) => `<button class="pce-chip${PCE.pos === v ? " active" : ""}" data-pce-pos="${escHtml(v || "")}">${escHtml(label)}</button>`;
  const countries = o.countries.map(cc => ({ cc, n: pceCountryName(cc) }))
    .sort((a, b) => (a.cc === "UZ" ? -1 : b.cc === "UZ" ? 1 : a.n.localeCompare(b.n)));
  return `<div class="modal-box pce-box">
      <div class="modal-title">${escHtml(pcT("pc_edit_title"))}</div>
      <div class="pce-label">${escHtml(pcT("pc_pos"))}</div>
      <div class="pce-chips">${chip(null, pcT("pc_none"))}${o.positions.map(p => chip(p, p)).join("")}</div>
      <div class="pce-label">${escHtml(pcT("pc_country"))}</div>
      <select class="modal-input" id="pce-country">
        <option value="">${escHtml(pcT("pc_none"))}</option>
        ${countries.map(x => `<option value="${escHtml(x.cc)}"${PCE.cc === x.cc ? " selected" : ""}>${pcFlag(x.cc)} ${escHtml(x.n)}</option>`).join("")}
      </select>
      <div class="modal-actions">
        <button class="btn btn--ghost" data-pce="cancel">${escHtml(pcT("pc_cancel"))}</button>
        <button class="btn btn--primary" data-pce="save">${escHtml(pcT("pc_save"))}</button>
      </div>
    </div>`;
}

async function pceOpen(uid) {
  if (!uid) return;
  PCE.uid = uid;
  try {
    PCE.opts = PCE.opts || await apiFetch("/pcard/options");
    const c = await apiFetch(`/pcard/${Number(uid)}`);
    PCE.pos = c.position || null; PCE.cc = c.country || null;
  } catch (_) { showToast(pcT("pc_err")); return; }
  document.getElementById("pce-modal")?.remove();
  const m = document.createElement("div");
  m.id = "pce-modal"; m.className = "modal";
  m.innerHTML = pceHtml();
  document.body.appendChild(m);
}

async function pceSave() {
  if (PCE.busy) return;                                    // ikki marta bosish (qoida #38)
  PCE.busy = true;
  PCE.cc = document.getElementById("pce-country")?.value || null;
  try {
    pcRemember(await apiFetch("/pcard/me", { method: "POST", body: JSON.stringify({ position: PCE.pos, country: PCE.cc }) }));
    document.getElementById("pce-modal")?.remove();
    showToast(pcT("pc_saved"));
    pcRefreshMine();
  } catch (_) {
    showToast(pcT("pc_err"));
  } finally {
    PCE.busy = false;
  }
}

document.addEventListener("click", (e) => {
  const t = e.target.closest ? e.target : null;
  if (!t) return;
  const edit = t.closest("[data-pcard-edit]");
  if (edit) { void pceOpen(Number(edit.dataset.pcardEdit)); return; }
  const modal = document.getElementById("pce-modal");
  if (!modal || !modal.contains(t)) return;
  if (t === modal || t.closest('[data-pce="cancel"]')) { modal.remove(); return; }
  const chip = t.closest("[data-pce-pos]");
  if (chip) {
    PCE.cc = document.getElementById("pce-country")?.value || null;   // tanlangan davlat saqlansin
    PCE.pos = chip.dataset.pcePos || null;
    modal.innerHTML = pceHtml();
    return;
  }
  if (t.closest('[data-pce="save"]')) void pceSave();
});
