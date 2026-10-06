// =============================================================
//  pt.js — SHAXSIY turnirlar ekrani (2026-10-02, 1-bosqich)
//  Ko'rinishlar: list (mening turnirlarim) | create | detail.
//  Global: APP, apiFetch, escHtml, showToast, ICON, PTT, showHubSelect.
//  Barcha foydalanuvchi matni escHtml orqali (qoida #35).
// =============================================================

const PT = {
  view: "list",        // list | create | detail | payments | join
  payments: [],
  list: [],
  config: null,
  detail: null,
  detailId: null,
  busy: false,
};

// joinCode: taklif havolasi orqali kelinsa (pt_members.js) — ro'yxat o'rniga qo'shilish ekrani
function showPrivateTournaments(joinCode) {
  document.getElementById("hub-select")?.classList.add("hidden");
  document.getElementById("mode-select")?.classList.add("hidden");
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelector(".bottom-nav")?.classList.add("hidden");

  let root = document.getElementById("pt-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "pt-root";
    (document.querySelector("main") || document.body).appendChild(root);
  }
  root.classList.remove("hidden");
  if (joinCode && typeof ptOpenJoin === "function") { void ptOpenJoin(joinCode); return; }
  PT.view = "list";
  void ptLoadList();
}

function exitPrivateTournaments() {
  document.getElementById("pt-root")?.classList.add("hidden");
  if (typeof showHubSelect === "function") showHubSelect();
}

function ptStatusLabel(status) {
  return PTT("pt_status_" + status) || status;
}

function ptFormatPrice(n) {
  return Number(n || 0).toLocaleString("ru-RU").replace(/,/g, " ");
}

// --- Yuklash -------------------------------------------------------------

async function ptLoadList() {
  ptRender(`<div class="empty-state">${escHtml(PTT("pt_loading"))}</div>`);
  try {
    const [my, cfg] = await Promise.all([apiFetch("/pt/my"), apiFetch("/pt/config")]);
    PT.list = my.tournaments || [];
    PT.config = cfg;
    ptRenderList();
  } catch (e) {
    ptRender(`<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`);
  }
}

async function ptOpenDetail(id) {
  if (String(PT.detailId) !== String(id)) PT.tab = "home";   // boshqa turnir — Asosiy sahifadan
  PT.view = "detail";
  PT.detailId = id;
  ptRender(`<div class="empty-state">${escHtml(PTT("pt_loading"))}</div>`);
  try {
    if (!PT.config) PT.config = await apiFetch("/pt/config");
    PT.detail = await apiFetch(`/pt/${encodeURIComponent(id)}`);
    PT.play = null;
    // O'yin ma'lumoti bir marta yuklanadi — sahifalar orasida o'tish so'rovsiz (pt_tabs.js)
    if (["running", "finished"].includes(PT.detail.status) && typeof ptFetchPlay === "function") {
      await ptFetchPlay(id);
    }
    ptRenderDetail();
  } catch (e) {
    ptRender(`<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`);
  }
}

// --- Chizish -------------------------------------------------------------

