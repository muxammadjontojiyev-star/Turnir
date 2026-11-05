// =============================================================
//  player_card.js — ISHTIROKCHINING SHAXSIY O'YINCHI KARTASI (2026-11-04, player_card.py)
//  eFootball kartasi uslubida: ramka foni (images/card-showtime.jpg), futbolchi o'rnida — ishtirokchi rasmidan
//  o'zi YUKLAGAN rasm (fon olib tashlangan, butun tana — GET /players/{id}/cardphoto; bo'lmasa — Telegram rasmi), chap tepada OVR,
//  pozitsiya, bayroq; pastda nik va yulduzlar. Dizayn — player_card.css.
//  Ko'rinadi: FAQAT Divizionda (2026-11-05) — o'z profili / o'yinchi profili (renderDivision o'raladi), qur'a kartasi (division.js
//  pcardHtml'ni chaqiradi). Kartani bosish — katta ko'rinish. API: GET /pcard/{user_id}.
//  Global: APP, API_BASE, apiFetch, escHtml. Ulanish: api.js, cosmetics.js, division.js dan KEYIN.
// =============================================================

const PC_STAR_TIERS = [95, 90, 85, 80];          // OVR ≥ shu → 5/4/3/2 yulduz, qolgani (70–79) — 1
const PC_LONG_NAME = 11;                         // shundan uzun nik — kichikroq shrift
const PC_BG_RE = /^card_[a-z0-9_]{1,30}$/;
const PC_POS_RE = /^[A-Z]{2,3}$/;
const PC_CC_RE = /^[A-Z]{2}$/;
const PC_SEQ = { div: 0 }; // eski javob yangisini bosib ketmasin

function pcT(key, vars) {
  let s = (APP.t && APP.t[key]) || (PCARD_TEXTS.uz[key] ?? key);
  if (vars) for (const k of Object.keys(vars)) s = s.split(`{${k}}`).join(String(vars[k]));
  return s;
}

function pcFlag(cc) {
  if (!PC_CC_RE.test(cc || "")) return "";
  return String.fromCodePoint(...[...cc].map(ch => 0x1f1e6 + ch.charCodeAt(0) - 65));
}

function pcStars(ovr) {
  const i = PC_STAR_TIERS.findIndex(t => ovr >= t);
  return 5 - (i < 0 ? PC_STAR_TIERS.length : i);
}

function pcPhotoSrc(c) {
  const myId = (APP.profileData && APP.profileData.user_id) || (typeof DIV !== "undefined" && DIV.status && DIV.status.me_id);
  const me = Number(myId) === Number(c.user_id);
  return (me && APP.currentUser && APP.currentUser.photo_url) || `${API_BASE}/players/${Number(c.user_id)}/photo`;
}

// Karta rasmi: o'zi yuklagani (fon olib tashlangan — butun tana / fonli) yoki Telegram profil rasmi (chetlari xira)
function pcPhotoHtml(c, name) {
  const letter = `<span class="pcard-letter">${escHtml(name[0].toUpperCase())}</span>`;
  const ph = c.photo && Number.isInteger(c.photo.v) ? c.photo : null;
  if (ph) {
    return `<div class="pcard-photo ${ph.cut ? "pcard-photo--cut" : "pcard-photo--own"}">
        <img src="${API_BASE}/players/${Number(c.user_id)}/cardphoto?v=${ph.v}" alt="" onerror="this.remove()">${letter}</div>`;
  }
  return `<div class="pcard-photo pcard-photo--plain">
      <img src="${escHtml(pcPhotoSrc(c))}" alt="" onerror="this.remove()">${letter}</div>`;
}

