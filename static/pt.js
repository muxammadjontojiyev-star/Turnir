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
  if (String(PT.detailId) !== String(id)) { PT.tab = "home"; PT.playerView = null; PT.rulesEdit = false; PT.rulesOpen = false; PT.teamEdit = false; PT.lgTab = null; }   // boshqa turnir — Asosiy sahifadan
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
  } catch (e) {
    ptRender(`<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`);
    return;
  }
  try {
    ptRenderDetail();
  } catch (e) {          // chizish xatosi (masalan, skript fayli yuklanmagan) — tarmoq xatosi bilan adashtirilmasin
    console.error("PT chizish xatosi:", e);
    ptRender(`<div class="empty-state">${escHtml(PTT("pt_load_err"))}<br><small class="pt-muted">${escHtml(String(e && e.message || e))}</small></div>`);
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
    else if (PT.view === "detail" && PT.fromAll && typeof ptOpenAll === "function") void ptOpenAll();   // bosh admin ro'yxatiga
    else { PT.view = "list"; PT.fromAll = false; void ptLoadList(); }
  });
}

// 2026-10-07: stadion fonidagi hero + "Yangi turnir" asosiy tugma; bo'sh bo'lsa "Qanday ishlaydi" (pt_home.js)
function ptRenderList() {
  PT.view = "list";
  const cards = PT.list.map(ptListCardHtml).join("");
  // Bosh admin: to'lovlar navbati (2-bosqich, pt_payment.js)
  const adminBtn = (PT.config && PT.config.is_super)
    ? `<div class="pt-super-actions"><button class="btn btn--ghost" id="pt-payments-btn">${escHtml(PTT("pt_payments_btn"))}</button>
       <button class="btn btn--ghost" id="pt-all-btn">${escHtml(PTT("pt_all_btn"))}</button></div>` : "";
  const subCard = typeof ptSubCardHtml === "function" ? ptSubCardHtml() : "";   // 2026-10-03
  ptRender(`
    ${ptListHeroHtml()}
    ${subCard}
    ${adminBtn}
    ${cards ? `<div class="section-label pt-label">${escHtml(PTT("pt_my"))}</div>${cards}` : ptHowHtml()}`);

  document.getElementById("pt-new-btn").addEventListener("click", () => ptRenderCreate());
  document.getElementById("pt-payments-btn")?.addEventListener("click", () => void ptOpenPayments());
  document.getElementById("pt-all-btn")?.addEventListener("click", () => void ptOpenAll());       // pt_superadmin.js
  document.getElementById("pt-sub-open")?.addEventListener("click", () => void ptOpenSub());
  document.querySelectorAll("#pt-root [data-pt-open]").forEach(el =>
    el.addEventListener("click", () => void ptOpenDetail(el.dataset.ptOpen)));
  if (typeof ptBindDelete === "function") ptBindDelete();          // 2026-10-07: 🗑 o'chirish
}

// Yaratish formasi (format, liga, sig'im, to'lov) — pt_create.js (2026-10-07)

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

// Turnir sarlavhasi (Asosiy'dan boshqa sahifalar tepasida) — stadion fonidagi ixcham banner
function ptHeadHtml(t) {
  return `
    <div class="pt-head pt-head--banner pt-head--${escHtml(t.format || "classic")}"${typeof PT_FORMAT_META !== "undefined" && PT_FORMAT_META[t.format || "classic"]
      ? ` style="--pt-head-bg:url('${PT_FORMAT_META[t.format || "classic"].bg}')"` : ""}>
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
  else if (PT.view === "all" && typeof ptRenderAll === "function") ptRenderAll();
  else ptRenderList();
}