// nav — ixtiyoriy pastki menyu (turnir sahifalari, pt_tabs.js)
function ptRender(body, nav) {
  const root = document.getElementById("pt-root");
  if (!root) return;
  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="pt-back-btn">←</button>
      <div class="wc-header-title pt-title">${ICON.get("swords", 20)} <span>${escHtml(PTT("pt_title"))}</span></div>
    </div>
    <div class="wc-body pt-body${nav ? " pt-body--nav" : ""}">${body}</div>${nav || ""}`;
  if (nav && typeof applyIcons === "function") applyIcons(root);
  document.getElementById("pt-back-btn").addEventListener("click", () => {
    if (PT.view === "list") exitPrivateTournaments();
    else { PT.view = "list"; void ptLoadList(); }
  });
}

function ptRenderList() {
  PT.view = "list";
  const cards = PT.list.map(t => `
    <button class="pt-card" data-pt-open="${t.id}">
      <div class="pt-card-top">
        <span class="pt-card-name">${escHtml(t.name)}</span>
        ${t.is_owner ? `<span class="pt-tag">${escHtml(PTT("pt_owner_tag"))}</span>`
          : t.is_admin ? `<span class="pt-tag pt-tag--admin">${escHtml(PTT("pt_admin_tag"))}</span>` : ""}
      </div>
      <div class="pt-card-meta">
        <span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span>
        <span>${t.members_count} ${escHtml(PTT("pt_members"))}</span>
      </div>
    </button>`).join("");

  // Bosh admin: to'lovlar navbati (2-bosqich, pt_payment.js)
  const adminBtn = (PT.config && PT.config.is_super)
    ? `<button class="btn btn--ghost" id="pt-payments-btn">${escHtml(PTT("pt_payments_btn"))}</button>` : "";
  const subCard = typeof ptSubCardHtml === "function" ? ptSubCardHtml() : "";   // 2026-10-03
  ptRender(`
    ${adminBtn}
    ${subCard}
    <button class="btn btn--primary btn--glow" id="pt-new-btn">${escHtml(PTT("pt_new"))}</button>
    <div class="section-label pt-label">${escHtml(PTT("pt_my"))}</div>
    ${cards || `<div class="empty-state">${escHtml(PTT("pt_empty"))}</div>`}`);

  document.getElementById("pt-new-btn").addEventListener("click", ptRenderCreate);
  document.getElementById("pt-payments-btn")?.addEventListener("click", () => void ptOpenPayments());
  document.getElementById("pt-sub-open")?.addEventListener("click", () => void ptOpenSub());
  document.querySelectorAll("#pt-root [data-pt-open]").forEach(el =>
    el.addEventListener("click", () => void ptOpenDetail(el.dataset.ptOpen)));
}

function ptRenderCreate(keep) {
  PT.view = "create";
  const c = PT.config || {};
  // 2026-10-03: to'lov turi (obuna | bir martalik) va sig'im pog'onasiga qarab narx (pt_sub.js)
  const mode = (keep && keep.mode) || PT.createMode || (typeof ptDefaultMode === "function" ? ptDefaultMode() : "one_time");
  PT.createMode = mode;
  const allow = n => (typeof ptSizeAllowed === "function" ? ptSizeAllowed(n, mode) : true);
  let size = Number((keep && keep.size) || c.default_players || 8);
  if (!allow(size)) {   // tanlangan sig'im shu to'lov turida yopiq — undan kichik eng yaqin ochig'iga (yo'q bo'lsa birinchisiga)
    const step = c.group_size || 4, lo = c.min_players || 8, hi = c.max_players || 128;
    let pick = null;
    for (let n = Math.min(size, hi); n >= lo; n -= step) { if (allow(n)) { pick = n; break; } }
    if (pick === null) for (let n = lo; n <= hi; n += step) { if (allow(n)) { pick = n; break; } }
    if (pick !== null) size = pick;
  }
  const price = typeof ptCreatePriceText === "function" ? ptCreatePriceText(size, mode) : { ok: c.price_set, html: "" };
  const modeHtml = typeof ptPayModeHtml === "function" ? ptPayModeHtml(mode) : "";
  const priceBlock = `<div id="pt-price-box">${price.html}</div>`;
  ptRender(`
    <div class="card pt-form">
      <div class="section-label pt-label">${escHtml(PTT("pt_create_title"))}</div>
      <label class="pt-field-label" for="pt-name">${escHtml(PTT("pt_name_label"))}</label>
      <input class="modal-input" id="pt-name" maxlength="${c.name_max || 40}"
             placeholder="${escHtml(PTT("pt_name_ph"))}" autocomplete="off">
      <label class="pt-field-label" for="pt-size">${escHtml(PTT("pt_size_label"))}</label>
      ${ptSizeSelectHtml("pt-size", size, 0, allow)}
      ${modeHtml}
      <div class="pt-hint">${escHtml(PTT("pt_format", { min: c.min_players || 8 }))}</div>
      ${priceBlock}
      <button class="btn btn--primary" id="pt-create-btn" ${price.ok ? "" : "disabled"}>
        ${escHtml(PTT("pt_create_btn"))}</button>
    </div>`);
  if (keep && keep.name) document.getElementById("pt-name").value = keep.name;
  document.getElementById("pt-create-btn").addEventListener("click", ptCreateSubmit);
  const snapshot = () => ({ name: document.getElementById("pt-name").value,
                            size: Number(document.getElementById("pt-size").value) });
  document.getElementById("pt-size").addEventListener("change", () => {
    const p = ptCreatePriceText(Number(document.getElementById("pt-size").value), PT.createMode);
    document.getElementById("pt-price-box").innerHTML = p.html;
    document.getElementById("pt-create-btn").disabled = !p.ok;
  });
  document.querySelectorAll("#pt-root input[name='pt-mode']").forEach(r =>
    r.addEventListener("change", () => ptRenderCreate({ ...snapshot(), mode: r.value })));
}

async function ptCreateSubmit() {
  if (PT.busy) return;                       // ikki marta bosish (qoida #38)
  const input = document.getElementById("pt-name");
  const btn = document.getElementById("pt-create-btn");
  const name = (input.value || "").trim();
  PT.busy = true;
  btn.disabled = true;
  btn.textContent = PTT("pt_creating");
  try {
    const max_players = Number(document.getElementById("pt-size")?.value || 8);
    const pay_mode = PT.createMode || "one_time";
    const r = await apiFetch("/pt/create", { method: "POST", body: JSON.stringify({ name, max_players, pay_mode }) });
    showToast(PTT("pt_created"));
    await ptOpenDetail(r.id);
  } catch (e) {
    const map = { name_too_short: "pt_err_name_short", name_too_long: "pt_err_name_long", bad_size: "pt_err_bad_size",
                  no_subscription: "pt_err_no_sub", sub_limit: "pt_err_sub_limit",
                  too_many_unpaid: "pt_err_too_many", price_not_set: "pt_price_not_set" };
    const code = (e && (e.detail || e.message)) || "";
    showToast(PTT(map[code] || "pt_err_generic"));
    btn.disabled = false;
    btn.textContent = PTT("pt_create_btn");
  } finally {
    PT.busy = false;
  }
}

// To'lov bloki (faqat tashkilotchi): kutilmoqda/rad etilgan — karta + chek; tekshiruvda — izoh
function ptPayBlockHtml(t) {
  const c = PT.config || {};
  const payStatuses = ["awaiting_payment", "rejected", "payment_review"];
  if (!(t.is_owner && payStatuses.includes(t.status))) return "";
  const showCard = t.status !== "payment_review";
  return `
    <div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_pay_title"))}</div>
      ${showCard ? `
      <div class="pt-hint">${escHtml(PTT("pt_pay_text", { price: ptFormatPrice(t.price_uzs) }))}</div>
      <div class="pt-card-row">
        <span>${escHtml(PTT("pt_card"))}</span>
        <b class="pt-mono">${escHtml(c.card_number || "—")}</b>
        ${c.card_number ? `<button class="pt-copy" data-pt-copy="${escHtml(c.card_number.replace(/\s/g, ""))}">${escHtml(PTT("pt_copy"))}</button>` : ""}
      </div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_card_holder"))}</span><b>${escHtml(c.card_holder || "—")}</b></div>` : ""}
      ${typeof ptPaymentActionsHtml === "function" ? ptPaymentActionsHtml(t) : ""}
    </div>`;
}

// Turnir sarlavha kartasi (barcha sahifalar tepasida)
function ptHeadHtml(t) {
  return `
    <div class="card pt-head">
      <div class="pt-head-name">${escHtml(t.name)}</div>
      <div class="pt-card-meta">
        <span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span>
        <span>${t.approved_count}/${t.max_players} ${escHtml(PTT("pt_members"))}</span>
      </div>
    </div>`;
}

// 2026-10-03: turnir sahifasi pastki menyuli sahifalarga bo'lingan — pt_tabs.js
function ptRenderDetail() {
  if (typeof ptRenderDetailTabs === "function") ptRenderDetailTabs();
}

function ptCopy(text) {
  const done = () => showToast(PTT("pt_copied"));
  const fallback = () => {
    const ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); done(); } catch (_) { showToast(text); }
    document.body.removeChild(ta);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(fallback);
  } else {
    fallback();
  }
}

// Til almashganda joriy ko'rinishni qayta chizadi (app.js cycleLanguage chaqiradi)
function ptRerender() {
  if (PT.view === "create") ptRenderCreate();
  else if (PT.view === "sub" && typeof ptRenderSub === "function") ptRenderSub();
  else if (PT.view === "payments" && typeof ptRenderPayments === "function") ptRenderPayments();
  else if (PT.view === "join" && PT.invite && typeof ptRenderJoin === "function") ptRenderJoin();
  else if (PT.view === "detail" && PT.detail) ptRenderDetail();
  else ptRenderList();
}
