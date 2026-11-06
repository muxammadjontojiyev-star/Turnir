// =============================================================
//  mshot_admin.js — Admin → «📸 SKRINSHOT VA TEXNIK G'ALABA» (2026-11-06). Bosh admin — hammasi,
//  liga admini — o'z ligalari (server: match_claims.admin_list). Guruh ochilganda yuklanadi.
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

async function msaLoad() {
  const box = document.getElementById("mshot-adm-list");
  if (!box) return;
  try { MSA.items = (await apiFetch("/mshot/admin/list")).items || []; }
  catch (e) { box.innerHTML = `<div class="adm-pp-hint">${escHtml(msErr(e))}</div>`; return; }
  const cnt = document.getElementById("mshot-adm-count");
  if (cnt) cnt.textContent = MSA.items.length ? String(MSA.items.length) : "";
  box.innerHTML = MSA.items.length ? MSA.items.map(msaItemHtml).join("")
    : `<div class="adm-pp-hint">${escHtml(msT("ms_adm_empty"))}</div>`;
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
    await msaLoad();
  } catch (e) { showToast(msErr(e)); btn.disabled = false; }
  finally { MSA.busy = false; }
}

document.addEventListener("click", (e) => {
  const card = e.target.closest ? e.target.closest(".msa-item") : null;
  if (!card) return;
  const img = e.target.closest("[data-msa-img]");
  if (img) { void msaShowImg(card, Number(img.dataset.msaImg)); return; }
  const act = e.target.closest("[data-msa]");
  if (act) void msaDecide(card, act);
});
document.addEventListener("toggle", (e) => {
  if (e.target && e.target.id === "mshot-adm-group" && e.target.open) void msaLoad();
}, true);
