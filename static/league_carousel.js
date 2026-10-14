// =============================================================
//  league_carousel.js — Asosiy sahifadagi LIGA TANLASH karuseli (2026-10-14)
//  Mobil o'yinlardagidek: ligalar chapga/o'ngga suriladi, markazdagisi katta va
//  yaqin, qo'shnilari orqada kichikroq va xiraroq (3D "coverflow").
//  - Surish — brauzerning o'z scroll'i (inersiya + scroll-snap), shuning uchun silliq;
//  - 3D ko'rinish — har kadrda faqat transform/opacity (rAF bilan, layout'siz);
//  - surish to'xtaganda markazdagi liga avtomatik TANLANADI (api.js dagi click mantig'i);
//    yopiq (navbati kelmagan) liga markazda ko'rinadi, lekin tanlanmaydi;
//  - chetdagi kartaga bosish — uni markazga olib keladi.
//  api.js renderLeagues() oxirida leagueCarouselInit(list) chaqiriladi.
// =============================================================

const LC_MAX_ROTATE_DEG = 32;   // qo'shni kartaning burilishi
const LC_DEPTH_PX       = 140;  // har qadamda orqaga ketish (translateZ)
const LC_MIN_SCALE      = 0.74; // eng chetki kartaning kattaligi
const LC_FADE_PER_STEP  = 0.38; // har qadamda xiralashish
const LC_SETTLE_MS      = 140;  // scroll to'xtadi deb hisoblash (scrollend yo'q brauzerlar)

function lcItems(list) {
  return Array.from(list.querySelectorAll(".league-item"));
}

// Kartaning markazdan "qadam"lardagi masofasi (-1 — chapdagi qo'shni, 0 — markaz)
function lcOffset(list, item) {
  const center = list.scrollLeft + list.clientWidth / 2;
  const itemCenter = item.offsetLeft + item.offsetWidth / 2;
  return (itemCenter - center) / (item.offsetWidth || 1);
}

function lcPaint(list) {
  lcItems(list).forEach(item => {
    const d = lcOffset(list, item);
    const a = Math.min(Math.abs(d), 2.2);
    const rot = Math.max(-1, Math.min(1, d)) * -LC_MAX_ROTATE_DEG;
    const scale = Math.max(LC_MIN_SCALE, 1 - a * 0.16);
    item.style.transform = `perspective(900px) translateZ(${-a * LC_DEPTH_PX}px) rotateY(${rot}deg) scale(${scale})`;
    item.style.opacity = String(Math.max(0.15, 1 - a * LC_FADE_PER_STEP));
    item.style.zIndex = String(100 - Math.round(a * 10));
    item.classList.toggle("lc-center", a < 0.5);
  });
}

function lcCenteredItem(list) {
  let best = null, bestD = Infinity;
  lcItems(list).forEach(item => {
    const d = Math.abs(lcOffset(list, item));
    if (d < bestD) { bestD = d; best = item; }
  });
  return best;
}

function lcScrollTo(list, item, smooth) {
  const left = item.offsetLeft - (list.clientWidth - item.offsetWidth) / 2;
  list.scrollTo({ left, behavior: smooth ? "smooth" : "auto" });
}

// Surish to'xtaganda markazdagi ligani tanlash (yopiq bo'lsa — faqat ko'rinadi)
function lcSettle(list) {
  const item = lcCenteredItem(list);
  if (!item || item.classList.contains("selected") || item.classList.contains("league-item--locked")) return;
  list._lcAuto = true;          // click handler'ga: bu foydalanuvchi bosishi emas
  item.click();
  list._lcAuto = false;
}

function leagueCarouselInit(list) {
  if (!list) return;
  list.classList.add("lc");

  if (!list._lcBound) {
    list._lcBound = true;
    let frame = 0, settleTimer = 0;
    list.addEventListener("scroll", () => {
      if (!frame) frame = requestAnimationFrame(() => { frame = 0; lcPaint(list); });
      clearTimeout(settleTimer);
      settleTimer = setTimeout(() => lcSettle(list), LC_SETTLE_MS);
    }, { passive: true });
    // Chetdagi kartaga bosish — markazga olib kelish (tanlash api.js click'ida)
    list.addEventListener("click", (e) => {
      if (list._lcAuto) return;
      const item = e.target.closest(".league-item");
      if (item && !item.classList.contains("lc-center")) lcScrollTo(list, item, true);
    });
    // Sahifa yashirin paytda chizilgan bo'lsa (kenglik 0) — ko'ringanda markazlash
    if (typeof ResizeObserver === "function") {
      let lastW = list.clientWidth;
      new ResizeObserver(() => {
        if (list.clientWidth === lastW) return;
        lastW = list.clientWidth;
        const sel = list.querySelector(".league-item.selected");
        if (sel) lcScrollTo(list, sel, false);
        lcPaint(list);
      }).observe(list);
    }
  }

  // Tanlangan liga markazda boshlanadi (animatsiyasiz)
  const selected = list.querySelector(".league-item.selected") || lcItems(list)[0];
  requestAnimationFrame(() => {
    if (selected) lcScrollTo(list, selected, false);
    lcPaint(list);
  });
}
