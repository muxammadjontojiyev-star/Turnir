// =============================================================
//  mshot_nick.js — eFOOTBALL NIKNAME (2026-11-06): barcha rejimlarda O'Z profil kartasida (username ostida, ixcham)
//  + skrinshot oynasida (kiritilmagan bo'lsa).
//  Qoida (egasi): har mavsumda 2 marta bepul almashtirish, keyin — 5 eF Token (server: ef_nick.py).
//  API: GET/POST /ef-nick. Global: APP, apiFetch, escHtml, showToast, msT, msErr, msShotRender (mshot.js).
// =============================================================

const MSN = { info: null, busy: false, edit: false, loading: false };

async function msNickLoad(force = false) {
  if (MSN.info && !force) return MSN.info;
  try { MSN.info = await apiFetch("/ef-nick"); } catch (_) { MSN.info = MSN.info || null; }
  return MSN.info;
}
function msNickHas() { return !!(MSN.info && MSN.info.nick); }

// 2026-11-06 (egasi): ixcham — profil kartasida username ostida; ortiqcha tushuntirishsiz
function msNickFormHtml(where) {
  const i = MSN.info || {};
  if ((i.nick || i.pending) && !MSN.edit) {
    const pend = !i.nick && i.pending;                   // ikkinchi akkaunt — egasining tasdig'i kutilmoqda
    return `<div class="ms-nick ms-nick--set${pend ? " ms-nick--pending" : ""}" data-ms-nick-where="${where}"
        title="${escHtml(pend ? msT("ms_nick_pending") : i.linked ? msT("ms_nick_linked") : "")}">
        <span class="ms-nick-ic">${pend ? "⏳" : i.linked ? "🔗" : "🎮"}</span><span class="ms-nick-val">${escHtml(i.nick || i.pending)}</span>
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
    showToast(msT(MSN.info && MSN.info.link_requested ? "ms_nick_link_sent" : "ms_nick_saved"));
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
    Array.from(document.querySelectorAll(".ms-nick-slot .ms-nick-input")).find(x => x.offsetParent)?.focus();
  }
}, true);

// ---- O'z profil kartasi — BARCHA REJIMLARDA username ostida ixcham qator (2026-11-06, egasi) ----
// Har rejimda faqat O'Z profilim (boshqa o'yinchi profili emas). Rejim fayllariga tegilmaydi — DOM kuzatiladi.
function msMyUsername() { return (APP.currentUser && APP.currentUser.username) || ""; }
const MSN_TARGETS = [
  () => document.getElementById("profile-nickname")?.closest(".profile-info"),                       // liga
  () => (typeof DIV !== "undefined" && DIV.section === "profile"
    ? document.querySelector('#div-root .card div[style*="flex:1"]') : null),                         // Divizion
  () => (typeof CL !== "undefined" && CL.section === "profile" ? document.querySelector("#cl-root .card--profile .profile-info") : null),
  () => (typeof EL !== "undefined" && EL.section === "profile" ? document.querySelector("#el-root .card--profile .profile-info") : null),
  () => (typeof AC !== "undefined" && AC.section === "profile" ? document.querySelector("#ac-root .card--profile .profile-info") : null),
  () => (typeof CO !== "undefined" && CO.section === "profile" ? document.querySelector("#co-root .card--profile .profile-info") : null),
  () => (typeof WC !== "undefined" && WC.section === "profile"
    ? document.querySelector("#worldcup-root .card--profile .profile-info") : null),                  // JCh
  () => {                                                                                             // xususiy turnir
    const me = msMyUsername();
    if (!me) return null;
    const a = Array.from(document.querySelectorAll(".pt-profile-card .profile-username"))
      .find(x => x.textContent.trim().toLowerCase() === "@" + me.toLowerCase());
    return a ? a.closest(".profile-info") : null;
  },
];

function msNickSlotHtml() {
  const i = MSN.info || {};
  return `${!(i.nick || i.pending) ? `<div class="ms-nick-label">${escHtml(msT("ms_nick_need"))}</div>` : ""}${msNickFormHtml("profile")}`;
}

function msNickPaintProfile() {
  const html = msNickSlotHtml();
  for (const get of MSN_TARGETS) {
    let box = null;
    try { box = get(); } catch (_) { box = null; }
    if (!box || !box.isConnected) continue;
    let slot = box.querySelector(":scope > .ms-nick-slot");
    if (!slot) {
      slot = document.createElement("div");
      slot.className = "ms-nick-slot";
      box.appendChild(slot);
    }
    // faqat maydonga yozilayotgan paytda qayta chizilmaydi (✏️ tugmasi fokusda bo'lsa — chiziladi; 2026-11-06 xato)
    const typing = document.activeElement && document.activeElement.classList.contains("ms-nick-input") && slot.contains(document.activeElement);
    if (slot._html !== html && !typing) { slot.innerHTML = html; slot._html = html; }
  }
}

let _msnT = 0;
new MutationObserver(() => {                         // throttle — doimiy animatsiyada ham ishlaydi
  if (_msnT) return;
  _msnT = requestAnimationFrame(() => {
    _msnT = 0;
    if (!MSN.info && !MSN.loading) { MSN.loading = true; void msNickLoad().finally(() => { MSN.loading = false; msNickPaintProfile(); }); }
    msNickPaintProfile();
  });
}).observe(document.body, { subtree: true, childList: true });

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
