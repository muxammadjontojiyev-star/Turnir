// =============================================================
//  shop_stack.js — Do'kon paketlari rasmi: eF Token MIQDORI ko'rinadigan uyum (2026-10-31)
//  Egasi so'rovi: 100 eF — 1 ta token, 300 — 3 ta, 800 — 8 ta ...; tokenlar orqasiga qo'yib ko'paytirilmasin —
//  YOTQIZIB TAXLANGAN (ustma-ust ustunlar) bo'lsin va BITTASI TIK turgan bo'lsin.
//  Hisob: n = coins / SHOP_STACK_UNIT (kamida 1). 1 tasi oldinda tik (images/ef-token.svg), qolgan n−1 tasi
//  ustunlarga taqsimlanadi: ustunda SHOP_STACK_PILE_MAX tagacha, ustunlar soni SHOP_STACK_SLOTS.length dan
//  oshmaydi (juda katta paketda ustun balandroq bo'ladi). Faqat SVG — rasm fayli yo'q.
//  Global: SHOP_TOKEN_IMG (shop.js).
// =============================================================

const SHOP_STACK_UNIT = 100;           // bitta token = 100 eF
const SHOP_STACK_PILE_MAX = 8;         // ustundagi tokenlar (ustunlar yetmasa — ko'proq)
const SHOP_STACK_W = 180, SHOP_STACK_H = 108, SHOP_STACK_BASE = 98;
const SHOP_STACK_R = 18;               // yotgan tokenning yarim kengligi
const SHOP_STACK_SQ = 0.42;            // qiya ko'rinish (balandlik siqilishi)
const SHOP_STACK_T = 4;                // token qalinligi
// Ustun joylari (markazdan x, asosdan y) — to'ldirish tartibida; chizishda orqadagilar birinchi
const SHOP_STACK_SLOTS = [[-38, 0], [38, 0], [-68, -10], [68, -10], [-17, -19], [17, -19], [-49, -27], [49, -27]];

let _shopStackUid = 0;

function shopStackDisc(cx, y, top, uid) {
  const r = SHOP_STACK_R, h = r * 0.866 * SHOP_STACK_SQ, t = SHOP_STACK_T;
  const P = (dx, dy) => `${(cx + dx).toFixed(1)},${(y + dy).toFixed(1)}`;
  const side = [P(r, 0), P(r / 2, h), P(-r / 2, h), P(-r, 0), P(-r, t), P(-r / 2, h + t), P(r / 2, h + t), P(r, t)].join(" ");
  const face = [P(r, 0), P(r / 2, h), P(-r / 2, h), P(-r, 0), P(-r / 2, -h), P(r / 2, -h)].join(" ");
  const k = 0.62;
  const inner = [P(r * k, 0), P(r / 2 * k, h * k), P(-r / 2 * k, h * k), P(-r * k, 0), P(-r / 2 * k, -h * k), P(r / 2 * k, -h * k)].join(" ");
  return `<polygon points="${side}" fill="url(#ssd${uid})"/>
    <polygon points="${face}" fill="#16143a" stroke="url(#sse${uid})" stroke-width="1.6" stroke-linejoin="round"/>
    ${top ? `<polygon points="${inner}" fill="none" stroke="#00f0ff" stroke-opacity=".45" stroke-width=".8"/>` : ""}`;
}

function shopStackPiles(flat) {
  if (flat <= 0) return [];
  const slots = SHOP_STACK_SLOTS.length;
  const p = Math.min(slots, Math.ceil(flat / SHOP_STACK_PILE_MAX));
  const base = Math.floor(flat / p), extra = flat % p;
  return Array.from({ length: p }, (_, i) => ({ slot: SHOP_STACK_SLOTS[i], n: base + (i < extra ? 1 : 0) }));
}

function shopStackSvg(coins) {
  const n = Math.max(1, Math.round((Number(coins) || 0) / SHOP_STACK_UNIT));
  const uid = ++_shopStackUid;
  const cx0 = SHOP_STACK_W / 2;
  const piles = shopStackPiles(n - 1).sort((a, b) => a.slot[1] - b.slot[1] || Math.abs(b.slot[0]) - Math.abs(a.slot[0]));
  const body = piles.map(({ slot, n: cnt }) => {
    let s = "";
    for (let i = 0; i < cnt; i++) s += shopStackDisc(cx0 + slot[0], SHOP_STACK_BASE + slot[1] - i * SHOP_STACK_T - SHOP_STACK_T, i === cnt - 1, uid);
    return s;
  }).join("");
  const tw = 54, th = 62;                                   // tik turgan token — oldinda, markazda
  return `<svg class="shop-stack" viewBox="0 0 ${SHOP_STACK_W} ${SHOP_STACK_H}" role="img" aria-label="${n} × eF">
      <defs>
        <linearGradient id="ssd${uid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3a1590"/><stop offset=".5" stop-color="#5b2fe0"/><stop offset="1" stop-color="#1d4fb8"/></linearGradient>
        <linearGradient id="sse${uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00f0ff"/><stop offset="1" stop-color="#7b2fff"/></linearGradient>
        <radialGradient id="ssg${uid}" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#00f0ff" stop-opacity=".28"/><stop offset="1" stop-color="#00f0ff" stop-opacity="0"/></radialGradient>
      </defs>
      <ellipse cx="${cx0}" cy="${SHOP_STACK_BASE + 4}" rx="${piles.length ? 80 : 30}" ry="7" fill="url(#ssg${uid})"/>
      ${body}
      <image href="${SHOP_TOKEN_IMG}" x="${cx0 - tw / 2}" y="${SHOP_STACK_BASE + 4 - th}" width="${tw}" height="${th}"/>
    </svg>`;
}