// c — /pcard javobi; opts.size: "sm" (Divizion ustuni) | "md" (profil) | "lg" (katta ko'rinish)
function pcardHtml(c, opts = {}) {
  if (!c) return "";
  const ovr = Math.max(0, Math.min(99, Number(c.ovr) || 0));
  const name = String(c.nickname || "—");
  const bg = PC_BG_RE.test(c.bg || "") ? ` pcard--bg pcard-bg-${c.bg}` : "";
  const pos = PC_POS_RE.test(c.position || "") ? c.position : "";
  const stars = "★".repeat(pcStars(ovr));
  return `<div class="pcard pcard--${opts.size || "md"}${bg}" data-pcard="${Number(c.user_id)}" role="button">
      <div class="pcard-in">
        ${pcPhotoHtml(c, name)}
        <div class="pcard-side">
          <div class="pcard-ovr">${ovr}</div>
          ${pos ? `<div class="pcard-pos">${escHtml(pos)}</div>` : ""}
          ${pcFlag(c.country) ? `<div class="pcard-flag">${pcFlag(c.country)}</div>` : ""}
        </div>
        <div class="pcard-name${name.length > PC_LONG_NAME ? " pcard-name--long" : ""}">${escHtml(name)}</div>
        <div class="pcard-plate"><span class="pcard-stars">${stars}</span></div>
      </div>
    </div>`;
}

// ---- katta ko'rinish (bosilganda) ----
const PC_CACHE = new Map();
function pcOpenBig(c) {
  document.querySelector(".pcard-ov")?.remove();
  const ov = document.createElement("div");
  ov.className = "pcard-ov";
  ov.innerHTML = `${pcardHtml(c, { size: "lg" })}
    <div class="pcard-ov-meta">${escHtml(pcT("pc_games", { n: c.played || 0, w: c.wins || 0 }))}</div>
    <div class="pcard-ov-hint">${escHtml(pcT("pc_tap_close"))}</div>`;
  ov.addEventListener("click", () => ov.remove());
  document.body.appendChild(ov);
  if (c.photo) void pcAdminDeleteBtn(ov, c);
}

// Bosh admin — nomaqbul karta rasmini o'chirish (katta ko'rinishda tugma)
let _pcWhoami = null;
async function pcAdminDeleteBtn(ov, c) {
  _pcWhoami = _pcWhoami || apiFetch("/admin/whoami").catch(() => ({}));
  if (!(await _pcWhoami).is_super || !ov.isConnected) return;
  const b = document.createElement("button");
  b.className = "btn btn--danger pcard-ov-del";
  b.textContent = pcT("pc_admin_del");
  b.addEventListener("click", async (e) => {
    e.stopPropagation();
    if (!window.confirm(pcT("pc_admin_del_q"))) return;
    b.disabled = true;
    try {
      await apiFetch(`/pcard/admin/${Number(c.user_id)}/photo`, { method: "DELETE" });
      pcRemember({ ...c, photo: null });
      ov.remove();
      showToast("✅");
    } catch (err) { b.disabled = false; showToast("❌ " + err.message); }
  });
  ov.appendChild(b);
}
document.addEventListener("click", (e) => {
  const el = e.target.closest ? e.target.closest("[data-pcard]") : null;
  if (!el || el.closest(".pcard-ov")) return;
  const c = PC_CACHE.get(Number(el.dataset.pcard));
  if (!c) return;
  e.stopPropagation();                          // Divizion ustuni: raqib profiliga o'tish o'rniga — katta karta
  pcOpenBig(c);
}, true);

const PC_AT = new Map();                          // user_id → keshga tushgan vaqt
function pcRemember(c) {
  if (c && c.user_id) { PC_CACHE.set(Number(c.user_id), c); PC_AT.set(Number(c.user_id), Date.now()); }
  return c;
}

