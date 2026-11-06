// =============================================================
//  mshot.js — NATIJA KIRITISH OYNALARIGA 2 TUGMA (2026-11-06, barcha rejimlar):
//    «📸 Skrinshot bilan yuborish» — Match History skrinshoti → bot o'qiydi → o'yinni tanlash → natija yoziladi
//    «⚠️ Raqib yozmadi / o'ynamadi» — mshot_tech.js
//  Har rejimning natija oynasi kuzatiladi (MS_CTX) — rejim fayllariga tegilmaydi. API: /mshot/read, /mshot/apply,
//  /ef-nick (mshot_nick.js). Global: APP, apiFetch, escHtml, showToast, msT, msErr (texts_mshot.js).
// =============================================================

const MS_IMG_MAX = 1800;          // skrinshot shu o'lchamgacha kichraytiriladi (o'qish uchun yetarli)
const MS_IMG_Q = 0.88;
const MS = { ctx: null, rows: null, token: null, busy: false, only: true, pick: null };
const MS_PLAYOFF = new Set(["wc_po", "cl_po", "el_po", "ac_po", "co_po"]);

// «Natija faqat skrinshot bilan» (bosh admin kaliti, match_guard.py) — yoqiq bo'lsa qo'lda kiritish yashiriladi
async function msLoadConfig() {
  try { MS.only = !!(await apiFetch("/mshot/config")).shot_only; } catch (_) { /* standart — yoqiq */ }
  document.querySelectorAll(".ms-slot").forEach(el => el.remove());
  msSync();
}
setTimeout(msLoadConfig, 1200);

// Ochiq natija oynasi → {mode, id}. Umumiy #modal-result (liga, ChL, YeL, OChL, KL — guruh va pley-off).
function msResultModalCtx() {
  const pick = [
    ["cl_po", typeof CLPO !== "undefined" && CLPO._resultMatchId], ["cl", typeof CL !== "undefined" && CL._resultMatchId],
    ["el_po", typeof ELPO !== "undefined" && ELPO._resultMatchId], ["el", typeof EL !== "undefined" && EL._resultMatchId],
    ["ac_po", typeof ACPO !== "undefined" && ACPO._resultMatchId], ["ac", typeof AC !== "undefined" && AC._resultMatchId],
    ["co_po", typeof COPO !== "undefined" && COPO._resultMatchId], ["co", typeof CO !== "undefined" && CO._resultMatchId],
  ].find(([, id]) => id != null && id !== false);
  if (pick) return { mode: pick[0], id: Number(pick[1]) };
  return APP.activeMatchId ? { mode: "league", id: Number(APP.activeMatchId) } : null;
}

const MS_CTX = [
  { box: () => document.getElementById("modal-result"), ctx: msResultModalCtx },
  { box: () => document.getElementById("wc-input-score1")?.closest(".modal"),
    ctx: () => (typeof WC !== "undefined" && WC.activeMatchId ? { mode: "wc", id: Number(WC.activeMatchId) } : null) },
  { box: () => document.getElementById("wc-po-modal"),
    ctx: () => (typeof WC !== "undefined" && WC.poActiveMatch && document.getElementById("wc-po-modal-mode")?.value === "submit"
      ? { mode: "wc_po", id: Number(WC.poActiveMatch) } : null) },
  { box: () => document.getElementById("modal-div-result"),
    ctx: () => (typeof DIV !== "undefined" && DIV.status?.my_match?.id ? { mode: "div", id: Number(DIV.status.my_match.id) } : null) },
  { box: () => document.getElementById("modal-pt-result"),
    ctx: () => { const i = document.querySelector('#modal-pt-result input[id^="pt-s1-"]'); return i ? { mode: "pt", id: Number(i.id.split("-").pop()) } : null; } },
];

function msSlotHtml(c) {
  return `<div class="ms-slot${MS.only ? " ms-slot--only" : ""}" data-ms-mode="${escHtml(c.mode)}" data-ms-id="${Number(c.id)}">
      ${MS.only ? `<div class="ms-only-hint">${escHtml(msT("ms_only_hint"))}</div>` : ""}
      <button class="btn ${MS.only ? "btn--primary btn--glow" : "btn--ghost"} ms-btn" data-ms="shot">${escHtml(msT("ms_btn_shot"))}</button>
      <button class="btn btn--ghost ms-btn ms-btn--warn" data-ms="tech">${escHtml(msT("ms_btn_tech"))}</button>
      ${MS.only && MS_PLAYOFF.has(c.mode) ? `<button class="ms-pen-link" data-ms="pen">${escHtml(msT("ms_pen_manual"))}</button>` : ""}
    </div>`;
}

