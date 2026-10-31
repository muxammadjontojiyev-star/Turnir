// =============================================================
//  cosmetics.js — DO'KON → «Bezaklar» tabi + profilda qo'llash (2026-10-30)
//  Avatar ramkalari (.cos-frame-<id>) va profil kartasi orqa fonlari (.cos-bg-<id>) — dizayn cosmetics.css.
//  Ko'rinadi: o'z Profil sahifasi (renderProfile) va reytingdan ochilgan o'yinchi profili (renderPlayerModal) —
//  ikkala funksiya o'ralib, javobdagi data.cosmetics bo'yicha klass qo'shiladi.
//  API: GET /shop/cosmetics, POST /shop/cosmetics/buy {item_id}, POST /shop/cosmetics/equip {kind, item_id|null}.
//  Global: SHOP, shopT, shopNum, shopToken, shopRender (shop.js), APP, apiFetch, escHtml, showToast.
// =============================================================

const COS = { data: null, busy: false };
const COS_KINDS = ["frame", "bg"];

function cosClassFor(kind, id) { return id ? `cos-${kind}-${id}` : ""; }

// Kartadagi eski bezak klasslarini olib, yangisini qo'yadi
function cosApply(card, avatar, cos) {
  const c = cos || {};
  const strip = (el, kind) => {
    if (!el) return;
    [...el.classList].filter(x => x.startsWith(`cos-${kind}-`)).forEach(x => el.classList.remove(x));
    const cls = cosClassFor(kind, c[kind]);
    if (cls) el.classList.add(cls);
  };
  strip(avatar, "frame");
  strip(card, "bg");
}

function cosApplyById(letterId, cos) {
  const av = document.getElementById(letterId)?.closest(".profile-avatar");
  const card = av?.closest(".card--profile");
  cosApply(card, av, cos);
  cosApplyPage(card?.closest(".section"), cos && cos.bg);
}

// 2026-10-31: futbolchi rasmli fon (pl_*) — butun sahifa foni (poster to'liq ko'rinadi), cosmetics.css .cos-page
function cosApplyPage(section, bg) {
  if (!section) return;
  [...section.classList].filter(x => x.startsWith("cos-page")).forEach(x => section.classList.remove(x));
  if (bg && bg.startsWith("pl_")) section.classList.add("cos-page", `cos-page-${bg}`);
  cosSyncHeader();
}

// 2026-10-31: faol sahifada futbolchi foni bo'lsa — yuqori panel (header) shaffof, poster ekranni to'liq egallaydi
function cosSyncHeader() {
  document.body.classList.toggle("cos-theme-on", !!document.querySelector(".section.active.cos-page"));
}
if (typeof navigateTo === "function") {
  const _cosPrevNavigate = navigateTo;
  navigateTo = function (...args) { const r = _cosPrevNavigate(...args); cosSyncHeader(); return r; };   // eslint-disable-line no-global-assign
}

// 2026-10-31: o'z futbolchi foni — ilovaning asosiy sahifalarida ham (egasi so'rovi). Do'kon va Admin — fonsiz
// (bezak namunalari va boshqaruv aniq ko'rinsin); o'yinchi sahifasida — O'SHA o'yinchining foni (renderPlayerModal).
const COS_THEME_SECTIONS = ["section-home", "section-rating", "section-prizes", "section-profile"];

function cosApplyTheme(bg) {
  COS_THEME_SECTIONS.forEach(id => cosApplyPage(document.getElementById(id), bg));
}

async function cosThemeInit() {
  try {
    const d = await apiFetch("/shop/cosmetics");
    cosApplyTheme(d && d.equipped && d.equipped.bg);
  } catch (_) { /* fonsiz qoladi */ }
}

if (typeof renderProfile === "function") {
  const _cosPrevRenderProfile = renderProfile;
  renderProfile = function (data) {                                                  // eslint-disable-line no-global-assign
    _cosPrevRenderProfile(data);
    cosApplyById("profile-avatar-letter", data && data.cosmetics);
    cosApplyTheme(data && data.cosmetics && data.cosmetics.bg);
  };
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => setTimeout(cosThemeInit, 0));
else setTimeout(cosThemeInit, 0);
if (typeof renderPlayerModal === "function") {
  const _cosPrevRenderPlayer = renderPlayerModal;
  renderPlayerModal = function (data) { _cosPrevRenderPlayer(data); cosApplyById("player-avatar-letter", data && data.cosmetics); };   // eslint-disable-line no-global-assign
}

async function cosLoad() {
  try {
    COS.data = await apiFetch("/shop/cosmetics");
    if (SHOP.data) SHOP.data.balance = COS.data.balance;
  } catch (_) {
    if (!COS.data) COS.data = { error: true };
  }
  if (SHOP.tab === "cos") shopRender();
}

