// =============================================================
//  pt_sub.js — SHAXSIY turnir narxlari va obunalari (2026-10-03)
//  1) Narx: sig'im pog'onasi (8–20 / 24–64 / 68–128), narx 0 — sig'im yopiq.
//  2) Yaratishda to'lov turi: obuna (to'lovsiz, limit) | bir martalik.
//  3) Obuna sahifasi: tarif → buyurtma → karta + chek → holat.
//  4) Bosh admin: obuna to'lovlari (pt_payment.js ptRenderPayments chaqiradi).
//  Global: PT, PTT, apiFetch, escHtml, showToast, ptRender, ptFormatPrice, ptCopy,
//          ptCompressImage, ptLoadList, ptLoadReceiptImage.
// =============================================================

function ptPricing() { return (PT.config && PT.config.pricing) || { tiers: [], plans: [], sub_active_limit: 2 }; }
function ptSub() { return (PT.config && PT.config.subscription) || {}; }

function ptTierOf(n) {
  return ptPricing().tiers.find(t => n >= t.min && n <= t.max) || null;
}
function ptTierPrice(n) { const t = ptTierOf(n); return t ? t.price_uzs : 0; }

// Obuna bilan yaratish mumkinmi (faol obuna va limit)
function ptSubUsable() {
  const s = ptSub();
  return !!(s.active && s.active_tournaments < s.limit);
}

// Narx pog'onalari serverdan kelmagan bo'lsa (eski backend bilan qisman deploy) — avvalgi xulq:
// bitta narx (config.price_uzs), barcha sig'imlar ochiq.
function ptHasTiers() { return (ptPricing().tiers || []).length > 0; }

// Joriy to'lov turida shu sig'imni tanlash mumkinmi
function ptSizeAllowed(n, mode) {
  if (mode === "subscription" || !ptHasTiers()) return true;
  return ptTierPrice(n) > 0;
}

// ---------------- Yaratish formasi qismlari (pt.js ptRenderCreate) ----------------

function ptPayModeHtml(mode) {
  const s = ptSub();
  if (!s.active) return "";
  const full = !ptSubUsable();
  return `<div class="pt-field-label">${escHtml(PTT("pt_pay_mode"))}</div>
    <div class="pt-mode">
      <label class="pt-mode-opt ${full ? "pt-mode-opt--off" : ""}">
        <input type="radio" name="pt-mode" value="subscription" ${mode === "subscription" ? "checked" : ""} ${full ? "disabled" : ""}>
        <span>${escHtml(PTT("pt_mode_sub", { used: s.active_tournaments, limit: s.limit }))}</span></label>
      <label class="pt-mode-opt">
        <input type="radio" name="pt-mode" value="one_time" ${mode === "one_time" ? "checked" : ""}>
        <span>${escHtml(PTT("pt_mode_once"))}</span></label>
    </div>`;
}

function ptCreatePriceText(n, mode) {
  if (mode === "subscription") return { ok: true, html: `<div class="pt-price">${escHtml(PTT("pt_price_sub"))}</div>` };
  const p = ptHasTiers() ? ptTierPrice(n) : ((PT.config && PT.config.price_uzs) || 0);
  return p > 0
    ? { ok: true, html: `<div class="pt-price">${escHtml(PTT("pt_price"))}: <b>${escHtml(ptFormatPrice(p))} so'm</b></div>` }
    : { ok: false, html: `<div class="pt-warn">${escHtml(PTT("pt_price_not_set"))}</div>` };
}

function ptDefaultMode() { return ptSubUsable() ? "subscription" : "one_time"; }

// ---------------- Ro'yxat tepasidagi obuna kartasi ----------------