function msSync() {
  for (const d of MS_CTX) {
    const box = d.box();
    if (!box) continue;
    const open = !box.classList.contains("hidden");
    const slot = box.querySelector(".ms-slot");
    const c = open ? d.ctx() : null;
    if (!c || !c.id) { slot?.remove(); box.classList.remove("ms-only"); continue; }
    if (slot && slot.dataset.msMode === c.mode && Number(slot.dataset.msId) === c.id) continue;
    slot?.remove();
    const actions = box.querySelector(".modal-actions");
    if (!actions) continue;
    actions.insertAdjacentHTML("afterend", msSlotHtml(c));
    box.classList.toggle("ms-only", MS.only);           // qo'lda hisob va «Yuborish» yashiriladi (mshot.css)
  }
}
let _msSyncT = 0;
new MutationObserver(() => { cancelAnimationFrame(_msSyncT); _msSyncT = requestAnimationFrame(msSync); })
  .observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] });

// ---- natija oynasini yopib, rejim ro'yxatini yangilash (rejimning o'z yangilovchisi) ----
const MS_REFRESH = {
  league: () => { closeResultModal(); return refreshMatchViews(); },
  cl: () => { closeResultModal(); return clLoadMatches(); }, cl_po: () => { closeResultModal(); return clpoLoadMyMatches(true); },
  el: () => { closeResultModal(); return elLoadMatches(); }, el_po: () => { closeResultModal(); return elpoLoadMyMatches(true); },
  ac: () => { closeResultModal(); return acLoadMatches(); }, ac_po: () => { closeResultModal(); return acpoLoadMyMatches(true); },
  co: () => { closeResultModal(); return coLoadMatches(); }, co_po: () => { closeResultModal(); return copoLoadMyMatches(true); },
  wc: () => { document.getElementById("wc-input-score1")?.closest(".modal")?.classList.add("hidden"); return wcLoadMatches(); },
  wc_po: () => { document.getElementById("wc-po-modal")?.classList.add("hidden"); return renderWorldCup(); },
  div: () => { document.getElementById("modal-div-result")?.classList.add("hidden"); return divLoadStatus(); },
  pt: () => { const m = document.getElementById("modal-pt-result"); if (m) { m.classList.add("hidden"); m.innerHTML = ""; }
    return typeof PT !== "undefined" && PT.detailId ? ptRefreshDetailKeepScroll(PT.detailId) : null; },
};
async function msRefresh(mode) {
  try { await (MS_REFRESH[mode] || (() => null))(); } catch (e) { console.warn("mshot refresh", e); }
}

// ---- rasmni kichraytirish ----
function msShrink(file, max = MS_IMG_MAX, q = MS_IMG_Q) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight));
      const cv = document.createElement("canvas");
      cv.width = Math.round(img.naturalWidth * k); cv.height = Math.round(img.naturalHeight * k);
      cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
      URL.revokeObjectURL(url);
      resolve(cv.toDataURL("image/jpeg", q));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("bad_image")); };
    img.src = url;
  });
}

function msModal(id, html) {
  let m = document.getElementById(id);
  if (!m) { m = document.createElement("div"); m.id = id; m.className = "modal ms-modal"; document.body.appendChild(m); }
  m.innerHTML = `<div class="modal-box ms-box">${html}</div>`;
  m.classList.remove("hidden");
  return m;
}
function msCloseModal(id) { document.getElementById(id)?.remove(); }

// ---- 📸 skrinshot oynasi ----
function msRowInner(r) {
  return `<span class="ms-row-dt">${escHtml(r.date)} ${escHtml(r.time || "")}</span>
    <span class="ms-row-main"><b>${escHtml(r.left)}</b><span class="ms-row-sc">${Number(r.s_left)} – ${Number(r.s_right)}</span><b>${escHtml(r.right)}</b></span>`;
}
function msRowHtml(r, i) {
  return `<button class="ms-row${r.marked ? " ms-row--marked" : ""}" data-ms-row="${i}" ${MS.busy ? "disabled" : ""}>${msRowInner(r)}</button>`;
}

function msAskHtml() {
  const r = MS.rows[MS.pick];
  return `<div class="ms-hint">${escHtml(msT(r.marked ? "ms_ask_marked" : "ms_ask_one"))}</div>
    <div class="ms-rows"><div class="ms-row ms-row--marked">${msRowInner(r)}</div></div>
    <button class="btn btn--primary btn--glow ms-wide" data-ms-row="${MS.pick}" ${MS.busy ? "disabled" : ""}>${escHtml(msT(MS.busy ? "ms_applying" : "ms_ask_yes"))}</button>
    ${MS.rows.length > 1 ? `<button class="btn btn--ghost ms-wide" data-ms="list">${escHtml(msT("ms_ask_other"))}</button>` : ""}
    <button class="btn btn--ghost ms-wide" data-ms="again">${escHtml(msT("ms_back"))}</button>`;
}

