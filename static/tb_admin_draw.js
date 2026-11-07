// =============================================================
//  tb_admin_draw.js — "TEAMLAR JANGI": keyingi mavsum rejasi va qur'a (2026-10-18; qayta tuzildi 2026-11-07)
//  2026-11-07 (egasi: «Liga admini UCL formatini tanlab saqlash tugmasini bosadigan bo'lsin … UCL formatida mavjud
//  teamlar sonidan kelib chiqib bo'lajak o'yinlar formati tashkil etilishi kerak»):
//    1) format (Liga / UCL) → 2) har bahsda nechta o'yinchi (N vs N) → 3) «📋 Mavsum rejasi» avtomatik tuziladi
//    (qatnasha oladigan teamlar soniga qarab; qoida tb_plan.auto_ucl bilan bir xil) → «💾 Saqlash» (server:
//    POST /tb/admin/league/draw-plan) → «🎲 Qur'a o'tkazish» faqat saqlangan reja bilan ochiladi.
//    «⚙️ Qo'lda o'zgartirish» — ixtiyoriy (bahslar soni, pley-off, 1/2 o'yin; Liga: divizion hajmi).
//  tb_admin_season.js chaqiradi: tbAdminDrawFormHtml(p, noDraw), tbAdminDrawBody(). Server tekshiradi: tb_ucl.validate_ucl.
//  Global: TB, apiFetch, escHtml, showToast, tbErr, tbAdminRender.
// =============================================================

const TBD_ROUNDS_MAX = 6, TBD_PLAYIN_BIG = 24, TBD_PLAYIN_MID = 12, TBD_TOP4_FROM = 8, TBD_TWO_LEGS_FROM = 8;  // tb_plan.py
const TBD_DIV_TAIL_MIN = 6;                                  // tb_season.TB_DIV_TAIL_MIN
const TBD_Q_OPTIONS = ["p16", "p8", "p4", "t16", "t8", "t4", "t2"];
const TBD_STAGE = { 16: "1/8 final", 8: "Chorak final", 4: "Yarim final", 2: "Final" };

function tbdPlayinNeed(b) { return b / 2 + b; }               // tb_ucl.playin_need
function tbdMaxRounds(n) { return n % 2 === 0 ? n - 1 : n; }
function tbdEligible(p, n) { return (p.lineups || []).filter(x => x >= n).length; }

function tbdAutoUcl(n) {                                    // tb_plan.auto_ucl
  if (n < 2) return null;
  const [q, playin] = n >= TBD_PLAYIN_BIG ? [16, true] : n >= TBD_PLAYIN_MID ? [8, true] : n >= TBD_TOP4_FROM ? [4, false] : [2, false];
  return { ucl_rounds: Math.max(1, Math.min(TBD_ROUNDS_MAX, tbdMaxRounds(n))), ucl_qualify: q, ucl_playin: playin,
           ko_legs: n >= TBD_TWO_LEGS_FROM ? 2 : 1, final_legs: 1 };
}

function tbdUclError(n, u) {                                // tb_ucl.validate_ucl bilan bir xil
  if (n < 2) return "Kamida 2 ta team kerak";
  if (u.ucl_rounds < 1 || u.ucl_rounds > tbdMaxRounds(n)) return `Bahslar soni 1–${tbdMaxRounds(n)} bo'lishi kerak`;
  if (u.ucl_playin && tbdPlayinNeed(u.ucl_qualify) > n) return `Pley-off raundi uchun ${tbdPlayinNeed(u.ucl_qualify)} ta team kerak`;
  if (u.ucl_qualify > n) return `Pley-offga ${u.ucl_qualify} ta team chiqishi uchun teamlar yetmaydi`;
  return "";
}

function tbdSplit(n, size) {                                // tb_season.split_divisions
  const chunks = [];
  for (let i = 0; i < n; i += size) chunks.push(Math.min(size, n - i));
  if (chunks.length > 1 && chunks[chunks.length - 1] < Math.min(TBD_DIV_TAIL_MIN, size)) chunks[chunks.length - 2] += chunks.pop();
  return chunks;
}

// ---------- holat (liga bo'yicha; saqlangan reja serverdan) ----------
function tbdState(p) {
  const pl = p.plan || {};
  if (!TB.dplan || TB.dplan.lid !== TB.adminLeagueId || TB.dplan.planRef !== pl) {
    TB.dplan = { lid: TB.adminLeagueId, planRef: pl, fmt: pl.format || "league", size: pl.match_size || p.lineup_min,
                 manual: pl.manual || null, savedKey: null };
    if (pl.saved) TB.dplan.savedKey = tbdKey(TB.dplan);
  }
  return TB.dplan;
}
function tbdKey(st) { return JSON.stringify([st.fmt, st.size, st.manual]); }

