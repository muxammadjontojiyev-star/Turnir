// =============================================================
//  shop_admin.js — Admin sahifasi «🛒 DO'KON» bo'limi (faqat bosh admin, 2026-10-30)
//  - eF Token buyurtmalari: chek rasmi, Tasdiqlash / Rad etish (sabab ixtiyoriy)
//  - Paketlar: qo'shish, eF soni va narxini o'zgartirish, sotuvda / yashirin
//  Bo'lim ochilganda yuklanadi (<details id="shop-adm-group"> toggle). Admin paneli o'zbekcha (boshqa bo'limlar kabi).
//  API: /shop/admin/orders, /order/{id}/receipt, /order/{id}/review, /packages, /package.
//  Global: apiFetch, escHtml, showToast, shopNum, shopToken (shop.js), chatImgLightbox (chat_images.js).
// =============================================================

const SHOP_ADM = { busy: false };
const SHOP_ADM_ERR = {
  bad_coins: "eF Token soni 1 dan 1 000 000 gacha bo'lsin.", bad_price: "Narx 1 so'mdan 100 000 000 so'mgacha bo'lsin.",
  too_many_packages: "Paketlar soni chegarasiga yetildi — keraksizini yashiring yoki o'zgartiring.",
  wrong_status: "Bu buyurtma allaqachon ko'rib chiqilgan.", not_found: "Topilmadi.",
};

async function shopAdmLoad() {
  const box = document.getElementById("shop-adm");
  if (!box) return;
  try {
    const [o, p] = await Promise.all([apiFetch("/shop/admin/orders"), apiFetch("/shop/admin/packages")]);
    box.innerHTML = shopAdmOrdersHtml(o.orders || []) + shopAdmPackagesHtml(p.packages || []);
    const cnt = document.getElementById("shop-adm-count");
    if (cnt) cnt.textContent = o.orders && o.orders.length ? `(${o.orders.length})` : "";
  } catch (e) {
    box.innerHTML = `<div class="adm-pp-hint">${escHtml(e.message || "Xatolik")}</div>`;
  }
}

function shopAdmOrdersHtml(orders) {
  const rows = orders.map(o => {
    const who = o.username ? "@" + o.username : (o.nickname || "");
    return `<div class="shop-adm-order">
        <div class="shop-adm-order-top">${shopToken("shop-tk shop-tk--xs")}<b>${shopNum(o.coins)}</b>
          <span>· ${shopNum(o.price_uzs)} so'm · #${Number(o.id)}</span></div>
        <div class="shop-adm-order-who">${escHtml(who)} · ID ${escHtml(o.telegram_id)} · ${escHtml(o.created_local || "")}</div>
        <div class="shop-adm-actions">
          ${o.has_receipt ? `<button class="btn btn--ghost" data-shop-adm="receipt" data-id="${Number(o.id)}">🧾 Chek</button>`
            : `<button class="btn btn--ghost" disabled title="Xaridor chekni Telegram'da yuboradi">📩 Telegramda</button>`}
          <button class="btn btn--primary" data-shop-adm="approve" data-id="${Number(o.id)}">✅ Tasdiqlash</button>
          <button class="btn btn--ghost" data-shop-adm="reject" data-id="${Number(o.id)}">❌ Rad etish</button>
        </div>
      </div>`;
  }).join("");
  return `<div class="adm-pp-hint"><b>BUYURTMALAR</b> — chekdagi summa va sana mos kelsa tasdiqlang: eF Token xaridor balansiga tushadi va bot xabar beradi.</div>
    ${rows || `<div class="adm-pp-hint">Tekshiruvdagi buyurtma yo'q.</div>`}`;
}

function shopAdmPackagesHtml(pkgs) {
  const row = p => `<div class="shop-adm-pkg" data-pkg-row="${p ? Number(p.id) : ""}">
      <input class="modal-input" type="number" min="1" inputmode="numeric" placeholder="eF soni" value="${p ? Number(p.coins) : ""}" data-f="coins">
      <input class="modal-input" type="number" min="1" inputmode="numeric" placeholder="Narx, so'm" value="${p ? Number(p.price_uzs) : ""}" data-f="price">
      <label class="shop-adm-act"><input type="checkbox" data-f="active" ${!p || p.active ? "checked" : ""}> sotuvda</label>
      <button class="btn btn--primary" data-shop-adm="save">${p ? "💾" : "➕"}</button>
    </div>`;
  return `<div class="adm-pp-hint" style="margin-top:14px"><b>PAKETLAR</b> — ishtirokchilar Do'kon sahifasida faqat «sotuvda» belgilanganlarini ko'radi. Narx o'zgarsa, avvalgi buyurtmalar eski narxda qoladi.</div>
    ${pkgs.map(row).join("")}
    <div class="adm-pp-hint">Yangi paket:</div>${row(null)}`;
}

async function shopAdmAction(btn) {
  if (SHOP_ADM.busy) return;
  const a = btn.dataset.shopAdm, id = btn.dataset.id;
  if (a === "receipt") {
    try {
      const res = await fetch(API_BASE + `/shop/admin/order/${encodeURIComponent(id)}/receipt`,
        { headers: { "X-Telegram-Init-Data": window.Telegram?.WebApp?.initData || "" } });
      if (!res.ok) throw new Error("not_found");
      const url = URL.createObjectURL(await res.blob());
      if (typeof chatImgLightbox === "function") chatImgLightbox(url); else window.open(url, "_blank");
    } catch (_) { showToast(SHOP_ADM_ERR.not_found); }
    return;
  }
  let path, body;
  if (a === "approve" || a === "reject") {
    let reason = "";
    if (a === "reject") {
      reason = window.prompt("Rad etish sababi (ixtiyoriy):", "");
      if (reason === null) return;
    } else if (!window.confirm("Buyurtmani tasdiqlaysizmi? eF Token balansga tushadi.")) return;
    path = `/shop/admin/order/${encodeURIComponent(id)}/review`;
    body = { approve: a === "approve", reason };
  } else if (a === "save") {
    const row = btn.closest("[data-pkg-row]");
    const v = f => row.querySelector(`[data-f="${f}"]`);
    path = "/shop/admin/package";
    body = { id: row.dataset.pkgRow ? Number(row.dataset.pkgRow) : null, coins: Number(v("coins").value),
             price_uzs: Number(v("price").value), active: v("active").checked };
  } else return;
  SHOP_ADM.busy = true;
  btn.disabled = true;
  try {
    await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    showToast("✅ Saqlandi");
  } catch (e) {
    showToast("❌ " + (SHOP_ADM_ERR[e.message] || e.message));
  } finally {
    SHOP_ADM.busy = false;
    btn.disabled = false;
  }
  await shopAdmLoad();
}

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-shop-adm]") : null;
  if (b && document.getElementById("shop-adm")?.contains(b)) void shopAdmAction(b);
});
document.getElementById("shop-adm-group")?.addEventListener("toggle", (e) => { if (e.target.open) void shopAdmLoad(); });
// Admin sahifasi ochilganda navbat sonini ko'rsatish (bo'lim yig'iq bo'lsa ham). 403 — bosh admin emas, jim.
if (typeof SECTION_LOADERS !== "undefined" && SECTION_LOADERS.admin) {
  const _shopPrevAdmin = SECTION_LOADERS.admin;
  SECTION_LOADERS.admin = (...args) => {
    const r = _shopPrevAdmin(...args);
    void shopAdmLoad();
    return r;
  };
}
