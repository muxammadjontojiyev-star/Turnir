// =============================================================
//  player_card.js — ISHTIROKCHINING SHAXSIY O'YINCHI KARTASI (2026-11-04, player_card.py)
//  eFootball kartasi uslubida: ramka foni (images/card-showtime.jpg), futbolchi o'rnida — ishtirokchi rasmidan
//  qirqilgan ODAMNING O'ZI (GET /players/{id}/cutout; bo'lmasa — butun rasm), chap tepada OVR,
//  pozitsiya, bayroq; pastda nik va yulduzlar. Dizayn — player_card.css.
//  Ko'rinadi: Profil sahifasi (renderProfile o'raladi), reytingdan ochilgan profil (renderPlayerModal),
//  Divizion o'z profili / o'yinchi profili (renderDivision o'raladi), Divizion qur'a kartasi (division.js
//  pcardHtml'ni chaqiradi). Kartani bosish — katta ko'rinish. API: GET /pcard/{user_id}.
//  Global: APP, API_BASE, apiFetch, escHtml. Ulanish: api.js, cosmetics.js, division.js dan KEYIN.
// =============================================================

const PC_STAR_TIERS = [90, 80, 70, 60];          // OVR ≥ shu → 5/4/3/2 yulduz, qolgani — 1
const PC_LONG_NAME = 11;                         // shundan uzun nik — kichikroq shrift
const PC_BG_RE = /^card_[a-z0-9_]{1,30}$/;
const PC_POS_RE = /^[A-Z]{2,3}$/;
const PC_CC_RE = /^[A-Z]{2}$/;
const PC_SEQ = { profile: 0, player: 0, div: 0 }; // eski javob yangisini bosib ketmasin

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

// Qirqilgan rasm (faqat odam, player_cutout.py) bo'lmasa — butun rasm, chetlari xira; u ham bo'lmasa — ism harfi
function pcCutFail(img) {
  const fb = img.dataset.fb;
  if (!fb) { img.remove(); return; }
  delete img.dataset.fb;
  img.parentElement.classList.add("pcard-photo--plain");
  img.src = fb;
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
        <div class="pcard-photo">
          <img src="${API_BASE}/players/${Number(c.user_id)}/cutout" data-fb="${escHtml(pcPhotoSrc(c))}" alt="" loading="lazy"
            onerror="pcCutFail(this)"><span class="pcard-letter">${escHtml(name[0].toUpperCase())}</span>
        </div>
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
}
document.addEventListener("click", (e) => {
  const el = e.target.closest ? e.target.closest("[data-pcard]") : null;
  if (!el || el.closest(".pcard-ov")) return;
  const c = PC_CACHE.get(Number(el.dataset.pcard));
  if (!c) return;
  e.stopPropagation();                          // Divizion ustuni: raqib profiliga o'tish o'rniga — katta karta
  pcOpenBig(c);
}, true);

function pcRemember(c) { if (c && c.user_id) PC_CACHE.set(Number(c.user_id), c); return c; }

// Profil / o'yinchi sahifasiga blok: sarlavha + karta (+ o'zimniki bo'lsa — «Kartani sozlash»)
function pcBlockHtml(c, mine) {
  return `<div class="section-label">${escHtml(pcT(mine ? "pc_title" : "pc_player_title"))}</div>
    <div class="pcard-block">${pcardHtml(pcRemember(c), { size: "md" })}
      ${mine ? `<button class="btn btn--ghost pcard-edit-btn" data-pcard-edit="${Number(c.user_id)}">${escHtml(pcT("pc_edit"))}</button>
        <div class="pcard-hint">${escHtml(pcT("pc_ovr_hint"))}</div>` : ""}
    </div>`;
}

async function pcMount(slotKey, anchor, userId, mine) {
  if (!anchor || !userId) return;
  const seq = ++PC_SEQ[slotKey];
  let slot = anchor.parentElement.querySelector(`:scope > [data-pcard-slot="${slotKey}"]`);
  if (!slot) {
    slot = document.createElement("div");
    slot.dataset.pcardSlot = slotKey;
    anchor.insertAdjacentElement("afterend", slot);
  }
  try {
    const c = await apiFetch(`/pcard/${Number(userId)}`);
    if (seq !== PC_SEQ[slotKey]) return;
    slot.innerHTML = pcBlockHtml(c, mine);
  } catch (_) {
    if (seq === PC_SEQ[slotKey]) slot.innerHTML = "";        // karta chiqmasa ham profil ishlayveradi
  }
}

function pcRefreshMine() {
  const uid = (APP.profileData && APP.profileData.user_id) || PCE.uid;
  const card = document.getElementById("profile-avatar-letter")?.closest(".card--profile");
  if (uid && card) void pcMount("profile", card, uid, true);
  if (typeof DIV !== "undefined" && DIV.section === "profile") pcDivHook();
}

if (typeof renderProfile === "function") {
  const _pcPrevRenderProfile = renderProfile;
  renderProfile = function (data) {                                                   // eslint-disable-line no-global-assign
    _pcPrevRenderProfile(data);
    const card = document.getElementById("profile-avatar-letter")?.closest(".card--profile");
    if (data && data.user_id) void pcMount("profile", card, data.user_id, true);
  };
}
if (typeof renderPlayerModal === "function") {
  const _pcPrevRenderPlayer = renderPlayerModal;
  renderPlayerModal = function (data) {                                               // eslint-disable-line no-global-assign
    _pcPrevRenderPlayer(data);
    const card = document.getElementById("player-avatar-letter")?.closest(".card--profile");
    if (data && data.user_id) void pcMount("player", card, data.user_id, false);
  };
}

// Divizion: o'z profilim va o'yinchi profili — birinchi kartadan keyin
function pcDivHook() {
  const root = document.getElementById("div-root");
  if (!root || typeof DIV === "undefined") return;
  const mine = DIV.section === "profile";
  const uid = mine ? DIV.status && DIV.status.me_id : DIV.section === "player" ? DIV.player && DIV.player.user_id : null;
  const first = root.querySelector(".card");
  if (uid && first) void pcMount("div", first, uid, mine);
}
if (typeof renderDivision === "function") {
  const _pcPrevRenderDivision = renderDivision;
  renderDivision = function (...args) {                                              // eslint-disable-line no-global-assign
    const r = _pcPrevRenderDivision(...args);
    pcDivHook();
    return r;
  };
}