function tbdResolve(p, st) {                                // amaldagi parametrlar
  const n = tbdEligible(p, st.size);
  if (st.fmt === "ucl") {
    const man = st.manual && st.manual.ucl_qualify ? st.manual : null;
    const u = man || tbdAutoUcl(n);
    return { n, ucl: u, auto: !man, err: u ? tbdUclError(n, u) : "Kamida 2 ta team kerak" };
  }
  const ds = (st.manual && st.manual.division_size) || p.division_size;
  return { n, ds, auto: !(st.manual && st.manual.division_size), err: n < 2 ? "Kamida 2 ta team kerak" : "" };
}

// ---------- reja kartasi ----------
function tbdStep(ic, title, sub) { return `<div class="tb-plan-step"><i>${ic}</i><span><b>${title}</b>${sub ? `<small>${sub}</small>` : ""}</span></div>`; }
function tbdLegs(k) { return k === 2 ? "2 o'yin (uy + mehmon)" : "1 o'yin"; }

function tbdPlanHtml(p, st, r) {
  if (r.err) return `<div class="tb-plan tb-plan--bad">⚠️ ${escHtml(r.err)}</div>`;
  let steps = "", days = 0;
  if (st.fmt === "ucl") {
    const u = r.ucl, q = u.ucl_qualify;
    const inKo = u.ucl_playin ? tbdPlayinNeed(q) : q;
    steps += tbdStep("1", "Liga bosqichi", `${r.n} team bitta umumiy jadvalda · har team ${u.ucl_rounds} ta bahs (har kuni bittadan), raqiblar tasodifiy`);
    days += u.ucl_rounds;
    if (u.ucl_playin) {
      steps += tbdStep("2", "Pley-off raundi", `1–${q / 2}-o'rinlar to'g'ridan ${TBD_STAGE[q]}ga. ${q / 2 + 1}–${inKo}-o'rinlar juft bo'lib o'ynaydi (${q / 2 + 1}–${inKo}, ${q / 2 + 2}–${inKo - 1} …) · ${tbdLegs(u.ko_legs)}`);
      days += u.ko_legs;
    }
    let no = u.ucl_playin ? 3 : 2;
    for (let s = q; s >= 2; s /= 2) {
      const legs = s === 2 ? u.final_legs : u.ko_legs;
      const sub = (s === q && !u.ucl_playin ? `Top-${q} chiqadi (1-o'rin — ${q}-o'rin bilan) · ` : "") + tbdLegs(legs);
      steps += tbdStep(String(no++), TBD_STAGE[s], sub);
      days += legs;
    }
    const out = r.n - inKo;
    if (out > 0) steps += `<div class="tb-hint">${inKo + 1}–${r.n}-o'rinlar liga bosqichidan keyin to'xtaydi.</div>`;
  } else {
    const divs = tbdSplit(r.n, r.ds);
    divs.forEach((k, i) => { steps += tbdStep(String(i + 1), `${i + 1}-divizion — ${k} team`, `Har kim har kim bilan bir marta · ${tbdMaxRounds(k)} tur`); });
    days = Math.max(...divs.map(tbdMaxRounds));
  }
  return `<div class="tb-plan">
      <div class="tb-plan-h">📋 Mavsum rejasi — ${r.n} team<em>${r.auto ? "avtomatik" : "qo'lda"}</em></div>
      ${steps}
      <div class="tb-plan-total">Jami <b>${days}</b> tur (kun) · tur har kuni 23:30 da almashadi</div>
    </div>`;
}

