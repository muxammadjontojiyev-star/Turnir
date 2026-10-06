// =============================================================
//  pt.js — SHAXSIY turnirlar ekrani (2026-10-02, 1-bosqich)
//  Ko'rinishlar: list (mening turnirlarim) | create | detail.
//  Global: APP, apiFetch, escHtml, showToast, ICON, PTT, showHubSelect.
//  Barcha foydalanuvchi matni escHtml orqali (qoida #35).
// =============================================================

const PT = {
  view: "list",        // list | create | detail
  list: [],
  config: null,
  detail: null,
  detailId: null,
  busy: false,
};

function showPrivateTournaments() {
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
  PT.view = "detail";
  PT.detailId = id;
  ptRender(`<div class="empty-state">${escHtml(PTT("pt_loading"))}</div>`);
  try {
    if (!PT.config) PT.config = await apiFetch("/pt/config");
    PT.detail = await apiFetch(`/pt/${encodeURIComponent(id)}`);
    ptRenderDetail();
  } catch (e) {
    ptRender(`<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`);
  }
}

// --- Chizish -------------------------------------------------------------

function ptRender(body) {
  const root = document.getElementById("pt-root");
  if (!root) return;
  root.innerHTML = `
    <div class="wc-header">
      <button class="wc-back" id="pt-back-btn">←</button>
      <div class="wc-header-title pt-title">${ICON.get("swords", 20)} <span>${escHtml(PTT("pt_title"))}</span></div>
    </div>
    <div class="wc-body pt-body">${body}</div>`;
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
        ${t.is_owner ? `<span class="pt-tag">${escHtml(PTT("pt_owner_tag"))}</span>` : ""}
      </div>
      <div class="pt-card-meta">
        <span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span>
        <span>${t.members_count} ${escHtml(PTT("pt_members"))}</span>
      </div>
    </button>`).join("");

  ptRender(`
    <button class="btn btn--primary btn--glow" id="pt-new-btn">${escHtml(PTT("pt_new"))}</button>
    <div class="section-label pt-label">${escHtml(PTT("pt_my"))}</div>
    ${cards || `<div class="empty-state">${escHtml(PTT("pt_empty"))}</div>`}`);

  document.getElementById("pt-new-btn").addEventListener("click", ptRenderCreate);
  document.querySelectorAll("#pt-root [data-pt-open]").forEach(el =>
    el.addEventListener("click", () => void ptOpenDetail(el.dataset.ptOpen)));
}

function ptRenderCreate() {
  PT.view = "create";
  const c = PT.config || {};
  const priceBlock = c.price_set
    ? `<div class="pt-price">${escHtml(PTT("pt_price"))}: <b>${escHtml(ptFormatPrice(c.price_uzs))} so'm</b></div>`
    : `<div class="pt-warn">${escHtml(PTT("pt_price_not_set"))}</div>`;
  ptRender(`
    <div class="card pt-form">
      <div class="section-label pt-label">${escHtml(PTT("pt_create_title"))}</div>
      <label class="pt-field-label" for="pt-name">${escHtml(PTT("pt_name_label"))}</label>
      <input class="modal-input" id="pt-name" maxlength="${c.name_max || 40}"
             placeholder="${escHtml(PTT("pt_name_ph"))}" autocomplete="off">
      <div class="pt-hint">${escHtml(PTT("pt_format", { min: c.min_players || 6, max: c.max_players || 20 }))}</div>
      ${priceBlock}
      <button class="btn btn--primary" id="pt-create-btn" ${c.price_set ? "" : "disabled"}>
        ${escHtml(PTT("pt_create_btn"))}</button>
    </div>`);
  document.getElementById("pt-create-btn").addEventListener("click", ptCreateSubmit);
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
    const r = await apiFetch("/pt/create", { method: "POST", body: JSON.stringify({ name }) });
    showToast(PTT("pt_created"));
    await ptOpenDetail(r.id);
  } catch (e) {
    const map = { name_too_short: "pt_err_name_short", name_too_long: "pt_err_name_long",
                  too_many_unpaid: "pt_err_too_many", price_not_set: "pt_price_not_set" };
    const code = (e && (e.detail || e.message)) || "";
    showToast(PTT(map[code] || "pt_err_generic"));
    btn.disabled = false;
    btn.textContent = PTT("pt_create_btn");
  } finally {
    PT.busy = false;
  }
}

function ptRenderDetail() {
  const t = PT.detail;
  const c = PT.config || {};
  const pay = (t.is_owner && t.status === "awaiting_payment") ? `
    <div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_pay_title"))}</div>
      <div class="pt-hint">${escHtml(PTT("pt_pay_text", { price: ptFormatPrice(t.price_uzs) }))}</div>
      <div class="pt-card-row">
        <span>${escHtml(PTT("pt_card"))}</span>
        <b class="pt-mono">${escHtml(c.card_number || "—")}</b>
        ${c.card_number ? `<button class="pt-copy" data-pt-copy="${escHtml(c.card_number.replace(/\s/g, ""))}">${escHtml(PTT("pt_copy"))}</button>` : ""}
      </div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_card_holder"))}</span><b>${escHtml(c.card_holder || "—")}</b></div>
    </div>` : "";

  const members = (t.members || []).map(m => `
    <div class="match-item pt-member">
      <span>${escHtml(m.nickname || "")}${m.username ? ` <span class="pt-muted">@${escHtml(m.username)}</span>` : ""}</span>
      ${m.status === "pending" ? `<span class="pt-status pt-status--payment_review">${escHtml(PTT("pt_pending"))}</span>` : ""}
    </div>`).join("");

  ptRender(`
    <div class="card pt-head">
      <div class="pt-head-name">${escHtml(t.name)}</div>
      <div class="pt-card-meta">
        <span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span>
        <span>${t.approved_count}/${t.max_players} ${escHtml(PTT("pt_members"))}</span>
      </div>
    </div>
    ${pay}
    <div class="section-label pt-label">${escHtml(PTT("pt_members_title"))}</div>
    ${members}`);

  document.querySelectorAll("#pt-root [data-pt-copy]").forEach(el =>
    el.addEventListener("click", () => ptCopy(el.dataset.ptCopy)));
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
  else if (PT.view === "detail" && PT.detail) ptRenderDetail();
  else ptRenderList();
}
