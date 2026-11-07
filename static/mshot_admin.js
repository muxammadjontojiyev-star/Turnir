// =============================================================
//  mshot_admin.js — «📸 SKRINSHOT VA TEXNIK G'ALABA» (2026-11-06). Bosh admin — hammasi (asosiy Admin panel),
//  liga admini — o'z ligasi (asosiy Admin panel), rejim adminlari — o'z rejimining Admin bo'limida
//  (server: match_claims.admin_list + can_review). Guruh ochilganda yuklanadi.
//  Ishlar: texnik g'alaba so'rovi (3:0 / rad), skrinshotli natijaga e'tiroz va katta hisob (to'g'ri / tuzatish).
//  API: GET /mshot/admin/list, GET /mshot/admin/img/{kind}/{id}/{idx}, POST /mshot/admin/decide.
//  Global: apiFetch, escHtml, showToast, msT, msErr.
// =============================================================

const MSA = { items: [], busy: false };

function msaMode(m) { return msT(`ms_mode_${m}`); }

function msaItemHtml(it) {
  const head = `<div class="msa-head"><b>${escHtml(msaMode(it.mode))} · #${Number(it.match_id)}</b>
      <span class="msa-kind">${escHtml(msT(it.kind === "tech" ? "ms_adm_tech" : it.status === "admin_pending" ? "ms_adm_pending" : "ms_adm_dispute"))}</span></div>`;
  const imgs = it.kind === "tech" ? Number(it.n_img) || 0 : 1;
  const imgBtns = Array.from({ length: imgs }, (_, i) =>
    `<button class="btn btn--ghost msa-img-btn" data-msa-img="${i}">${escHtml(msT("ms_adm_show"))}${imgs > 1 ? ` ${i + 1}` : ""}</button>`).join("");
  if (it.kind === "tech") {
    return `<div class="card msa-item" data-msa-kind="tech" data-msa-id="${Number(it.id)}">${head}
        <div class="msa-line">⚠️ <b>${escHtml(it.claimant_name || "")}</b> → ${escHtml(it.opponent_name || "")}</div>
        ${it.note ? `<div class="msa-note">${escHtml(it.note)}</div>` : ""}
        <div class="msa-imgs">${imgBtns}</div><div class="msa-pics"></div>
        <div class="msa-acts">
          <button class="btn btn--primary" data-msa="tech_win" data-msa-who="${escHtml(it.claimant_name || "")}">${escHtml(msT("ms_adm_win"))}</button>
          <button class="btn btn--ghost" data-msa="reject">${escHtml(msT("ms_adm_reject"))}</button>
        </div></div>`;
  }
  return `<div class="card msa-item" data-msa-kind="shot" data-msa-id="${Number(it.id)}">${head}
      <div class="msa-line">📸 ${escHtml(it.uploader_name || "")} · ${escHtml((it.played_at || "").replace("T", " ").slice(0, 16))}</div>
      <div class="msa-line">${escHtml(msT("ms_adm_fix"))}: <input class="modal-input msa-s" data-msa-s="1" type="number" min="0" max="99" value="${Number(it.score1)}">
        : <input class="modal-input msa-s" data-msa-s="2" type="number" min="0" max="99" value="${Number(it.score2)}"></div>
      <div class="msa-imgs">${imgBtns}</div><div class="msa-pics"></div>
      <div class="msa-acts">
        <button class="btn btn--primary" data-msa="uphold">${escHtml(msT("ms_adm_uphold"))}</button>
        <button class="btn btn--ghost" data-msa="set">${escHtml(msT("ms_adm_fix"))}</button>
      </div></div>`;
}

// Guruh — <details class="msa-group" data-msa-modes="cl,cl_po">: asosiy Admin panelda (hammasi, server huquq bo'yicha
// filtrlaydi) va har rejimning o'z Admin bo'limida (faqat o'sha rejim) — 2026-11-06.
const MSA_TTL_MS = 30 * 1000;
const MSA_CACHE = new Map();                 // modes → {items, at}

async function msaLoad(group, force = true) {
  group = group || document.getElementById("mshot-adm-group");
  if (!group) return;
  const box = group.querySelector(".msa-list");
  const modes = group.dataset.msaModes || "";
  const c = MSA_CACHE.get(modes);
  let items;
  if (!force && c && Date.now() - c.at < MSA_TTL_MS) items = c.items;
  else {
    try { items = (await apiFetch(`/mshot/admin/list${modes ? `?modes=${encodeURIComponent(modes)}` : ""}`)).items || []; }
    catch (e) { if (box) box.innerHTML = `<div class="adm-pp-hint">${escHtml(msErr(e))}</div>`; return; }
    MSA_CACHE.set(modes, { items, at: Date.now() });
  }
  MSA.items = items;
  const cnt = group.querySelector(".msa-count");
  if (cnt) cnt.textContent = items.length ? String(items.length) : "";
  if (!box) return;
  const head = modes ? "" : (await msaOnlyHtml()) + (typeof crAdminHtml === "function" ? await crAdminHtml() : "");   // 2026-11-07: javob kechikishi chegarasi
  box.innerHTML = head + (items.length ? items.map(msaItemHtml).join("")
    : `<div class="adm-pp-hint">${escHtml(msT("ms_adm_empty"))}</div>`);
}

