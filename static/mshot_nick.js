// =============================================================
//  mshot_nick.js — eFOOTBALL NIKNAME (2026-11-06): Profil sahifasida bo'lim + skrinshot oynasida (kiritilmagan bo'lsa).
//  Qoida (egasi): har mavsumda 2 marta bepul almashtirish, keyin — 5 eF Token (server: ef_nick.py).
//  API: GET/POST /ef-nick. Global: APP, apiFetch, escHtml, showToast, msT, msErr, msShotRender (mshot.js).
// =============================================================

const MSN = { info: null, busy: false };

async function msNickLoad(force = false) {
  if (MSN.info && !force) return MSN.info;
  try { MSN.info = await apiFetch("/ef-nick"); } catch (_) { MSN.info = MSN.info || null; }
  return MSN.info;
}
function msNickHas() { return !!(MSN.info && MSN.info.nick); }

function msNickFormHtml(where) {
  const i = MSN.info || {};
  const left = i.nick ? (i.free_left > 0 ? msT("ms_nick_free", { n: i.free_left }) : msT("ms_nick_paid", { price: i.price })) : "";
  return `<div class="ms-nick" data-ms-nick-where="${where}">
      <div class="ms-nick-hint">${escHtml(msT("ms_nick_hint"))}</div>
      <div class="ms-nick-row">
        <input class="modal-input ms-nick-input" maxlength="24" placeholder="${escHtml(msT("ms_nick_ph"))}" value="${escHtml(i.nick || "")}">
        <button class="btn btn--primary" data-ms-nick-save="1" ${MSN.busy ? "disabled" : ""}>${escHtml(msT("ms_nick_save"))}</button>
      </div>
      ${left ? `<div class="ms-nick-left">${escHtml(left)}</div>` : ""}
    </div>`;
}

// skrinshot oynasida — faqat nikname hali kiritilmagan bo'lsa
function msNickInlineHtml() {
  if (msNickHas()) return "";
  return `<div class="ms-nick-need">${escHtml(msT("ms_nick_need"))}</div>${msNickFormHtml("shot")}`;
}

async function msNickSave(btn) {
  if (MSN.busy) return;
  const box = btn.closest(".ms-nick");
  const nick = (box.querySelector(".ms-nick-input").value || "").trim();
  MSN.busy = true; btn.disabled = true;
  const send = (pay) => apiFetch("/ef-nick", { method: "POST", body: JSON.stringify({ nick, pay }) });
  try {
    try { MSN.info = await send(false); }
    catch (e) {
      if (!String(e.message || "").includes("need_pay")) throw e;
      if (!window.confirm(msT("ms_nick_pay_q", { price: (MSN.info && MSN.info.price) || 5 }))) return;
      MSN.info = await send(true);
    }
    showToast(msT("ms_nick_saved"));
  } catch (e) {
    showToast(msErr(e));
  } finally {
    MSN.busy = false;
    if (box.dataset.msNickWhere === "shot" && typeof msShotRender === "function") msShotRender();
    else msNickPaintProfile();
  }
}

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-ms-nick-save]") : null;
  if (b) { e.preventDefault(); e.stopPropagation(); void msNickSave(b); }
}, true);

// ---- Profil sahifasi: «eFOOTBALL NIKNAMEINGIZ» bo'limi (profil kartasidan keyin) ----
function msNickPaintProfile() {
  const card = document.getElementById("profile-avatar-letter")?.closest(".card--profile");
  if (!card) return;
  let slot = card.parentElement.querySelector(":scope > .ms-nick-slot");
  if (!slot) {
    slot = document.createElement("div");
    slot.className = "ms-nick-slot";
    card.insertAdjacentElement("afterend", slot);
  }
  const html = `<div class="section-label">${escHtml(msT("ms_nick_title"))}</div>
    <div class="card ms-nick-card">${msNickFormHtml("profile")}</div>`;
  if (slot._html !== html) { slot.innerHTML = html; slot._html = html; }
}

if (typeof renderProfile === "function") {
  const _msPrevRenderProfile = renderProfile;
  renderProfile = function (data) {                                                  // eslint-disable-line no-global-assign
    _msPrevRenderProfile(data);
    msNickPaintProfile();
    void msNickLoad().then(msNickPaintProfile);
  };
}
