// =============================================================
//  shop.js — DO'KON sahifasi (#section-shop, pastki menyuning 5-tugmasi) va eF Token (2026-10-30)
//  Tablar: «eF Token» — balans, paketlar, sotib olish (karta + chek), buyurtmalarim;
//          «Bezaklar» — ramka va profil orqa foni (cosmetics.js); «Auksion» — klub uchun kim oshdi savdosi (shop_auction.js).
//  API: GET /shop, POST /shop/order {package_id, image_base64}. Matnlar — texts_shop.js.
//  Global: APP, apiFetch, escHtml, showToast, SECTION_LOADERS (app.js), receiptPrepare (receipt_image.js).
// =============================================================

const SHOP = { data: null, tab: "coins", busy: false, pkg: null };
const SHOP_TOKEN_IMG = "images/ef-token.svg?v=20261030a";

function shopT(key, vars) {
  let s = (APP.t && APP.t[key]) || (SHOP_TEXTS.uz[key] ?? key);
  if (vars) for (const k of Object.keys(vars)) s = s.split(`{${k}}`).join(String(vars[k]));
  return s;
}
function shopNum(n) { return String(Math.trunc(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " "); }
function shopToken(cls = "shop-tk") { return `<img src="${SHOP_TOKEN_IMG}" alt="eF" class="${cls}">`; }

async function loadShop() {
  const root = document.getElementById("shop-root");
  if (!root) return;
  if (!SHOP.data) root.innerHTML = `<div class="shop-loading">…</div>`;
  try {
    SHOP.data = await apiFetch("/shop");
  } catch (e) {
    if (!SHOP.data) { root.innerHTML = `<div class="card shop-empty">${escHtml(shopT("shop_err_generic"))}</div>`; return; }
  }
  shopRender();
  if (SHOP.tab === "auction" && typeof aucLoad === "function") await aucLoad();
  if (SHOP.tab === "cos" && typeof cosLoad === "function") await cosLoad();
}

function shopRender() {
  const root = document.getElementById("shop-root");
  const d = SHOP.data;
  if (!root || !d) return;
  root.innerHTML = `
    <div class="card shop-hero">
      ${shopToken("shop-tk shop-tk--hero")}
      <div class="shop-hero-txt">
        <div class="shop-hero-lbl">${escHtml(shopT("shop_balance"))}</div>
        <div class="shop-hero-val">${shopNum(d.balance)}<small>${escHtml(shopT("shop_currency"))}</small></div>
      </div>
    </div>
    <div class="shop-seg">
      <button class="shop-seg-btn ${SHOP.tab === "coins" ? "active" : ""}" data-shop-tab="coins">${shopToken("shop-tk shop-tk--xs")} ${escHtml(shopT("shop_tab_coins"))}</button>
      <button class="shop-seg-btn ${SHOP.tab === "cos" ? "active" : ""}" data-shop-tab="cos">🎨 ${escHtml(shopT("shop_tab_cos"))}</button>
      <button class="shop-seg-btn ${SHOP.tab === "auction" ? "active" : ""}" data-shop-tab="auction">🔨 ${escHtml(shopT("shop_tab_auction"))}</button>
    </div>
    ${SHOP.tab === "auction" ? shopAuctionHtml() : SHOP.tab === "cos" && typeof cosTabHtml === "function" ? cosTabHtml() : shopCoinsHtml(d)}`;
}

function shopCoinsHtml(d) {
  const pk = (d.packages || []).map(p => `
    <button class="shop-pkg" data-shop-pkg="${Number(p.id)}">
      ${typeof shopStackSvg === "function" ? shopStackSvg(p.coins) : shopToken("shop-tk shop-tk--pkg")}
      <b>${shopNum(p.coins)}</b><span class="shop-pkg-cur">${escHtml(shopT("shop_currency"))}</span>
      <span class="shop-pkg-price">${escHtml(shopT("shop_price", { price: shopNum(p.price_uzs) }))}</span>
    </button>`).join("");
  const orders = (d.orders || []).map(o => `
    <div class="shop-order">
      <div class="shop-order-main">${shopToken("shop-tk shop-tk--xs")}<b>${shopNum(o.coins)}</b>
        <span class="shop-order-sub">${escHtml(shopT("shop_price", { price: shopNum(o.price_uzs) }))} · ${escHtml(o.created_local || "")}</span></div>
      <span class="shop-st shop-st--${escHtml(o.status)}">${escHtml(shopT("shop_st_" + o.status))}</span>
      ${!o.has_receipt && o.status === "review" ? `<div class="shop-order-reason shop-order-tg">${escHtml(shopT("shop_receipt_tg"))}</div>` : ""}
      ${o.status === "rejected" && o.reject_reason ? `<div class="shop-order-reason">${escHtml(shopT("shop_reason"))}: ${escHtml(o.reject_reason)}</div>` : ""}
    </div>`).join("");
  return `
    <div class="section-label">${escHtml(shopT("shop_packages"))}</div>
    ${pk ? `<div class="shop-pkgs">${pk}</div>` : `<div class="card shop-empty">${escHtml(shopT("shop_no_packages"))}</div>`}
    <div class="section-label">${escHtml(shopT("shop_orders"))}</div>
    ${orders ? `<div class="card shop-orders">${orders}</div>` : `<div class="card shop-empty">${escHtml(shopT("shop_no_orders"))}</div>`}`;
}

// Auksion tabi — shop_auction.js (shopAuctionHtml, aucLoad)

// ---------------- Sotib olish oynasi ----------------

function shopOpenBuy(pid) {
  const d = SHOP.data, p = (d.packages || []).find(x => Number(x.id) === Number(pid));
  if (!p) return;
  SHOP.pkg = p;
  let m = document.getElementById("shop-buy");
  if (!m) {
    m = document.createElement("div");
    m.id = "shop-buy"; m.className = "modal";
    document.body.appendChild(m);
    m.addEventListener("click", shopBuyClick);
  }
  const card = d.card_number
    ? `<div class="shop-card"><span class="shop-card-num">${escHtml(d.card_number)}</span>
         <button class="btn btn--ghost shop-copy" data-shop="copy">${escHtml(shopT("shop_copy"))}</button></div>
       ${d.card_holder ? `<div class="shop-card-holder">${escHtml(shopT("shop_holder"))}: <b>${escHtml(d.card_holder)}</b></div>` : ""}`
    : `<div class="shop-empty">${escHtml(shopT("shop_no_card"))}</div>`;
  m.innerHTML = `<div class="modal-box shop-buy-box">
      <div class="shop-buy-head">${shopToken("shop-tk shop-tk--pkg")}<div class="modal-title">${shopNum(p.coins)} ${escHtml(shopT("shop_currency"))}</div></div>
      <div class="shop-step">${escHtml(shopT("shop_step1", { price: shopNum(p.price_uzs) }))}</div>
      ${card}
      <div class="shop-step">${escHtml(shopT("shop_step2"))}</div>
      <input type="file" accept="image/*" id="shop-file" hidden>
      <button class="btn btn--primary" data-shop="pick" ${d.card_number ? "" : "disabled"}>${escHtml(shopT("shop_send_receipt"))}</button>
      <div class="shop-err hidden" id="shop-err"></div>
      <div class="shop-hint">${escHtml(shopT("shop_hint"))}</div>
      ${d.card_number ? `<button class="shop-noreceipt" data-shop="noreceipt">${escHtml(shopT("shop_no_receipt_btn"))}</button>` : ""}
      <button class="btn btn--ghost" data-shop="close">${escHtml(shopT("shop_close"))}</button>
    </div>`;
  m.classList.remove("hidden");
  m.querySelector("#shop-file").addEventListener("change", (e) => {
    const f = e.target.files && e.target.files[0];
    if (f) void shopUpload(f, m.querySelector('[data-shop="pick"]'));
    e.target.value = "";
  });
}

function shopCloseBuy() { document.getElementById("shop-buy")?.classList.add("hidden"); }

function shopBuyClick(e) {
  if (e.target.id === "shop-buy") { shopCloseBuy(); return; }
  const b = e.target.closest && e.target.closest("[data-shop]");
  if (!b) return;
  const a = b.dataset.shop;
  if (a === "close") shopCloseBuy();
  else if (a === "pick") document.getElementById("shop-file")?.click();
  else if (a === "noreceipt") void shopNoReceipt(b);
  else if (a === "copy") {
    const num = String(SHOP.data.card_number || "").replace(/\s+/g, "");
    navigator.clipboard?.writeText(num).then(() => showToast(shopT("shop_copied")), () => {});
  }
}

function shopErr(e) {
  const code = e && e.message;
  if (code === "too_many_pending") return shopT("shop_err_too_many_pending", { n: SHOP.data.pending_max });
  if (code === "unsupported_format") return shopT("shop_err_format");
  if (code === "bad_image" || code === "empty_image") return shopT("shop_err_image");
  if (code === "image_too_large") return shopT("shop_err_image_large");
  if (code === "no_card") return shopT("shop_no_card");
  if (code === "package_not_found") return shopT("shop_err_package_not_found");
  return shopT("shop_err_generic");
}

// 2026-10-30: xato toast emas — oynaning o'zida qoladi va "chekni Telegram'da yuborish" yo'li ko'rsatiladi
function shopShowErr(msg) {
  const el = document.getElementById("shop-err");
  if (!el) { showToast(msg); return; }
  el.textContent = msg;
  el.classList.remove("hidden");
  document.querySelector('#shop-buy [data-shop="noreceipt"]')?.classList.add("shop-noreceipt--hl");
}

async function shopUpload(file, btn) {
  if (SHOP.busy || !SHOP.pkg) return;                 // ikki marta yuborish (qoida #38)
  SHOP.busy = true;
  btn.disabled = true;
  btn.textContent = shopT("shop_sending");
  document.getElementById("shop-err")?.classList.add("hidden");
  let ok = false;
  try {
    const image = await receiptPrepare(file);
    await apiFetch("/shop/order", { method: "POST", body: JSON.stringify({ package_id: SHOP.pkg.id, image_base64: image }) });
    ok = true;
    shopCloseBuy();
    showToast(shopT("shop_sent"));
  } catch (e) {
    const code = e && e.message;
    const fallback = ["unsupported_format", "bad_image", "empty_image", "image_too_large"].includes(code);
    shopShowErr(shopErr(e) + (fallback ? " " + shopT("shop_err_fallback_hint") : ""));
    btn.disabled = false;
    btn.textContent = shopT("shop_send_receipt");
  } finally {
    SHOP.busy = false;
  }
  if (ok) await loadShop();
}

function shopOpenAdminChat() {
  const c = APP.adminContact || {};
  const url = c.url || (c.username ? `https://t.me/${encodeURIComponent(String(c.username).replace(/^@/, ""))}` : "");
  if (!url) return;
  const w = window.Telegram?.WebApp;
  if (w?.openTelegramLink && /^https:\/\/t\.me\//.test(url)) w.openTelegramLink(url); else window.open(url, "_blank");
}

// Chekni ilovada yubora olmadi: buyurtma chek rasmisiz ochiladi, admin bilan chat ochiladi (chek o'sha yerga)
async function shopNoReceipt(btn) {
  if (SHOP.busy || !SHOP.pkg) return;
  if (!window.confirm(shopT("shop_no_receipt_ask", { coins: shopNum(SHOP.pkg.coins), price: shopNum(SHOP.pkg.price_uzs) }))) return;
  SHOP.busy = true;
  btn.disabled = true;
  try {
    await apiFetch("/shop/order", { method: "POST", body: JSON.stringify({ package_id: SHOP.pkg.id, no_receipt: true }) });
    shopCloseBuy();
    showToast(shopT("shop_no_receipt_done"));
    shopOpenAdminChat();
  } catch (e) {
    shopShowErr(shopErr(e));
    btn.disabled = false;
  } finally {
    SHOP.busy = false;
  }
  await loadShop();
}

document.addEventListener("click", (e) => {
  const root = document.getElementById("shop-root");
  if (!root || !e.target.closest || !root.contains(e.target)) return;
  const tab = e.target.closest("[data-shop-tab]");
  if (tab) {
    SHOP.tab = tab.dataset.shopTab;
    shopRender();
    if (SHOP.tab === "auction" && typeof aucLoad === "function") void aucLoad();
    if (SHOP.tab === "cos" && typeof cosLoad === "function") void cosLoad();      // 2026-10-30: bezaklar
    return;
  }
  const pkg = e.target.closest("[data-shop-pkg]");
  if (pkg) shopOpenBuy(pkg.dataset.shopPkg);
});

if (typeof SECTION_LOADERS !== "undefined") SECTION_LOADERS.shop = () => loadShop();