// rejimlarning o'z Admin bo'limiga guruh qo'shiladi (rejim fayllariga tegilmaydi — DOM kuzatiladi)
const MSA_TARGETS = [
  { modes: "div", box: () => (typeof DIV !== "undefined" && DIV.section === "admin" ? document.querySelector("#div-root .wc-body") : null) },
  { modes: "cl,cl_po", box: () => document.getElementById("cl-admin-page") },
  { modes: "el,el_po", box: () => document.getElementById("el-admin-page") },
  { modes: "ac,ac_po", box: () => document.getElementById("ac-admin-page") },
  { modes: "co,co_po", box: () => document.getElementById("co-admin-page") },
  { modes: "wc,wc_po", box: () => { const b = document.getElementById("wc-admin-panel"); return b && !b.classList.contains("hidden") ? b : null; } },
];
function msaGroupHtml(modes) {
  return `<details class="adm-group msa-group" data-msa-modes="${escHtml(modes)}">
      <summary><span class="adm-group-ic">📸</span><span>${escHtml(msT("ms_adm_title"))}</span><span class="adm-group-sub msa-count"></span></summary>
      <div class="msa-list"></div>
    </details>`;
}
function msaMount() {
  for (const t of MSA_TARGETS) {
    const box = t.box();
    if (!box || box.querySelector(":scope > .msa-group")) continue;
    box.insertAdjacentHTML("afterbegin", msaGroupHtml(t.modes));
    void msaLoad(box.querySelector(":scope > .msa-group"), false);
  }
}
let _msaT = 0;
// throttle (debounce emas): DOM har kadrda o'zgarsa ham (animatsiyalar) — ishlaydi
new MutationObserver(() => { if (_msaT) return; _msaT = requestAnimationFrame(() => { _msaT = 0; msaMount(); }); })
  .observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] });

// Bosh admin — «natija faqat skrinshot bilan» kaliti (favqulodda: skrinshot o'qish ishlamay qolsa — o'chiriladi)
async function msaOnlyHtml() {
  try {
    if (!(await apiFetch("/admin/whoami")).is_super) return "";
    const on = !!(await apiFetch("/mshot/config")).shot_only;
    return `<div class="card msa-only"><div class="msa-line"><b>${escHtml(msT(on ? "ms_adm_only_on" : "ms_adm_only_off"))}</b></div>
      <div class="adm-pp-hint">${escHtml(msT("ms_adm_only_hint"))}</div>
      <button class="btn ${on ? "" : "btn--primary"}" data-msa-only="${on ? "0" : "1"}" style="width:100%;margin-top:6px">${escHtml(msT(on ? "ms_adm_only_disable" : "ms_adm_only_enable"))}</button></div>`;
  } catch (_) { return ""; }
}

async function msaToggleOnly(btn) {
  const on = btn.dataset.msaOnly === "1";
  if (!window.confirm(msT(on ? "ms_adm_only_q_on" : "ms_adm_only_q_off"))) return;
  btn.disabled = true;
  try {
    await apiFetch("/mshot/admin/only", { method: "POST", body: JSON.stringify({ on }) });
    showToast(msT("ms_adm_done"));
    if (typeof msLoadConfig === "function") void msLoadConfig();
  } catch (e) { showToast(msErr(e)); }
  await msaLoad(btn.closest(".msa-group"));
}

async function msaShowImg(card, idx) {
  const kind = card.dataset.msaKind, id = card.dataset.msaId;
  const pics = card.querySelector(".msa-pics");
  if (pics.querySelector(`[data-msa-pic="${idx}"]`)) return;
  try {
    const r = await apiFetch(`/mshot/admin/img/${kind}/${id}/${idx}`);
    if (!/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/.test(r.data || "")) return;
    pics.insertAdjacentHTML("beforeend", `<img class="msa-pic" data-msa-pic="${Number(idx)}" src="${r.data}" alt="">`);
  } catch (e) { showToast(msErr(e)); }
}

async function msaDecide(card, btn) {
  if (MSA.busy) return;
  const action = btn.dataset.msa;
  if (action === "tech_win" && !window.confirm(msT("ms_adm_q_win", { who: btn.dataset.msaWho || "" }))) return;
  const body = { kind: card.dataset.msaKind, id: Number(card.dataset.msaId), action };
  if (action === "set") {
    body.s1 = Number(card.querySelector('[data-msa-s="1"]').value || 0);
    body.s2 = Number(card.querySelector('[data-msa-s="2"]').value || 0);
  }
  MSA.busy = true; btn.disabled = true;
  try {
    await apiFetch("/mshot/admin/decide", { method: "POST", body: JSON.stringify(body) });
    showToast(msT("ms_adm_done"));
    MSA_CACHE.clear();
    await msaLoad(card.closest(".msa-group"));
  } catch (e) { showToast(msErr(e)); btn.disabled = false; }
  finally { MSA.busy = false; }
}

document.addEventListener("click", (e) => {
  const only = e.target.closest ? e.target.closest("[data-msa-only]") : null;
  if (only) { void msaToggleOnly(only); return; }
  const card = e.target.closest ? e.target.closest(".msa-item") : null;
  if (!card) return;
  const img = e.target.closest("[data-msa-img]");
  if (img) { void msaShowImg(card, Number(img.dataset.msaImg)); return; }
  const act = e.target.closest("[data-msa]");
  if (act) void msaDecide(card, act);
});
document.addEventListener("toggle", (e) => {
  if (e.target && e.target.classList && e.target.classList.contains("msa-group") && e.target.open) void msaLoad(e.target);
}, true);
