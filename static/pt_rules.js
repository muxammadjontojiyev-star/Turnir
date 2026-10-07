// =============================================================
//  pt_rules.js — SHAXSIY turnir qoidalari (2026-10-07)
//  Asosiy sahifada hamma ko'radi; FAQAT tashkilotchi tahrirlaydi (server ham tekshiradi:
//  POST /pt/{id}/rules -> not_owner). Bo'sh — standart qoidalar (pt_rules_default, 3 tilda).
//  Har qator — bitta qoida (raqamlangan ro'yxat). Global: PT, PTT, escHtml, apiFetch,
//  showToast, ptRenderDetailTabs.
// =============================================================

const PT_RULES_MAX = 2000;           // server bilan bir xil (pt_rules.py)
const PT_RULES_PREVIEW = 4;          // yig'iq holatda ko'rinadigan qoidalar soni

function ptRulesText(t) { return (t.rules || "").trim() || PTT("pt_rules_default"); }

function ptRulesItems(text) {
  return text.split("\n").map(s => s.trim().replace(/^(\d+[.)]|[-•*–])\s*/, "")).filter(Boolean);
}

function ptRulesHtml(t) {
  const isDefault = !(t.rules || "").trim();
  const editBtn = t.is_owner && t.status !== "cancelled" && !PT.rulesEdit
    ? `<button class="pt-mini pt-mini--edit" id="pt-rules-edit">${escHtml(PTT("pt_rules_edit"))}</button>` : "";
  const head = `<div class="pt-rules-head"><span class="pt-next-kicker">${escHtml(PTT("pt_rules_title"))}</span>
${editBtn}</div>`;
  const defTag = isDefault ? `<span class="pt-tag pt-tag--muted">${escHtml(PTT("pt_rules_default_tag"))}</span>` : "";
  if (PT.rulesEdit && t.is_owner) {
    return `<div class="card pt-rules">${head}
        <textarea class="modal-input pt-rules-input" id="pt-rules-input" maxlength="${PT_RULES_MAX}" rows="9">${escHtml(ptRulesText(t))}</textarea>
        <div class="pt-rules-meta"><span class="pt-hint">${escHtml(PTT("pt_rules_hint"))}</span>
          <span class="pt-muted" id="pt-rules-count">${ptRulesText(t).length}/${PT_RULES_MAX}</span></div>
        <div class="pt-pay-actions">
          <button class="btn btn--ghost" id="pt-rules-cancel">${escHtml(PTT("pt_rules_cancel"))}</button>
          <button class="btn btn--primary" id="pt-rules-save">${escHtml(PTT("pt_rules_save"))}</button></div>
        ${isDefault ? "" : `<button class="pt-linkbtn" id="pt-rules-reset">${escHtml(PTT("pt_rules_reset"))}</button>`}
      </div>`;
  }
  const items = ptRulesItems(ptRulesText(t));
  const long = items.length > PT_RULES_PREVIEW;
  const shown = long && !PT.rulesOpen ? items.slice(0, PT_RULES_PREVIEW) : items;
  return `<div class="card pt-rules">${head}
      <ol class="pt-rules-list">${shown.map(x => `<li>${escHtml(x)}</li>`).join("")}</ol>
      <div class="pt-rules-foot">${long ? `<button class="pt-linkbtn" id="pt-rules-toggle">${escHtml(PTT(PT.rulesOpen ? "pt_rules_less" : "pt_rules_more"))}</button>` : "<span></span>"}${defTag}</div>
    </div>`;
}

function ptBindRules(t) {
  const rerender = () => { if (typeof ptRenderDetailTabs === "function") ptRenderDetailTabs(); };
  document.getElementById("pt-rules-toggle")?.addEventListener("click", () => { PT.rulesOpen = !PT.rulesOpen; rerender(); });
  document.getElementById("pt-rules-edit")?.addEventListener("click", () => {
    PT.rulesEdit = true; rerender();
    document.getElementById("pt-rules-input")?.focus();
  });
  document.getElementById("pt-rules-cancel")?.addEventListener("click", () => { PT.rulesEdit = false; rerender(); });
  const input = document.getElementById("pt-rules-input");
  input?.addEventListener("input", () => {
    const c = document.getElementById("pt-rules-count");
    if (c) c.textContent = `${input.value.length}/${PT_RULES_MAX}`;
  });
  document.getElementById("pt-rules-save")?.addEventListener("click", () => {
    // standart matn o'zgartirilmagan bo'lsa — NULL saqlanadi (til almashsa ham tarjima qilinadi)
    const v = (input?.value || "").trim();
    void ptSaveRules(t, v === PTT("pt_rules_default").trim() ? "" : v);
  });
  document.getElementById("pt-rules-reset")?.addEventListener("click", () => void ptSaveRules(t, ""));
}

async function ptSaveRules(t, text) {
  if (PT.busy) return;                       // ikki marta bosish (qoida #38)
  if (text.length > PT_RULES_MAX) { showToast(PTT("pt_rules_too_long")); return; }
  PT.busy = true;
  try {
    const r = await apiFetch(`/pt/${encodeURIComponent(t.id)}/rules`, { method: "POST", body: JSON.stringify({ rules: text }) });
    if (PT.detail && String(PT.detail.id) === String(t.id)) PT.detail.rules = r.rules || null;
    PT.rulesEdit = false;
    showToast(PTT("pt_rules_saved"));
  } catch (e) {
    const map = { too_long: "pt_rules_too_long", not_owner: "pt_rules_owner_only" };
    showToast(PTT(map[e && e.message] || "pt_err_generic"));
  } finally {
    PT.busy = false;
  }
  if (typeof ptRenderDetailTabs === "function") ptRenderDetailTabs();
}
