// =============================================================
//  tb_admin_draw.js — "TEAMLAR JANGI": qur'a formasi — Liga yoki UCL (2026-10-18)
//  Liga admini tanlaydi: format, bahsda necha kishi (N vs N), Liga: divizion hajmi;
//  UCL: har team nechta bahs, pley-offga nechta team, pley-off va final bahsi 1 yoki 2 o'yin.
//  Qatnasha oladigan teamlar soni N kiritilganda darhol hisoblanadi (TB.seasonPreview.lineups).
//  tb_admin_season.js chaqiradi: tbAdminDrawFormHtml(p), tbAdminDrawBody(). Backend: tb_draw.py.
//  2026-10-26: «Pley-offga chiqadi» — rasmiy ChL kabi pley-off raundi (p16/p8/p4: 1..B/2 setkaga,
//  B/2+1..1.5B raundga) yoki eski top-N (t2..t16). Teamlar yetmagan variant tanlanmaydi (disabled).
//  Global: TB, escHtml, tbAdminRender, tbI18nApply.
// =============================================================

const TB_DRAW_QUALIFY = [2, 4, 8, 16];
const TB_DRAW_PLAYIN = [16, 8, 4];                          // setka hajmi (tb_ucl.TB_UCL_PLAYIN_BRACKETS)

function tbDrawPlayinNeed(b) { return b / 2 + b; }          // tb_ucl.playin_need
function tbDrawQOptions(elig) {
  const p = TB_DRAW_PLAYIN.map(b => ({ v: `p${b}`, ok: tbDrawPlayinNeed(b) <= elig,
    lbl: `1–${b / 2} + ${b / 2 + 1}–${tbDrawPlayinNeed(b)}` }));
  const t = TB_DRAW_QUALIFY.slice().reverse().map(q => ({ v: `t${q}`, ok: q <= Math.max(2, elig), lbl: `top-${q}` }));
  return p.concat(t);
}
function tbDrawParseQ(v) {
  const m = /^([pt])(\d+)$/.exec(String(v || "")) || [null, "t", "2"];
  return { q: +m[2], playin: m[1] === "p" };
}
const TB_DRAW_ROUNDS_DEFAULT = 6;

function tbDrawEligible(p, n) { return (p.lineups || []).filter(x => x >= n).length; }

function tbDrawKoRounds(q, kl, fl, playin) {
  let total = playin ? kl : 0;                               // pley-off raundi — ko_legs o'yin
  for (let size = q; size >= 2; size /= 2) total += size === 2 ? fl : kl;
  return total;
}

function tbAdminDrawFormHtml(p) {
  const fmt = TB.drawFmt || "league";
  const n = TB.drawSize || p.lineup_min;
  const elig = tbDrawEligible(p, n);
  const seg = [["league", "🏆 Liga"], ["ucl", "⭐ UCL"]].map(([k, l]) =>
    `<button class="tb-seg-btn${fmt === k ? " active" : ""}" data-tbd-fmt="${k}">${l}</button>`).join("");
  const opts = (vals, cur, lbl) => vals.map(v => `<option value="${v}"${v === cur ? " selected" : ""}>${lbl(v)}</option>`).join("");
  const rounds = Math.max(1, Math.min(TB_DRAW_ROUNDS_DEFAULT, elig - 1));
  const qOpts = tbDrawQOptions(elig);
  const qSel = (qOpts.find(o => o.ok) || qOpts[qOpts.length - 1]).v;
  const extra = fmt === "ucl" ? `
      <div class="tb-adm-line"><span>Har team nechta bahs o'ynaydi</span>
        <input id="tbd-rounds" class="modal-input" type="number" min="1" max="30" value="${rounds}"></div>
      <div class="tb-adm-line"><span>Pley-offga chiqadi</span>
        <select id="tbd-q" class="modal-input pt-select">${qOpts.map(o =>
          `<option value="${o.v}"${o.v === qSel ? " selected" : ""}${o.ok ? "" : " disabled"}>${escHtml(o.lbl)}</option>`).join("")}</select></div>
      <div class="tb-adm-line"><span>Pley-off bahsi</span>
        <select id="tbd-kl" class="modal-input pt-select">${opts([1, 2], 2, v => v === 1 ? "1 o'yin" : "2 o'yin")}</select></div>
      <div class="tb-adm-line"><span>Final</span>
        <select id="tbd-fl" class="modal-input pt-select">${opts([1, 2], 1, v => v === 1 ? "1 o'yin" : "2 o'yin")}</select></div>
      <div class="tb-hint">Hamma teamlar bitta jadvalda tasodifiy raqiblar bilan o'ynaydi. «1–8 + 9–24» kabi variant — rasmiy ChL formati: 1–8 to'g'ridan 1/8 finalga, 9–24 pley-off raundida (9–24, 10–23 …) o'ynaydi, g'oliblar setkada 1–8 bilan uchrashadi. «top-N» — faqat top-N setkaga (1-o'rin — oxirgi o'tgan bilan). Teng bo'lsa: 1v1 g'alabalar yig'indisi → gol farqi → liga admini qarori.</div>`
    : `<div class="tb-adm-line"><span>Divizion hajmi</span>
        <input id="tbs-divsize" class="modal-input" type="number" min="4" max="20" value="${p.division_size}"></div>`;
  return `<div class="tb-seg">${seg}</div>
    <div class="tb-adm-line"><span>Bahsda o'yinchilar (N vs N)</span>
      <input id="tbd-size" class="modal-input" type="number" min="1" max="30" value="${n}"></div>
    <div class="tb-hint" id="tbd-elig">${tbDrawSummary(p, qSel)}</div>
    ${extra}
    <button class="btn btn--primary" data-tbsa="create">🎲 Qur'a o'tkazish (yangi mavsum)</button>`;
}