function ptSubCardHtml() {
  const s = ptSub(), plans = ptPricing().plans || [];
  if (s.active) {
    return `<button class="pt-card pt-sub-card pt-sub-card--on" id="pt-sub-open">
      <div class="pt-card-top"><span class="pt-card-name">⭐ ${escHtml(PTT("pt_sub_active", { plan: PTT("pt_plan_" + s.active.plan) }))}</span></div>
      <div class="pt-card-meta"><span>${escHtml(PTT("pt_sub_until", { date: s.active.expires_local }))}</span>
        <span>${escHtml(PTT("pt_sub_used", { used: s.active_tournaments, limit: s.limit }))}</span></div></button>`;
  }
  if (s.pending) {
    return `<button class="pt-card pt-sub-card" id="pt-sub-open">
      <div class="pt-card-top"><span class="pt-card-name">⭐ ${escHtml(PTT("pt_sub_order", { plan: PTT("pt_plan_" + s.pending.plan) }))}</span>
        <span class="pt-status pt-status--${escHtml(s.pending.status)}">${escHtml(ptStatusLabel(s.pending.status))}</span></div></button>`;
  }
  if (!plans.length) return "";
  return `<button class="btn btn--ghost pt-sub-buy" id="pt-sub-open">⭐ ${escHtml(PTT("pt_sub_buy"))}</button>`;
}

// ---------------- Obuna sahifasi ----------------

async function ptOpenSub() {
  PT.view = "sub";
  ptRender(`<div class="empty-state">${escHtml(PTT("pt_loading"))}</div>`);
  try {
    PT.config = await apiFetch("/pt/config");          // obuna holati yangi bo'lsin
    ptRenderSub();
  } catch (e) {
    ptRender(`<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`);
  }
}