// ---------- qo'lda sozlash ----------
function tbdManualHtml(p, st, r) {
  const sel = (id, vals, cur, lbl, dis) => `<select id="${id}" class="modal-input pt-select">${vals.map(v =>
    `<option value="${v}"${String(v) === String(cur) ? " selected" : ""}${dis && dis(v) ? " disabled" : ""}>${escHtml(lbl(v))}</option>`).join("")}</select>`;
  let body;
  if (st.fmt === "ucl") {
    const u = r.ucl || tbdAutoUcl(2) || {}, n = r.n;
    const qv = `${u.ucl_playin ? "p" : "t"}${u.ucl_qualify}`;
    const qLbl = v => { const b = +v.slice(1); return v[0] === "p" ? `${TBD_STAGE[b]} + raund (${tbdPlayinNeed(b)} team)` : `Top-${b} → ${TBD_STAGE[b]}`; };
    const qDis = v => { const b = +v.slice(1); return v[0] === "p" ? tbdPlayinNeed(b) > n : b > Math.max(2, n); };
    body = `<div class="tb-adm-line"><span>Har team nechta bahs</span>
        <input id="tbd-rounds" class="modal-input" type="number" min="1" max="${Math.max(1, tbdMaxRounds(n))}" value="${u.ucl_rounds || 1}"></div>
      <div class="tb-adm-line"><span>Pley-offga chiqadi</span>${sel("tbd-q", TBD_Q_OPTIONS, qv, qLbl, qDis)}</div>
      <div class="tb-adm-line"><span>Pley-off bahsi</span>${sel("tbd-kl", [1, 2], u.ko_legs || 1, tbdLegs)}</div>
      <div class="tb-adm-line"><span>Final</span>${sel("tbd-fl", [1, 2], u.final_legs || 1, tbdLegs)}</div>`;
  } else {
    body = `<div class="tb-adm-line"><span>Divizionda nechta team</span>
        <input id="tbd-divsize" class="modal-input" type="number" min="4" max="20" value="${r.ds}"></div>`;
  }
  return `<details class="tb-plan-man"${st.manual ? " open" : ""}><summary>⚙️ Qo'lda o'zgartirish (ixtiyoriy)</summary>
      ${body}
      ${st.manual ? `<button class="tb-mini" data-tbd-act="auto">↺ Avtomatik rejaga qaytish</button>` : ""}
    </details>`;
}

function tbdReadManual(st) {
  const v = id => { const x = document.getElementById(id)?.value; return x === undefined || x === "" ? null : x; };
  if (st.fmt === "ucl") {
    const q = String(v("tbd-q") || "t2");
    return { ucl_rounds: +v("tbd-rounds") || 1, ucl_qualify: +q.slice(1), ucl_playin: q[0] === "p",
             ko_legs: +v("tbd-kl") || 1, final_legs: +v("tbd-fl") || 1 };
  }
  return { division_size: +v("tbd-divsize") || null };
}

// ---------- pastki qism: saqlash / qur'a ----------
function tbdFootHtml(st, r, noDraw) {
  const saved = st.savedKey && st.savedKey === tbdKey(st);
  const status = saved ? `<div class="tb-plan-status tb-plan-status--ok">✅ Reja saqlangan</div>`
    : `<div class="tb-plan-status">${st.savedKey ? "✏️ O'zgarishlar saqlanmagan" : "💡 Rejani ko'rib chiqing va «Saqlash» ni bosing"}</div>`;
  const draw = noDraw ? "" : `<button class="btn btn--primary" data-tbsa="create"${saved && !r.err ? "" : " disabled"}>🎲 Qur'a o'tkazish (yangi mavsum)</button>
      ${saved ? "" : `<div class="tb-hint tb-hint--center">Qur'a — reja saqlangandan keyin</div>`}`;
  return `${status}
    <button class="btn ${saved ? "btn--ghost" : "btn--primary"}" data-tbd-act="save"${r.err || saved ? " disabled" : ""}>💾 Saqlash</button>
    ${draw}`;
}

function tbAdminDrawFormHtml(p, noDraw) {
  const st = tbdState(p), r = tbdResolve(p, st);
  TB.dplanNoDraw = !!noDraw;
  const seg = [["league", "🏆 Liga", "Divizionlar, har kim har kim bilan"], ["ucl", "⭐ UCL", "Liga bosqichi + pley-off"]].map(([k, l, d]) =>
    `<button class="tb-seg-btn${st.fmt === k ? " active" : ""}" data-tbd-fmt="${k}">${l}<small>${d}</small></button>`).join("");
  return `<div class="tb-plan-label">1. Format</div>
    <div class="tb-seg tb-fmt-seg">${seg}</div>
    <div class="tb-plan-label">2. Har bahsda nechta o'yinchi</div>
    <div class="tb-adm-line"><span>N vs N</span>
      <input id="tbd-size" class="modal-input" type="number" min="1" max="30" value="${st.size}"></div>
    <div class="tb-hint" id="tbd-elig">${tbdEligHtml(p, st, r)}</div>
    <div class="tb-plan-label">3. Reja</div>
    <div id="tbd-plan">${tbdPlanHtml(p, st, r)}</div>
    <div id="tbd-man">${tbdManualHtml(p, st, r)}</div>
    <div id="tbd-foot" class="tb-plan-foot">${tbdFootHtml(st, r, noDraw)}</div>`;
}

