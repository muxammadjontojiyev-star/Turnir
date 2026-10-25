// =============================================================
//  guide.js — butun bot bo'yicha QO'LLANMA (2026-10-25)
//  Yangi foydalanuvchilar uchun: bo'limlar ro'yxati -> bo'lim sahifasi (qadamlar, maslahatlar,
//  ixtiyoriy rasmlar static/images/guide/). Matnlar: guide_uz.js / guide_ru.js / guide_en.js
//  (GUIDE_I18N[lang] = { ui, sections }). Til — APP.lang, topilmasa o'zbekcha.
//  Kirish nuqtalari:
//    - bo'lim tanlash ekranidagi «📖 Qo'llanma» tugmasi (app.js showHubSelect -> guideHubButtonHtml);
//    - Teamlar jangi sarlavhasidagi «❓» (tb.js) -> openGuide("tb");
//    - bot /help va «Kirish» xabaridagi tugma: ?guide=<bo'lim> (app.js showEntryScreen -> guideConsumeParam);
//    - birinchi kirishda bir marta avtomatik (guideMaybeAutoOpen, localStorage).
//  Global: APP, escHtml, chatImgLightbox (chat_images.js), adminContact (APP.adminContact).
// =============================================================

const GUIDE = { open: false, section: null };
const GUIDE_SEEN_KEY = "guide_seen_v1";
const GUIDE_IMG_VER = "20261025a";

function guideLang() {
  const l = (typeof APP !== "undefined" && APP.lang) || "uz";
  return (typeof GUIDE_I18N !== "undefined" && GUIDE_I18N[l]) ? l : "uz";
}
function guideData() { return GUIDE_I18N[guideLang()]; }