function msShotHtml() {
  const rows = MS.rows;
  if (rows && MS.pick != null && rows[MS.pick]) {
    return `<div class="modal-title">${escHtml(msT("ms_shot_title"))}</div>${msAskHtml()}
      <div class="modal-actions"><button class="btn btn--ghost" data-ms="close">${escHtml(msT("ms_close"))}</button></div>`;
  }
  const body = !rows
    ? `<div class="ms-hint">${escHtml(msT("ms_shot_hint"))}</div>
       <label class="btn btn--primary ms-wide${MS.busy ? " ms-busy" : ""}">${escHtml(msT(MS.busy ? "ms_reading" : "ms_pick_file"))}
         <input type="file" accept="image/*" id="ms-shot-file" hidden ${MS.busy ? "disabled" : ""}></label>`
    : `<div class="ms-hint">${escHtml(msT("ms_pick_row"))}</div>
       <div class="ms-rows">${rows.map(msRowHtml).join("")}</div>
       <button class="btn btn--ghost ms-wide" data-ms="again">${escHtml(msT("ms_back"))}</button>`;
  return `<div class="modal-title">${escHtml(msT("ms_shot_title"))}</div>
    ${typeof msNickInlineHtml === "function" ? msNickInlineHtml() : ""}
    ${body}
    <div class="modal-actions"><button class="btn btn--ghost" data-ms="close">${escHtml(msT("ms_close"))}</button></div>`;
}
function msShotRender() { if (document.getElementById("ms-shot")) msModal("ms-shot", msShotHtml()); }

async function msShotOpen(c) {
  MS.ctx = c; MS.rows = null; MS.token = null; MS.busy = false; MS.pick = null;
  if (typeof msNickLoad === "function") await msNickLoad();
  msModal("ms-shot", msShotHtml());
}

async function msShotRead(file) {
  if (!file || MS.busy) return;
  if (typeof msNickHas === "function" && !msNickHas()) { showToast("❌ " + msT("ms_nick_need")); return; }
  MS.busy = true; msShotRender();
  try {
    const image = await msShrink(file);
    const r = await apiFetch("/mshot/read", { method: "POST", body: JSON.stringify({ image }) });
    MS.rows = r.rows; MS.token = r.token;
    const mk = r.rows.findIndex(x => x.marked);
    MS.pick = mk >= 0 ? mk : (r.rows.length === 1 ? 0 : null);   // belgilangan (yoki yagona) o'yin — so'raymiz
  } catch (e) { showToast(msErr(e)); }
  finally { MS.busy = false; msShotRender(); }
}

async function msShotApply(idx) {
  if (MS.busy || !MS.ctx) return;
  MS.busy = true; msShotRender();
  try {
    const r = await apiFetch("/mshot/apply", { method: "POST",
      body: JSON.stringify({ mode: MS.ctx.mode, match_id: MS.ctx.id, token: MS.token, row: idx }) });
    msCloseModal("ms-shot");
    showToast(msT(r.status === "admin_pending" ? "ms_done_pending" : "ms_done"));
    await msRefresh(MS.ctx.mode);
  } catch (e) {
    showToast(msErr(e));
    MS.busy = false; msShotRender();
  }
  MS.busy = false;
}

document.addEventListener("change", (e) => {
  if (e.target && e.target.id === "ms-shot-file") void msShotRead(e.target.files && e.target.files[0]);
});
document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-ms], [data-ms-row]") : null;
  if (!b) return;
  const slot = b.closest(".ms-slot");
  if (slot) {
    e.preventDefault(); e.stopPropagation();
    const c = { mode: slot.dataset.msMode, id: Number(slot.dataset.msId) };
    if (b.dataset.ms === "shot") void msShotOpen(c);
    if (b.dataset.ms === "tech" && typeof msTechOpen === "function") void msTechOpen(c);
    if (b.dataset.ms === "pen") { slot.closest(".modal")?.classList.remove("ms-only"); b.remove(); }   // pley-off durang
    return;
  }
  if (!b.closest("#ms-shot")) return;
  if (b.dataset.msRow != null) { void msShotApply(Number(b.dataset.msRow)); return; }
  if (b.dataset.ms === "again") { MS.rows = null; MS.token = null; MS.pick = null; msShotRender(); return; }
  if (b.dataset.ms === "list") { MS.pick = null; msShotRender(); return; }
  if (b.dataset.ms === "close") msCloseModal("ms-shot");
}, true);