function tbDrawVal(id, dflt) {
  const v = document.getElementById(id)?.value;
  return v === undefined || v === "" ? dflt : +v;
}

// qDefault — forma birinchi chizilayotganda (tanlov hali DOM'da yo'q) tanlangan variant
function tbDrawSummary(p, qDefault) {
  const n = tbDrawVal("tbd-size", TB.drawSize || p.lineup_min);
  const elig = tbDrawEligible(p, n);
  let txt = `${n} vs ${n}: qatnasha oladi ${elig} ta team (asosiy tarkibi ≥ ${n}).`;
  if ((TB.drawFmt || "league") === "ucl") {
    const r = tbDrawVal("tbd-rounds", Math.max(1, Math.min(TB_DRAW_ROUNDS_DEFAULT, elig - 1)));
    const sel = tbDrawParseQ(qDefault || document.getElementById("tbd-q")?.value);
    const ko = tbDrawKoRounds(sel.q, tbDrawVal("tbd-kl", 2), tbDrawVal("tbd-fl", 1), sel.playin);
    txt += ` Jami ${r + ko} tur (kun): liga bosqichi ${r} + pley-off ${ko}.`;
  }
  return txt;
}

function tbAdminDrawBody() {
  const body = { format: TB.drawFmt || "league", match_size: tbDrawVal("tbd-size", null) };
  if (body.format === "ucl") {
    const sel = tbDrawParseQ(document.getElementById("tbd-q")?.value);
    Object.assign(body, { ucl_rounds: tbDrawVal("tbd-rounds", null), ucl_qualify: sel.q, ucl_playin: sel.playin,
                          ko_legs: tbDrawVal("tbd-kl", 1), final_legs: tbDrawVal("tbd-fl", 1) });
  } else {
    body.division_size = tbDrawVal("tbs-divsize", null);
  }
  return body;
}

function tbDrawRefresh() {
  const box = document.getElementById("tbd-elig");
  if (box && TB.seasonPreview) { box.textContent = tbDrawSummary(TB.seasonPreview); tbI18nApply(box); }
}

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("#tb-root [data-tbd-fmt]") : null;
  if (!b) return;
  TB.drawSize = tbDrawVal("tbd-size", TB.drawSize);
  TB.drawFmt = b.dataset.tbdFmt;
  const y = window.scrollY;
  tbAdminRender();
  window.scrollTo(0, y);
});
document.addEventListener("input", (e) => {
  if (e.target.closest && e.target.closest("#tb-root .tb-adm-season")) tbDrawRefresh();
});
document.addEventListener("change", (e) => {
  if (e.target.closest && e.target.closest("#tb-root .tb-adm-season")) tbDrawRefresh();
});