// **qalin** -> <b>, qolgani escape (matn faqat bizning fayllarimizdan, lekin baribir xavfsiz)
function guideFmt(s) { return escHtml(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>"); }

function guideHubButtonHtml() {
  if (typeof GUIDE_I18N === "undefined") return "";
  const u = guideData().ui;
  return `<button class="guide-hub-btn" id="guide-hub-btn" data-guide-open="list">
      <span class="guide-hub-ico">📖</span>
      <span class="guide-hub-txt"><b>${escHtml(u.hub_btn)}</b><small>${escHtml(u.hub_btn_sub)}</small></span>
      <span class="guide-hub-go">›</span>
    </button>`;
}

// ?guide=<bo'lim> yoki Telegram startapp "guide" / "guide_<bo'lim>" (bir marta o'qiladi)
function guideConsumeParam() {
  let v = null;
  try {
    const p = new URLSearchParams(window.location.search);
    v = p.get("guide");
    if (v !== null) {
      p.delete("guide");
      const q = p.toString();
      window.history.replaceState(null, "", window.location.pathname + (q ? "?" + q : "") + window.location.hash);
    }
  } catch (_) { v = null; }
  if (v === null && !GUIDE._spUsed) {
    const sp = window.Telegram?.WebApp?.initDataUnsafe?.start_param || "";
    if (sp === "guide" || sp.startsWith("guide_")) { v = sp.slice(6) || "start"; GUIDE._spUsed = true; }
  }
  if (v === null) return null;
  return /^[a-z]{2,12}$/.test(v) ? v : "start";
}

function guideMaybeAutoOpen() {
  let seen = true;                                   // xotira ishlamasa — har safar ochilmasin
  try { seen = localStorage.getItem(GUIDE_SEEN_KEY) === "1"; } catch (_) { seen = true; }
  if (!seen) openGuide(null);
}

function guideMarkSeen() { try { localStorage.setItem(GUIDE_SEEN_KEY, "1"); } catch (_) { /* xotira yopiq */ } }

function openGuide(sectionId) {
  let root = document.getElementById("guide-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "guide-root";
    root.className = "guide-root";
    root.setAttribute("role", "dialog");
    document.body.appendChild(root);
    root.addEventListener("click", guideClick);
  }
  const ids = guideData().sections.map(s => s.id);
  GUIDE.section = ids.includes(sectionId) ? sectionId : null;
  GUIDE.open = true;
  guideMarkSeen();
  root.classList.remove("hidden");
  document.body.classList.add("guide-lock");
  guideRender();
}

function closeGuide() {
  GUIDE.open = false;
  document.getElementById("guide-root")?.classList.add("hidden");
  document.body.classList.remove("guide-lock");
}

function guideRender() {
  const root = document.getElementById("guide-root");
  if (!root) return;
  const d = guideData(), u = d.ui;
  const sec = d.sections.find(s => s.id === GUIDE.section);
  root.innerHTML = `
    <div class="guide-head">
      <button class="guide-x" data-guide="${sec ? "list" : "close"}" aria-label="${escHtml(sec ? u.back : u.close)}">${sec ? "←" : "✕"}</button>
      <div class="guide-title">📖 ${escHtml(sec ? sec.title : u.title)}</div>
      ${sec ? `<button class="guide-x" data-guide="close" aria-label="${escHtml(u.close)}">✕</button>` : "<span></span>"}
    </div>
    <div class="guide-body">${sec ? guideSectionHtml(sec, d) : guideListHtml(d)}</div>`;
  root.scrollTop = 0;
}

function guideListHtml(d) {
  const u = d.ui;
  return `<div class="guide-intro">${guideFmt(u.intro)}</div>
    <div class="guide-list">${d.sections.map(s => `
      <button class="guide-item" data-guide-open="${s.id}">
        <span class="guide-item-ico">${s.icon}</span>
        <span class="guide-item-txt"><b>${escHtml(s.title)}</b><small>${escHtml(s.sub)}</small></span>
        <span class="guide-item-go">›</span>
      </button>`).join("")}</div>`;
}

function guideStepHtml(st) {
  const o = typeof st === "string" ? { t: st } : st;
  const img = o.img ? `<figure class="guide-fig">
      <img src="images/guide/${escHtml(o.img)}?v=${GUIDE_IMG_VER}" alt="${escHtml(o.cap || "")}" loading="lazy"
        data-guide-zoom="1" onerror="this.closest('figure').remove()">
      ${o.cap ? `<figcaption>${guideFmt(o.cap)}</figcaption>` : ""}</figure>` : "";
  return `<li><div>${guideFmt(o.t)}</div>${img}</li>`;
}

function guideSectionHtml(s, d) {
  const u = d.ui, i = d.sections.indexOf(s), next = d.sections[i + 1];
  const contact = s.id === "fair" && APP.adminContact && APP.adminContact.username
    ? `<button class="btn btn--ghost guide-contact" data-guide="contact">✉️ ${escHtml(u.admin_write)} ${escHtml(APP.adminContact.username)}</button>` : "";
  return `
    <div class="guide-sec-head"><span class="guide-sec-ico">${s.icon}</span><p>${guideFmt(s.intro)}</p></div>
    ${s.steps && s.steps.length ? `<div class="section-label">${escHtml(s.steps_title || u.steps)}</div>
      <ol class="guide-steps">${s.steps.map(guideStepHtml).join("")}</ol>` : ""}
    ${s.tips && s.tips.length ? `<div class="section-label">${escHtml(s.tips_title || u.tips)}</div>
      <ul class="guide-tips">${s.tips.map(t => `<li>${guideFmt(t)}</li>`).join("")}</ul>` : ""}
    ${contact}
    <div class="guide-nav">
      <button class="btn btn--ghost" data-guide="list">← ${escHtml(u.all_sections)}</button>
      ${next ? `<button class="btn btn--primary" data-guide-open="${next.id}">${escHtml(next.title)} ›</button>` : ""}
    </div>`;
}

function guideClick(e) {
  const t = e.target;
  if (!t.closest) return;
  const op = t.closest("[data-guide-open]");
  if (op) { GUIDE.section = op.dataset.guideOpen; guideRender(); return; }
  const z = t.closest("[data-guide-zoom]");
  if (z && typeof chatImgLightbox === "function") { chatImgLightbox(z.getAttribute("src")); return; }
  const b = t.closest("[data-guide]");
  if (!b) return;
  const a = b.dataset.guide;
  if (a === "close") closeGuide();
  else if (a === "list") { GUIDE.section = null; guideRender(); }
  else if (a === "contact" && APP.adminContact) {
    const url = APP.adminContact.url || `https://t.me/${encodeURIComponent(String(APP.adminContact.username).replace(/^@/, ""))}`;
    const w = window.Telegram?.WebApp;
    if (w?.openTelegramLink && /^https:\/\/t\.me\//.test(url)) w.openTelegramLink(url); else window.open(url, "_blank");
  }
}

// Bo'lim tanlash ekranidagi tugma va boshqa joylardagi «❓» (root tashqarisida)
document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-guide-open]") : null;
  if (b && !b.closest("#guide-root")) openGuide(b.dataset.guideOpen);
});