function tbdEligHtml(p, st, r) {
  return `Asosiy tarkibida kamida ${st.size} kishi bor teamlar qatnashadi: <b>${r.n}</b> ta (tasdiqlangan: ${p.approved}).`;
}

function tbdUpdate(rebuildManual) {
  const p = TB.seasonPreview, st = TB.dplan;
  if (!p || !st) return;
  const r = tbdResolve(p, st);
  // faqat o'zgarganda almashtiriladi: maydondan chiqishdagi «change» «Saqlash» tugmasini bosish paytida almashtirib yubormasin
  const set = (id, html) => { const el = document.getElementById(id); if (el && el.dataset.h !== html) { el.innerHTML = html; el.dataset.h = html; } };
  set("tbd-elig", tbdEligHtml(p, st, r));
  set("tbd-plan", tbdPlanHtml(p, st, r));
  set("tbd-foot", tbdFootHtml(st, r, TB.dplanNoDraw));
  if (rebuildManual) set("tbd-man", tbdManualHtml(p, st, r));
}

function tbdPayloadManual(st) { return st.manual ? { ...st.manual } : null; }

async function tbdSave(btn) {
  const st = TB.dplan;
  btn.disabled = true;
  try {
    const plan = await apiFetch("/tb/admin/league/draw-plan", { method: "POST", body: JSON.stringify({
      league_id: TB.adminLeagueId, format: st.fmt, match_size: st.size, manual: tbdPayloadManual(st) }) });
    st.savedKey = tbdKey(st);
    if (TB.seasonPreview) { TB.seasonPreview.plan = plan; st.planRef = plan; }
    showToast("✅ Reja saqlandi");
  } catch (e) { showToast("❌ " + tbErr(e)); }
  tbdUpdate(false);
}

// Qur'a: saqlangan rejaning amaldagi parametrlari (avtomatik bo'lsa — hozirgi teamlar soniga qarab)
function tbAdminDrawBody() {
  const p = TB.seasonPreview, st = TB.dplan;
  const r = tbdResolve(p, st);
  const body = { format: st.fmt, match_size: st.size };
  if (st.fmt === "ucl") Object.assign(body, r.ucl || {});
  else body.division_size = r.ds;
  return body;
}

document.addEventListener("click", (e) => {
  const t = e.target.closest ? e.target : null;
  if (!t || !t.closest("#tb-root")) return;
  const f = t.closest("[data-tbd-fmt]"), a = t.closest("[data-tbd-act]");
  if (f && TB.dplan && TB.dplan.fmt !== f.dataset.tbdFmt) {
    TB.dplan.fmt = f.dataset.tbdFmt;
    TB.dplan.manual = null;                                  // boshqa format — avtomatik rejadan boshlanadi
    const y = window.scrollY; tbAdminRender(); window.scrollTo(0, y);
  } else if (a && a.dataset.tbdAct === "save") void tbdSave(a);
  else if (a && a.dataset.tbdAct === "auto") { TB.dplan.manual = null; tbdUpdate(true); }
});
function tbdOnEdit(e) {
  const el = e.target;
  if (!TB.dplan || !el.closest || !el.closest("#tb-root .tb-adm-season")) return;
  if (el.id === "tbd-size") {
    const n = parseInt(el.value, 10);
    if (!(n >= 1)) return;
    TB.dplan.size = n;
    tbdUpdate(e.type === "change");                          // qo'lda maydonlar (variantlar) ham yangilansin
  } else if (el.closest("#tbd-man") && el.matches("input, select")) {
    TB.dplan.manual = tbdReadManual(TB.dplan);
    tbdUpdate(e.type === "change");                          // «↺ Avtomatik» tugmasi paydo bo'lsin
  }
}
document.addEventListener("input", tbdOnEdit);
document.addEventListener("toggle", (e) => {                 // «Keyingi mavsum rejasi» qayta chizilganda ochiq qolsin
  if (e.target.classList && e.target.classList.contains("tb-plan-next")) TB.dplanOpen = e.target.open;
}, true);
document.addEventListener("change", tbdOnEdit);
