// =============================================================
//  shop_stack.js — Do'kon paketlari rasmi: eF Token MIQDORI ko'rinadigan uyum (2026-10-31)
//  v2 (egasi yuborgan eFootball do'koni rasmi kabi): tokenlar yotqizilgan holda USTUNLARGA taxlanadi,
//  ustunlar zich to'da bo'lib turadi (1 → 2 → uchburchak → romb → ...), har ustun tepasida eF belgisi
//  qiya ko'rinishda. Tik turgan token yo'q (namunadagi kabi).
//  Hisob: token soni n = coins / SHOP_STACK_UNIT (kamida 1) — ustunlarga teng taqsimlanadi;
//  ustunlar soni n ga qarab ortadi (SHOP_STACK_TIERS), baland ustunda token qalinligi kamayadi.
//  Faqat SVG — rasm fayli yo'q.
// =============================================================

const SHOP_STACK_UNIT = 100;                 // bitta token = 100 eF
const SHOP_STACK_W = 180, SHOP_STACK_H = 124, SHOP_STACK_BASE = 104;
const SHOP_STACK_K = 0.6;                    // token belgisi (100×100) -> yotgan token o'lchami
const SHOP_STACK_SQ = 0.55;                  // qiya ko'rinish (balandlik siqilishi)
const SHOP_STACK_T_MAX = 5.5, SHOP_STACK_H_MAX = 44;   // token qalinligi / ustun eng katta balandligi (px)
// [shu songacha tokenlar, ustunlar soni]
const SHOP_STACK_TIERS = [[6, 1], [14, 2], [27, 3], [44, 4], [60, 5], [Infinity, 6]];
// Ustunlar joylashuvi (x, chuqurlik y; manfiy y — orqada): namunadagi to'dalar kabi
const SHOP_STACK_LAYOUTS = {
  1: [[0, 0]],
  2: [[30, -10], [-26, 4]],
  3: [[0, -24], [-30, 4], [30, 8]],
  4: [[-26, -26], [28, -22], [-38, 6], [16, 12]],
  5: [[-30, -28], [26, -28], [-50, 4], [0, 4], [50, 6]],
  6: [[-50, -26], [0, -30], [50, -26], [-40, 6], [8, 10], [54, 8]],
};
// Token yuzi (images/ef-token.svg bilan bir xil koordinatalar, 0..100)
const SHOP_HEX = [[50, 5], [89, 27.5], [89, 72.5], [50, 95], [11, 72.5], [11, 27.5]];
const SHOP_HEX_IN = [[50, 15], [80, 32.5], [80, 67.5], [50, 85], [20, 67.5], [20, 32.5]];
const SHOP_EF_PATH = "M30.5 52h19a9.5 9.5 0 1 0 -3.4 7.3 M58.5 62V43a5 5 0 0 1 5 -5h7 M54 50h13";

let _shopStackUid = 0;

function shopStackPt(cx, cy, x, y) {
  return `${(cx + (x - 50) * SHOP_STACK_K).toFixed(1)},${(cy + (y - 50) * SHOP_STACK_K * SHOP_STACK_SQ).toFixed(1)}`;
}

// Bitta yotgan token: yon tomoni (pastki 3 qirra qalinlik bilan) + yuzi; eng tepadagida eF belgisi
function shopStackCoin(cx, cy, t, top, uid) {
  const P = (x, y, dy = 0) => shopStackPt(cx, cy + dy, x, y);
  const side = [P(89, 72.5), P(50, 95), P(11, 72.5), P(11, 72.5, t), P(50, 95, t), P(89, 72.5, t)].join(" ");
  const face = SHOP_HEX.map(([x, y]) => P(x, y)).join(" ");
  let s = `<polygon points="${side}" fill="url(#ssd${uid})" stroke="#1a0a52" stroke-width=".6"/>
    <polygon points="${face}" fill="url(#ssf${uid})" stroke="url(#sse${uid})" stroke-width="1.5" stroke-linejoin="round"/>`;
  if (top) {
    const inner = SHOP_HEX_IN.map(([x, y]) => P(x, y)).join(" ");
    const sx = SHOP_STACK_K, sy = SHOP_STACK_K * SHOP_STACK_SQ;
    s += `<polygon points="${inner}" fill="none" stroke="#00f0ff" stroke-opacity=".3" stroke-width=".8"/>
      <path d="${SHOP_EF_PATH}" transform="translate(${(cx - 50 * sx).toFixed(1)} ${(cy - 50 * sy).toFixed(1)}) scale(${sx} ${sy})"
        fill="none" stroke="url(#sse${uid})" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>`;
  }
  return s;
}

function shopStackCounts(n) {
  const piles = SHOP_STACK_TIERS.find(([upto]) => n <= upto)[1];
  const base = Math.floor(n / piles), extra = n % piles;
  return Array.from({ length: piles }, (_, i) => base + (i < extra ? 1 : 0));   // ortiqchasi — orqa ustunlarga
}

function shopStackSvg(coins) {
  const n = Math.max(1, Math.round((Number(coins) || 0) / SHOP_STACK_UNIT));
  const uid = ++_shopStackUid;
  const counts = shopStackCounts(n);
  const layout = SHOP_STACK_LAYOUTS[counts.length];
  const t = Math.min(SHOP_STACK_T_MAX, SHOP_STACK_H_MAX / Math.max(...counts));
  const cx0 = SHOP_STACK_W / 2;
  const order = layout.map((p, i) => ({ x: p[0], y: p[1], c: counts[i] })).sort((a, b) => a.y - b.y);   // orqadagilar birinchi
  const body = order.map(({ x, y, c }) => {
    let s = "";
    for (let i = 0; i < c; i++) s += shopStackCoin(cx0 + x, SHOP_STACK_BASE + y - 16 - i * t, t, i === c - 1, uid);
    return s;
  }).join("");
  return `<svg class="shop-stack" viewBox="0 0 ${SHOP_STACK_W} ${SHOP_STACK_H}" role="img" aria-label="${n} × eF">
      <defs>
        <linearGradient id="ssd${uid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3a1590"/><stop offset=".45" stop-color="#6a3cf0"/><stop offset="1" stop-color="#1d4fb8"/></linearGradient>
        <linearGradient id="ssf${uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#231f52"/><stop offset="1" stop-color="#0d0c22"/></linearGradient>
        <linearGradient id="sse${uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00f0ff"/><stop offset="1" stop-color="#7b2fff"/></linearGradient>
        <radialGradient id="ssg${uid}" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#00f0ff" stop-opacity=".22"/><stop offset="1" stop-color="#00f0ff" stop-opacity="0"/></radialGradient>
      </defs>
      <ellipse cx="${cx0}" cy="${SHOP_STACK_BASE + 6}" rx="${30 + counts.length * 10}" ry="9" fill="url(#ssg${uid})"/>
      ${body}
    </svg>`;
}