// Profil / o'yinchi sahifasiga blok: sarlavha + karta (+ o'zimniki bo'lsa — «Kartani sozlash»)
function pcBlockHtml(c, mine) {
  return `<div class="section-label">${escHtml(pcT(mine ? "pc_title" : "pc_player_title"))}</div>
    <div class="pcard-block">${pcardHtml(c, { size: "md" })}
      ${mine ? `<button class="btn btn--ghost pcard-edit-btn" data-pcard-edit="${Number(c.user_id)}">${escHtml(pcT("pc_edit"))}</button>
        <div class="pcard-hint">${escHtml(pcT("pc_ovr_hint"))}</div>` : ""}
    </div>`;
}

// 2026-11-05: MILTILLASHSIZ — keshdagi karta darhol chiziladi, server javobi faqat o'zgargan bo'lsa DOM'ga
// tegadi, PC_TTL_MS ichida qayta so'ralmaydi (Divizion sahifasi bir ochilishda 3 marta qayta chiziladi).
const PC_TTL_MS = 60 * 1000;
function pcPaint(slot, c, mine) {
  const html = pcBlockHtml(c, mine);
  if (slot._pcHtml === html) return;
  slot.innerHTML = html;
  slot._pcHtml = html;
}

async function pcMount(slotKey, anchor, userId, mine, force = false) {
  if (!anchor || !userId) return;
  const uid = Number(userId);
  let slot = anchor.parentElement.querySelector(`:scope > [data-pcard-slot="${slotKey}"]`);
  if (!slot) {
    slot = document.createElement("div");
    slot.dataset.pcardSlot = slotKey;
    anchor.insertAdjacentElement("afterend", slot);
  }
  const cached = PC_CACHE.get(uid);
  if (slot.dataset.pcardUser !== String(uid) && !cached) { slot.innerHTML = ""; slot._pcHtml = ""; }
  slot.dataset.pcardUser = String(uid);
  if (cached) pcPaint(slot, cached, mine);
  if (!force && cached && Date.now() - (PC_AT.get(uid) || 0) < PC_TTL_MS) return;
  const seq = ++PC_SEQ[slotKey];
  try {
    const c = pcRemember(await apiFetch(`/pcard/${uid}`));
    if (seq === PC_SEQ[slotKey] && slot.isConnected) pcPaint(slot, c, mine);
  } catch (_) {
    if (seq === PC_SEQ[slotKey] && !cached) slot.innerHTML = "";   // karta chiqmasa ham profil ishlayveradi
  }
}

// 2026-11-05: karta FAQAT Divizionda (egasi: «ligalar rejimidan olib tashlang») — asosiy Profil va
// reytingdan ochilgan profilga qo'shilmaydi.
function pcRefreshMine() {
  if (typeof DIV !== "undefined" && DIV.section === "profile") pcDivHook(true);
}

// Divizion: o'z profilim va o'yinchi profili — birinchi kartadan keyin
function pcDivUid() {
  if (typeof DIV === "undefined") return null;
  if (DIV.section === "profile") return (DIV.status && DIV.status.me_id) || null;
  if (DIV.section === "player") return (DIV.player && DIV.player.user_id) || null;
  return null;
}
function pcDivHook(force = false) {
  const root = document.getElementById("div-root");
  if (!root || typeof DIV === "undefined") return;
  const mine = DIV.section === "profile";
  const uid = pcDivUid();
  const first = root.querySelector(".card");
  if (uid && first) void pcMount("div", first, uid, mine, force);
}
if (typeof renderDivision === "function") {
  const _pcPrevRenderDivision = renderDivision;
  renderDivision = function (...args) {                                              // eslint-disable-line no-global-assign
    const root = document.getElementById("div-root");
    const old = root && root.querySelector("[data-pcard-slot]");
    const r = _pcPrevRenderDivision(...args);
    // qayta chizilganda o'sha DOM tugunini qaytaramiz — rasm qayta yuklanmaydi, karta yo'qolib-chiqmaydi
    if (old && !old.isConnected && old.dataset.pcardUser === String(pcDivUid())) {
      const first = root.querySelector(".card");
      if (first) first.insertAdjacentElement("afterend", old);
    }
    pcDivHook();
    return r;
  };
}
