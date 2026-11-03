// =============================================================
//  guide_bot_faq.js — «Robi» SAVOLGA JAVOB topadi (2026-11-03). BEPUL: tashqi xizmat yo'q.
//  Bilimlar bazasi — guide_bot_faq_uz/ru/en.js (GBOT_FAQ[lang] = { ui, items }), faqat bot mavzusi:
//  savol bazadagi kalit so'zlar bilan solishtiriladi, eng mos javob qaytadi; topilmasa — null
//  (Robi «faqat bot haqida javob beraman» deydi va savol namunalarini taklif qiladi).
//  Kalit so'z: "liga" — so'z boshi (ligada, ligalar); "!liga" — muhim (2 ball); "=tur" — aynan shu so'z;
//  "klub tanla" — ikkala so'z ham bo'lsin. Qo'shimchalar uchun so'z boshi solishtiriladi.
//  Normallashtirish: kichik harf, o'zbek kirill -> lotin, tutuq belgilari (' ʻ ’ `) olib tashlanadi.
//  Savol boshqa tilda yozilsa ham topiladi (hamma tildagi baza ko'riladi) — javob ilova tilida (id bo'yicha).
// =============================================================

var GBOT_FAQ = window.GBOT_FAQ || {};
window.GBOT_FAQ = GBOT_FAQ;

const GBOT_FAQ_MIN_SCORE = 2;      // shundan kam bo'lsa — «bilmayman»
const GBOT_FAQ_CTX_BONUS = 0.5;    // hozirgi sahifaga oid savolga ustunlik
const GBOT_FAQ_PREFIX_MIN = 3;     // bundan qisqa kalit so'z — faqat aynan moslik
const GBOT_FAQ_LANGS = ["uz", "ru", "en"];
const GBOT_UZ_CYR = { "а": "a", "б": "b", "в": "v", "г": "g", "ғ": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j",
  "з": "z", "и": "i", "й": "y", "к": "k", "қ": "q", "л": "l", "м": "m", "н": "n", "о": "o", "ў": "o", "п": "p",
  "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ҳ": "h", "ц": "s", "ч": "ch", "ш": "sh", "ъ": "",
  "ь": "", "э": "e", "ю": "yu", "я": "ya" };
// O'zbek kirilida bo'ladigan, rus tilida yo'q harflar — matn o'zbekcha kirill ekanini bildiradi
const GBOT_UZ_CYR_MARK = /[ғқўҳ]/;

function gbotFaqNorm(s, lang) {
  let t = String(s || "").toLowerCase().replace(/[ʻʼ’‘'`´]/g, "");
  if (lang === "uz" && (GBOT_UZ_CYR_MARK.test(t) || !/[a-z]/.test(t))) {
    t = Array.from(t).map(ch => (ch in GBOT_UZ_CYR ? GBOT_UZ_CYR[ch] : ch)).join("");
  }
  return t.replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

function gbotFaqPrep(lang) {
  const d = GBOT_FAQ[lang];
  if (!d || d._prep) return d;
  d.items.forEach(it => {
    it._k = it.k.map(raw => {
      let s = raw, w = 1, exact = false;
      if (s.startsWith("!")) { w = 2; s = s.slice(1); }
      if (s.startsWith("=")) { exact = true; s = s.slice(1); }
      return { w, exact, words: gbotFaqNorm(s, lang).split(" ").filter(Boolean) };
    });
  });
  d._prep = true;
  return d;
}

function gbotFaqWordHit(tokens, kw, exact) {
  return tokens.some(t => (exact || kw.length < GBOT_FAQ_PREFIX_MIN ? t === kw : t.startsWith(kw)));
}

function gbotFaqScore(item, tokens, ctx) {
  let score = 0;
  item._k.forEach(g => { if (g.words.length && g.words.every(w => gbotFaqWordHit(tokens, w, g.exact))) score += g.w; });
  if (score > 0 && ctx && item.ctx && item.ctx.includes(ctx)) score += GBOT_FAQ_CTX_BONUS;
  return score;
}

function gbotFaqData(lang) {
  return gbotFaqPrep(lang) || gbotFaqPrep("uz");
}

// Eng mos javob (ilova tilida) yoki null
function gbotFaqFind(text, lang, ctx) {
  let best = null;
  GBOT_FAQ_LANGS.forEach(l => {
    const d = gbotFaqPrep(l);
    if (!d) return;
    const tokens = gbotFaqNorm(text, l).split(" ").filter(Boolean);
    if (!tokens.length) return;
    d.items.forEach(it => {
      const sc = gbotFaqScore(it, tokens, ctx) + (l === lang ? 0.01 : 0);   // teng bo'lsa — o'z tili
      if (!best || sc > best.score) best = { id: it.id, score: sc };
    });
  });
  if (!best || best.score < GBOT_FAQ_MIN_SCORE) return null;
  return gbotFaqData(lang).items.find(it => it.id === best.id) || null;
}

// Savol namunalari (tugmalar): avval shu sahifaga oidlari, keyin umumiylari
function gbotFaqSuggest(lang, ctx, n, skipId) {
  const items = gbotFaqData(lang).items.filter(it => it.q && it.id !== skipId && !it.chat);
  const mine = items.filter(it => it.ctx && it.ctx.includes(ctx));
  const rest = items.filter(it => !(it.ctx && it.ctx.includes(ctx)));
  const shuffle = arr => arr.map(v => [Math.random(), v]).sort((a, b) => a[0] - b[0]).map(x => x[1]);
  return shuffle(mine).concat(shuffle(rest)).slice(0, n);
}