function ptRenderSub() {
  PT.view = "sub";
  const s = ptSub(), c = PT.config || {};
  const active = s.active ? `<div class="pt-note pt-note--ok">${escHtml(PTT("pt_sub_active", { plan: PTT("pt_plan_" + s.active.plan) }))} · ${escHtml(PTT("pt_sub_until", { date: s.active.expires_local }))}</div>` : "";
  const intro = `<div class="pt-hint">${escHtml(PTT("pt_sub_intro", { limit: s.limit || 2 }))}</div>`;
  let body;
  if (s.pending) {
    const p = s.pending;
    const actions = p.status === "payment_review"
      ? `<div class="pt-note">${escHtml(PTT("pt_review_note"))}</div>`
      : `${p.status === "rejected" ? `<div class="pt-warn">${escHtml(PTT("pt_rejected_note", { reason: p.reject_reason || "—" }))}</div>` : ""}
         <input type="file" id="pt-sub-file" accept="image/*" hidden>
         <button class="btn btn--primary" id="pt-sub-receipt">${escHtml(PTT("pt_receipt_btn"))}</button>
         <button class="btn btn--ghost" id="pt-sub-cancel">${escHtml(PTT("pt_sub_cancel"))}</button>`;
    body = `<div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_sub_order", { plan: PTT("pt_plan_" + p.plan) }))}</div>
      ${p.status !== "payment_review" ? `
      <div class="pt-hint">${escHtml(PTT("pt_pay_text", { price: ptFormatPrice(p.price_uzs) }))}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_card"))}</span><b class="pt-mono">${escHtml(c.card_number || "—")}</b>
        ${c.card_number ? `<button class="pt-copy" data-pt-copy="${escHtml(c.card_number.replace(/\s/g, ""))}">${escHtml(PTT("pt_copy"))}</button>` : ""}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_card_holder"))}</span><b>${escHtml(c.card_holder || "—")}</b></div>` : ""}
      ${actions}</div>`;
  } else {
    const plans = (ptPricing().plans || []).map(pl => `
      <button class="pt-card pt-plan" data-pt-plan="${escHtml(pl.plan)}">
        <div class="pt-card-top"><span class="pt-card-name">${escHtml(PTT("pt_plan_title_" + pl.plan))}</span>
          <b>${escHtml(ptFormatPrice(pl.price_uzs))} so'm</b></div>
        <div class="pt-card-meta"><span>${escHtml(PTT("pt_plan_days", { days: pl.days }))}</span>
          <span>${escHtml(PTT(s.active ? "pt_plan_extend" : "pt_plan_choose"))}</span></div></button>`).join("");
    body = plans || `<div class="empty-state">${escHtml(PTT("pt_sub_none"))}</div>`;
  }
  ptRender(`<div class="section-label pt-label">⭐ ${escHtml(PTT("pt_sub_title"))}</div>${active}${intro}${body}`);
  document.querySelectorAll("#pt-root [data-pt-plan]").forEach(b => b.addEventListener("click", () => void ptSubOrder(b.dataset.ptPlan)));
  document.querySelectorAll("#pt-root [data-pt-copy]").forEach(b => b.addEventListener("click", () => ptCopy(b.dataset.ptCopy)));
  const file = document.getElementById("pt-sub-file");
  document.getElementById("pt-sub-receipt")?.addEventListener("click", () => file.click());
  file?.addEventListener("change", () => { const f = file.files && file.files[0]; if (f) void ptSubUpload(f); file.value = ""; });
  document.getElementById("pt-sub-cancel")?.addEventListener("click", () => void ptSubCancel());
}

async function ptSubAction(path, body, okKey) {
  if (PT.busy) return;
  PT.busy = true;
  try {
    await apiFetch(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
    if (okKey) showToast(PTT(okKey));
  } catch (e) {
    const map = { plan_unavailable: "pt_err_plan", pending_exists: "pt_err_pending", bad_image: "pt_err_image",
                  empty_image: "pt_err_image", image_too_large: "pt_err_image_large", wrong_status: "pt_err_wrong_status" };
    showToast(PTT(map[e && e.message] || "pt_err_generic"));
  } finally {
    PT.busy = false;
  }
  await ptOpenSub();
}

function ptSubOrder(plan) { return ptSubAction("/pt/sub/order", { plan }, null); }

async function ptSubUpload(file) {
  const p = ptSub().pending;
  if (!p) return;
  let dataUrl;
  try { dataUrl = await ptCompressImage(file); } catch (e) { showToast(PTT("pt_err_image")); return; }
  return ptSubAction(`/pt/sub/${encodeURIComponent(p.id)}/receipt`, { image_base64: dataUrl }, "pt_receipt_sent");
}

function ptSubCancel() {
  const p = ptSub().pending;
  if (!p || !window.confirm(PTT("pt_sub_cancel_ask"))) return;
  return ptSubAction(`/pt/sub/${encodeURIComponent(p.id)}/cancel`, null, null);
}

// ---------------- Bosh admin: obuna to'lovlari ----------------

function ptSubPaymentsHtml(subs) {
  if (!subs || !subs.length) return "";
  return `<div class="section-label pt-label">${escHtml(PTT("pt_sub_payments"))}</div>` + subs.map(s => `
    <div class="card pt-pay-item">
      <div class="pt-card-top"><span class="pt-card-name">⭐ ${escHtml(PTT("pt_plan_title_" + s.plan))}</span><span class="pt-muted">#${s.id}</span></div>
      <div class="pt-card-meta"><span>${escHtml(s.owner_username ? "@" + s.owner_username : (s.owner_nickname || ""))}</span>
        <b>${escHtml(ptFormatPrice(s.price_uzs))} so'm</b></div>
      <div class="pt-receipt-box" id="pt-receipt-sub-${s.id}">${escHtml(PTT("pt_loading"))}</div>
      <input class="modal-input" id="pt-reason-sub-${s.id}" maxlength="200" placeholder="${escHtml(PTT("pt_reject_ph"))}">
      <div class="pt-pay-actions">
        <button class="btn btn--ghost" data-pt-sreject="${s.id}">${escHtml(PTT("pt_reject"))}</button>
        <button class="btn btn--primary" data-pt-sapprove="${s.id}">${escHtml(PTT("pt_approve"))}</button>
      </div></div>`).join("");
}

function ptBindSubPayments(subs) {
  (subs || []).forEach(s => void ptLoadReceiptImage(s.id, `/pt/admin/sub/${encodeURIComponent(s.id)}/receipt`, `pt-receipt-sub-${s.id}`));
  document.querySelectorAll("#pt-root [data-pt-sapprove]").forEach(b =>
    b.addEventListener("click", () => void ptReview(b.dataset.ptSapprove, "approve", b, "sub")));
  document.querySelectorAll("#pt-root [data-pt-sreject]").forEach(b =>
    b.addEventListener("click", () => void ptReview(b.dataset.ptSreject, "reject", b, "sub")));
}
