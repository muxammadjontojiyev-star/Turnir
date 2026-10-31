// =============================================================
//  cosmetics_try.js — Bezakni SOTIB OLISHDAN OLDIN sinab ko'rish (2026-10-30)
//  «Bezaklar» tabida bezak namunasi yoki «👁 Ko'rish» bosilsa — oyna: o'z profil kartangiz (Telegram rasmi,
//  nik, liga/klub qatori) shu bezak bilan, hozir qo'llangan boshqa turdagi bezak ham saqlanadi
//  (masalan, fon sinalsa — ramkangiz qoladi). ‹ › bilan shu turdagi bezaklarni almashtirib ko'rish,
//  pastda — Sotib olish / Qo'llash. Hech narsa saqlanmaydi, faqat ko'rinish.
//  Global: COS, cosAction, cosClassFor (cosmetics.js), shopT, shopNum, shopToken (shop.js), APP, escHtml.
// =============================================================

const COS_TRY = { id: null };

function cosTryAvatarHtml() {
  const nick = (APP.profileData && APP.profileData.nickname) || document.getElementById("header-nickname")?.textContent || "?";
  const photo = APP.currentUser && APP.currentUser.photo_url;
  const letter = escHtml(nick.trim()[0] ? nick.trim()[0].toUpperCase() : "?");
  return photo
    ? `<div class="cos-try-letter"><img src="${escHtml(photo)}" alt="" onerror="this.parentElement.textContent='${letter}'"></div>`
    : `<div class="cos-try-letter">${letter}</div>`;
}

function cosTryHtml() {
  const d = COS.data, item = d && d.catalog.find(x => x.id === COS_TRY.id);
  if (!item) return "";
  const eq = d.equipped || {};
  const look = { frame: eq.frame, bg: eq.bg, [item.kind]: item.id };
  const nick = (APP.profileData && APP.profileData.nickname) || document.getElementById("header-nickname")?.textContent || "";
  const line = document.getElementById("profile-league")?.textContent || "";
  const owned = d.owned.includes(item.id), on = eq[item.kind] === item.id;
  const btn = on
    ? `<button class="btn btn--ghost" disabled>✓ ${escHtml(shopT("cos_try_on"))}</button>`
    : owned
      ? `<button class="btn btn--primary" data-cos="on" data-id="${escHtml(item.id)}" data-kind="${item.kind}">${escHtml(shopT("cos_apply"))}</button>`
      : `<button class="btn btn--primary cos-try-buy" data-cos="buy" data-id="${escHtml(item.id)}">${escHtml(shopT("cos_try_buy"))} · ${shopToken("shop-tk shop-tk--xs")} ${shopNum(item.price)}</button>`;
  return `<div class="modal-box cos-try-box">
      <div class="modal-title">${escHtml(shopT("cos_try_title"))}</div>
      ${(() => {
        const card = `<div class="card card--profile ${cosClassFor("bg", look.bg)}">
          <div class="profile-avatar ${cosClassFor("frame", look.frame)}">${cosTryAvatarHtml()}</div>
          <div class="profile-info">
            <h2 class="profile-nickname">${escHtml(nick)}</h2>
            ${line ? `<span class="profile-league">${escHtml(line)}</span>` : ""}
          </div>
        </div>`;
        // 2026-10-31: futbolchi foni — butun sahifa foni bo'lgani uchun baland namuna (poster to'liq)
        return look.bg && look.bg.startsWith("pl_") ? `<div class="cos-try-page cos-page-${escHtml(look.bg)} cos-bg-${escHtml(look.bg)}">${card}</div>` : card;
      })()}
      <div class="cos-try-nav">
        <button class="cos-try-arrow" data-cos-try-step="-1" aria-label="‹">‹</button>
        <div class="cos-try-name"><b>${escHtml(shopT("cos_" + item.id))}</b>
          <small>${escHtml(shopT(item.kind === "frame" ? "cos_frames" : "cos_bgs"))}${owned ? " · " + escHtml(shopT("cos_try_owned")) : ""}</small></div>
        <button class="cos-try-arrow" data-cos-try-step="1" aria-label="›">›</button>
      </div>
      <div class="cos-try-hint">${escHtml(shopT("cos_try_hint"))}</div>
      ${btn}
      <button class="btn btn--ghost" data-cos-try-close="1">${escHtml(shopT("shop_close"))}</button>
    </div>`;
}

function cosTryRender() {
  const m = document.getElementById("cos-try");
  if (m) m.innerHTML = cosTryHtml();
}

function cosTryOpen(id) {
  if (!COS.data || !COS.data.catalog.some(x => x.id === id)) return;
  COS_TRY.id = id;
  let m = document.getElementById("cos-try");
  if (!m) {
    m = document.createElement("div");
    m.id = "cos-try"; m.className = "modal";
    document.body.appendChild(m);
    m.addEventListener("click", cosTryClick);
  }
  m.classList.remove("hidden");
  cosTryRender();
}

function cosTryClose() { document.getElementById("cos-try")?.classList.add("hidden"); }

function cosTryStep(dir) {
  const item = COS.data.catalog.find(x => x.id === COS_TRY.id);
  const same = COS.data.catalog.filter(x => x.kind === item.kind);
  const i = same.findIndex(x => x.id === item.id);
  COS_TRY.id = same[(i + dir + same.length) % same.length].id;
  cosTryRender();
}

async function cosTryClick(e) {
  if (e.target.id === "cos-try" || (e.target.closest && e.target.closest("[data-cos-try-close]"))) { cosTryClose(); return; }
  const step = e.target.closest && e.target.closest("[data-cos-try-step]");
  if (step) { cosTryStep(Number(step.dataset.cosTryStep)); return; }
  const b = e.target.closest && e.target.closest("[data-cos]");
  if (b) {
    await cosAction(b);                                  // sotib olish / qo'llash — cosmetics.js (COS.data yangilanadi)
    cosTryRender();
  }
}

// Tabdagi namuna yoki «👁 Ko'rish» — sinab ko'rish oynasi
document.addEventListener("click", (e) => {
  const t = e.target.closest ? e.target.closest("[data-cos-try]") : null;
  if (t && document.getElementById("shop-root")?.contains(t)) cosTryOpen(t.dataset.cosTry);
});
