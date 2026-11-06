// =============================================================
//  mshot_tech.js — «⚠️ RAQIB YOZMADI / O'YNAMADI» — texnik g'alaba so'rovi (2026-11-06, barcha rejimlar).
//  Yozishma skrinshotlari (MS_TECH_MAX gacha) + izoh → POST /mshot/tech. Hech qachon avtomatik emas — admin hal qiladi.
//  Global: apiFetch, escHtml, showToast, msT, msErr, msShrink, msModal, msCloseModal (mshot.js).
// =============================================================

const MS_TECH_MAX = 3;
const MS_TECH_IMG_MAX = 1400;
const MS_TECH_Q = 0.8;
const MST = { ctx: null, files: [], busy: false };

function msTechHtml() {
  return `<div class="modal-title">${escHtml(msT("ms_tech_title"))}</div>
    <div class="ms-hint">${escHtml(msT("ms_tech_hint"))}</div>
    <label class="btn btn--ghost ms-wide">${escHtml(msT("ms_tech_pick"))}
      <input type="file" accept="image/*" multiple id="ms-tech-files" hidden></label>
    <div class="ms-tech-n">${MST.files.length ? escHtml(msT("ms_tech_n", { n: MST.files.length })) : ""}</div>
    <textarea class="modal-input ms-tech-note" id="ms-tech-note" maxlength="500" rows="2" required placeholder="${escHtml(msT("ms_tech_note"))}"></textarea>
    <div class="modal-actions">
      <button class="btn btn--ghost" data-ms-tech="close">${escHtml(msT("ms_close"))}</button>
      <button class="btn btn--primary" data-ms-tech="send" ${MST.busy || !MST.files.length ? "disabled" : ""}>${escHtml(msT(MST.busy ? "ms_applying" : "ms_tech_send"))}</button>
    </div>`;
}
function msTechRender() {
  const note = document.getElementById("ms-tech-note")?.value || "";
  msModal("ms-tech", msTechHtml());
  const t = document.getElementById("ms-tech-note");
  if (t) t.value = note;
}

function msTechOpen(c) {
  MST.ctx = c; MST.files = []; MST.busy = false;
  msModal("ms-tech", msTechHtml());
}

const MS_TECH_NOTE_MIN = 5;                          // izoh majburiy (server: match_claims.CLAIM_NOTE_MIN)

async function msTechSend() {
  if (MST.busy || !MST.files.length) return;
  const noteEl = document.getElementById("ms-tech-note");
  if ((noteEl?.value || "").trim().length < MS_TECH_NOTE_MIN) {          // 2026-11-06 (egasi): izohsiz yuborilmaydi
    showToast(msErr("no_note"));
    noteEl?.focus();
    return;
  }
  MST.busy = true; msTechRender();
  try {
    const images = [];
    for (const f of MST.files) images.push(await msShrink(f, MS_TECH_IMG_MAX, MS_TECH_Q));
    const note = document.getElementById("ms-tech-note")?.value || "";
    await apiFetch("/mshot/tech", { method: "POST",
      body: JSON.stringify({ mode: MST.ctx.mode, match_id: MST.ctx.id, images, note }) });
    msCloseModal("ms-tech");
    showToast(msT("ms_tech_sent"));
  } catch (e) {
    showToast(msErr(e));
    MST.busy = false; msTechRender();
  }
  MST.busy = false;
}

document.addEventListener("change", (e) => {
  if (!e.target || e.target.id !== "ms-tech-files") return;
  MST.files = Array.from(e.target.files || []).filter(f => /^image\//.test(f.type || "")).slice(0, MS_TECH_MAX);
  msTechRender();
});
document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-ms-tech]") : null;
  if (!b || !b.closest("#ms-tech")) return;
  if (b.dataset.msTech === "close") msCloseModal("ms-tech");
  if (b.dataset.msTech === "send") void msTechSend();
});
