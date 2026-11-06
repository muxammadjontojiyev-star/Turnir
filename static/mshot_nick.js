// =============================================================
//  mshot_nick.js — eFOOTBALL NIKNAME (2026-11-06): Profil sahifasida bo'lim + skrinshot oynasida (kiritilmagan bo'lsa).
//  Qoida (egasi): har mavsumda 2 marta bepul almashtirish, keyin — 5 eF Token (server: ef_nick.py).
//  API: GET/POST /ef-nick. Global: APP, apiFetch, escHtml, showToast, msT, msErr, msShotRender (mshot.js).
// =============================================================

const MSN = { info: null, busy: false, edit: false };

async function msNickLoad(force = false) {
  if (MSN.info && !force) return MSN.info;
  try { MSN.info = await apiFetch("/ef-nick"); } catch (_) { MSN.info = MSN.info || null; }
  return MSN.info;
}
function msNickHas() { return !!(MSN.info && MSN.info.nick); }

// 2026-11-06 (egasi): ixcham — profil kartasida username ostida; ortiqcha tushuntirishsiz
function msNickFormHtml(where) {
  const i = MSN.info || {};
  if (i.nick && !MSN.edit) {
    return `<div class="ms-nick ms-nick--set" data-ms-nick-where="${where}">
        <span class="ms-nick-ic">🎮</span><span class="ms-nick-val">${escHtml(i.nick)}</span>
        <button class="ms-nick-edit" data-ms-nick-edit="1" aria-label="edit">✏️</button>
      </div>`;
  }
  return `<div class="ms-nick ms-nick--form" data-ms-nick-where="${where}">
      <input class="ms-nick-input" maxlength="24" placeholder="${escHtml(msT("ms_nick_ph"))}" value="${escHtml(i.nick || "")}"
        autocomplete="off" autocapitalize="off" spellcheck="false">
      <button class="ms-nick-ok" data-ms-nick-save="1" ${MSN.busy ? "disabled" : ""} aria-label="save">✓</button>
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
    MSN.edit = false;
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
  if (b) { e.preventDefault(); e.stopPropagation(); void msNickSave(b); return; }
  const ed = e.target.closest ? e.target.closest("[data-ms-nick-edit]") : null;
  if (ed) {
    e.preventDefault(); e.stopPropagation();
    MSN.edit = true;
    msNickPaintProfile();
    document.querySelector(".ms-nick-slot .ms-nick-input")?.focus();
  }
}, true);

// ---- Profil kartasi: username ostida ixcham qator ----
function msNickPaintProfile() {
  const info = document.getElementById("profile-nickname")?.closest(".profile-info");
  if (!info) return;
  let slot = info.querySelector(":scope > .ms-nick-slot");
  if (!slot) {
    slot = document.createElement("div");
    slot.className = "ms-nick-slot";
    info.appendChild(slot);
  }
  const html = `${!(MSN.info && MSN.info.nick) ? `<div class="ms-nick-label">${escHtml(msT("ms_nick_need"))}</div>` : ""}${msNickFormHtml("profile")}`;
  if (slot._html !== html) { slot.innerHTML = html; slot._html = html; }
}

// Enter — saqlash
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || !e.target.classList || !e.target.classList.contains("ms-nick-input")) return;
  const b = e.target.closest(".ms-nick")?.querySelector("[data-ms-nick-save]");
  if (b) { e.preventDefault(); void msNickSave(b); }
});

if (typeof renderProfile === "function") {
  const _msPrevRenderProfile = renderProfile;
  renderProfile = function (data) {                                                  // eslint-disable-line no-global-assign
    _msPrevRenderProfile(data);
    msNickPaintProfile();
    void msNickLoad().then(msNickPaintProfile);
  };
}