function cosPreview(item, me) {
  const letter = escHtml(((me && me.nickname) || "?")[0].toUpperCase());
  const frame = item.kind === "frame" ? cosClassFor("frame", item.id) : "";
  const bg = item.kind === "bg" ? cosClassFor("bg", item.id) : "";
  return `<div class="card card--profile cos-prev ${bg}">
      <div class="profile-avatar ${frame}"><div class="cos-prev-letter">${letter}</div></div>
      ${item.kind === "bg" ? `<div class="profile-info"><b>${escHtml((me && me.nickname) || "")}</b></div>` : ""}
    </div>`;
}

function cosItemHtml(item, d) {
  const owned = d.owned.includes(item.id), on = d.equipped[item.kind] === item.id;
  const btn = on
    ? `<button class="btn btn--ghost cos-btn" data-cos="off" data-kind="${item.kind}">${escHtml(shopT("cos_remove"))}</button>`
    : owned
      ? `<button class="btn btn--primary cos-btn" data-cos="on" data-id="${escHtml(item.id)}" data-kind="${item.kind}">${escHtml(shopT("cos_apply"))}</button>`
      : `<button class="btn btn--primary cos-btn" data-cos="buy" data-id="${escHtml(item.id)}">${shopToken("shop-tk shop-tk--xs")} ${shopNum(item.price)}</button>`;
  return `<div class="cos-item ${on ? "cos-item--on" : ""}">
      <div class="cos-prev-wrap" data-cos-try="${escHtml(item.id)}" role="button">
        ${cosPreview(item, APP.profileData || { nickname: document.getElementById("header-nickname")?.textContent || "" })}
        <span class="cos-eye">👁</span>
      </div>
      <div class="cos-name">${escHtml(shopT("cos_" + item.id))}${on ? ` <span class="cos-on">✓</span>` : ""}</div>
      ${btn}
      <button class="cos-look" data-cos-try="${escHtml(item.id)}">${escHtml(shopT("cos_try_btn"))}</button>
    </div>`;
}

function cosTabHtml() {
  const d = COS.data;
  if (!d) return `<div class="shop-loading">…</div>`;
  if (d.error) return `<div class="card shop-empty">${escHtml(shopT("shop_err_generic"))}</div>`;
  // 2026-10-31: futbolchilar rasmli fonlar (pl_*) — alohida bo'lim; sotuvdan olinganlar faqat egasiga keladi (server)
  const group = (kind, pl) => d.catalog.filter(x => x.kind === kind && (pl === undefined || x.id.startsWith("pl_") === pl))
    .map(x => cosItemHtml(x, d)).join("");
  return `<div class="auc-rules">${escHtml(shopT("cos_rules"))}</div>
    <div class="section-label">${escHtml(shopT("cos_frames"))}</div><div class="cos-grid">${group("frame")}</div>
    <div class="section-label">${escHtml(shopT("cos_players"))}</div><div class="cos-grid cos-grid--bg">${group("bg", true)}</div>
    <div class="section-label">${escHtml(shopT("cos_bgs"))}</div><div class="cos-grid cos-grid--bg">${group("bg", false)}</div>`;
}

function cosErr(e) {
  const code = e && e.message;
  return shopT(["insufficient", "already_owned", "not_owned", "not_found"].includes(code) ? "cos_err_" + code : "shop_err_generic");
}

async function cosAction(btn) {
  if (COS.busy || !COS.data) return;                     // ikki marta bosish (qoida #38)
  const a = btn.dataset.cos, id = btn.dataset.id || null, kind = btn.dataset.kind;
  let path, body;
  if (a === "buy") {
    const item = COS.data.catalog.find(x => x.id === id);
    if (!item) return;
    if (item.price > (COS.data.balance || 0)) { showToast(shopT("cos_err_insufficient")); return; }
    if (!window.confirm(shopT("cos_confirm", { name: shopT("cos_" + id), price: shopNum(item.price) }))) return;
    path = "/shop/cosmetics/buy"; body = { item_id: id };
  } else {
    path = "/shop/cosmetics/equip"; body = { kind, item_id: a === "on" ? id : null };
  }
  COS.busy = true;
  btn.disabled = true;
  try {
    const r = await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    if (APP.profileData) {
      APP.profileData.cosmetics = r.equipped;            // Profil sahifasi qayta yuklanmasa ham yangilansin
      cosApplyById("profile-avatar-letter", r.equipped);
    }
    cosApplyTheme(r.equipped && r.equipped.bg);          // 2026-10-31: boshqa sahifalar foni ham
    showToast(shopT(a === "buy" ? "cos_bought" : a === "on" ? "cos_applied" : "cos_removed"));
  } catch (e) {
    showToast(cosErr(e));
  } finally {
    COS.busy = false;
  }
  await cosLoad();
}

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-cos]") : null;
  if (b && document.getElementById("shop-root")?.contains(b)) void cosAction(b);
});
