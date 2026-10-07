// =============================================================
//  pt_create.js — SHAXSIY turnir yaratish formasi (2026-10-07; pt.js'dan ajratildi — qoida #21)
//  1) Format: Liga | Chempionlar ligasi | Yevropa ligasi | Jahon chempionati | Erkin.
//  2) Liga formatida: liga (LaLiga, Premier Liga, ...) — ishtirokchilar soni = ligadagi klublar
//     soni (qat'iy), doira: 1 yoki 2 (uy+mehmon). Boshqalarida sig'im formatga qarab.
//  3) Nom, to'lov turi (obuna | bir martalik), narx (sig'im pog'onasi). Klubni har kim o'zi tanlaydi.
//  Global: PT, PTT, escHtml, apiFetch, showToast, ptRender, ptOpenDetail, ptSizeSelectHtml,
//  ptFmtRule, ptFormatSummary, ptFormatCardsHtml, ptLeagueCardsHtml, ptLegsHtml, ptCreatePriceText,
//  ptPayModeHtml, ptSizeAllowed, ptDefaultMode.
// =============================================================

function ptCreateState(keep) {
  const leagues = Object.keys((PT.config && PT.config.leagues) || LEAGUE_CLUBS);
  if (keep && keep.fmt) PT.createFmt = keep.fmt;
  if (keep && keep.league) {                              // liga tugmasi — tanlash/olib tashlash (kamida 1 ta)
    const cur = ptLeagues(PT.createLeagues || []);
    PT.createLeagues = cur.includes(keep.league) ? (cur.length > 1 ? cur.filter(x => x !== keep.league) : cur) : [...cur, keep.league];
  }
  if (keep && keep.legs) PT.createLegs = keep.legs;
  PT.createFmt = PT.createFmt || "league";
  PT.createLeagues = ptLeagues(PT.createLeagues || []).filter(x => leagues.includes(x));
  if (!PT.createLeagues.length) PT.createLeagues = [leagues[0]];
  PT.createLegs = ptLegsFormat(PT.createFmt) ? (PT.createLegs || 1) : 1;
  return { fmt: PT.createFmt, league: PT.createLeagues.join("|"), legs: PT.createLegs };
}

// Sig'im: format qoidasi + to'lov turida ochiq pog'onalar; tanlangan yopiq bo'lsa — eng yaqin ochig'i
function ptPickSize(rule, want, allow) {
  const ok = n => n >= rule.min && n <= rule.max && (n - rule.min) % rule.step === 0 && allow(n);
  if (ok(want)) return want;
  for (let n = Math.min(want, rule.max); n >= rule.min; n--) if (ok(n)) return n;
  for (let n = rule.min; n <= rule.max; n++) if (ok(n)) return n;
  return rule.min;
}

// Narx: liga — eng katta liga sig'imi narxi + har qo'shimcha liga uchun extra_league_uzs (server bilan bir xil);
// obunada qo'shimcha to'lov yo'q
function ptCreatePrice(st, size, mode) {
  if (typeof ptCreatePriceText !== "function") return { ok: (PT.config || {}).price_set, html: "" };
  if (st.fmt !== "league" || mode === "subscription") return ptCreatePriceText(size, mode);
  const lgs = ptLeagues(st.league);
  const base = ptCreatePriceText(Math.max(...lgs.map(ptLeagueSize)), mode);
  if (!base.ok || lgs.length < 2) return base;
  const extra = (((PT.config || {}).pricing || {}).extra_league_uzs || 0) * (lgs.length - 1);
  const total = (typeof ptTierPrice === "function" && ptHasTiers() ? ptTierPrice(Math.max(...lgs.map(ptLeagueSize)))
    : ((PT.config || {}).price_uzs || 0)) + extra;
  return { ok: true, html: `<div class="pt-price">${escHtml(PTT("pt_price"))}: <b>${escHtml(ptFormatPrice(total))} so'm</b>
    <span class="pt-muted">(${escHtml(PTT("pt_price_extra", { n: lgs.length - 1, price: ptFormatPrice(extra) }))})</span></div>` };
}

function ptRenderCreate(keep) {
  PT.view = "create";
  const c = PT.config || {};
  const st = ptCreateState(keep);
  const mode = (keep && keep.mode) || PT.createMode || (typeof ptDefaultMode === "function" ? ptDefaultMode() : "one_time");
  PT.createMode = mode;
  const allow = n => st.fmt === "league" || (typeof ptSizeAllowed === "function" ? ptSizeAllowed(n, mode) : true);
  const rule = ptFmtRule(st.fmt, st.league);
  const size = ptPickSize(rule, Number((keep && keep.size) || c.default_players || 8), allow);
  const fixed = rule.min === rule.max;
  const price = ptCreatePrice(st, size, mode);
  const step = (n, key) => `<div class="pt-step"><span class="pt-step-n">${n}</span>${escHtml(PTT(key))}</div>`;
  const extra = ((c.pricing || {}).extra_league_uzs) || 0;
  const league = st.fmt === "league" ? `
      ${step(2, "pt_step_league")}
      <div class="pt-hint">${escHtml(PTT("pt_leagues_hint", { price: ptFormatPrice(extra) }))}</div>${ptLeagueCardsHtml(st.league)}` : "";
  const legs = ptLegsFormat(st.fmt)
    ? `<div class="pt-field-label">${escHtml(PTT(st.fmt === "classic" ? "pt_legs_label_classic" : "pt_legs_label"))}</div>${ptLegsHtml(st.legs)}` : "";
  const sizeHtml = fixed
    ? `<div class="pt-fixed-size">${escHtml(PTT("pt_size_fixed", { n: size }))}</div><input type="hidden" id="pt-size" value="${size}">`
    : ptSizeSelectHtml("pt-size", size, 0, allow, rule);
  ptRender(`
    <div class="card pt-form">
      <div class="section-label pt-label">${escHtml(PTT("pt_create_title"))}</div>
      ${step(1, "pt_step_format")}${ptFormatCardsHtml(st.fmt)}
      ${league}
      ${legs}
      ${step(st.fmt === "league" ? 3 : 2, "pt_step_details")}
      <label class="pt-field-label" for="pt-name">${escHtml(PTT("pt_name_label"))}</label>
      <input class="modal-input" id="pt-name" maxlength="${c.name_max || 40}"
             placeholder="${escHtml(PTT("pt_name_ph"))}" autocomplete="off">
      <label class="pt-field-label" for="pt-size">${escHtml(PTT("pt_size_label"))}</label>
      ${sizeHtml}
      <div class="pt-size-sum" id="pt-size-sum">${escHtml(ptFormatSummary(st.fmt, size, st.legs))}</div>
      ${ptUsesTeams(st.fmt) ? `<div class="pt-hint">${escHtml(PTT("pt_team_hint_" + (st.fmt === "wc" ? "wc" : "club")))}</div>` : ""}
      ${typeof ptPayModeHtml === "function" ? ptPayModeHtml(mode) : ""}
      <div id="pt-price-box">${price.html}</div>
      <button class="btn btn--primary btn--glow" id="pt-create-btn" ${price.ok ? "" : "disabled"}>
        ${escHtml(PTT("pt_create_btn"))}</button>
    </div>`);
  if (keep && keep.name) document.getElementById("pt-name").value = keep.name;
  const snapshot = () => ({ name: document.getElementById("pt-name").value,
                            size: Number(document.getElementById("pt-size").value) });
  document.getElementById("pt-create-btn").addEventListener("click", ptCreateSubmit);
  document.getElementById("pt-size").addEventListener("change", () => {
    const n = Number(document.getElementById("pt-size").value);
    const p = ptCreatePrice(ptCreateState(), n, PT.createMode);
    document.getElementById("pt-size-sum").textContent = ptFormatSummary(PT.createFmt, n, PT.createLegs);
    document.getElementById("pt-price-box").innerHTML = p.html;
    document.getElementById("pt-create-btn").disabled = !p.ok;
  });
  const q = sel => document.querySelectorAll(`#pt-root ${sel}`);
  q("input[name='pt-mode']").forEach(r => r.addEventListener("change", () => ptRenderCreate({ ...snapshot(), mode: r.value })));
  q("[data-pt-fmt]").forEach(b => b.addEventListener("click", () => ptRenderCreate({ ...snapshot(), fmt: b.dataset.ptFmt })));
  q("[data-pt-league]").forEach(b => b.addEventListener("click", () => ptRenderCreate({ ...snapshot(), league: b.dataset.ptLeague })));
  q("[data-pt-legs]").forEach(b => b.addEventListener("click", () => ptRenderCreate({ ...snapshot(), legs: Number(b.dataset.ptLegs) })));
}

async function ptCreateSubmit() {
  if (PT.busy) return;                       // ikki marta bosish (qoida #38)
  const input = document.getElementById("pt-name");
  const btn = document.getElementById("pt-create-btn");
  const name = (input.value || "").trim();
  PT.busy = true;
  btn.disabled = true;
  btn.textContent = PTT("pt_creating");
  try {
    const max_players = Number(document.getElementById("pt-size")?.value || 8);
    const body = { name, max_players, pay_mode: PT.createMode || "one_time", format: PT.createFmt || "classic",
                   leagues: PT.createFmt === "league" ? PT.createLeagues : null, legs: PT.createLegs || 1 };
    const r = await apiFetch("/pt/create", { method: "POST", body: JSON.stringify(body) });
    showToast(PTT("pt_created"));
    await ptOpenDetail(r.id);
  } catch (e) {
    const map = { name_too_short: "pt_err_name_short", name_too_long: "pt_err_name_long", bad_size: "pt_err_bad_size",
                  no_subscription: "pt_err_no_sub", sub_limit: "pt_err_sub_limit", bad_format: "pt_err_generic",
                  too_many_unpaid: "pt_err_too_many", price_not_set: "pt_price_not_set" };
    const code = (e && (e.detail || e.message)) || "";
    showToast(PTT(map[code] || "pt_err_generic"));
    btn.disabled = false;
    btn.textContent = PTT("pt_create_btn");
  } finally {
    PT.busy = false;
  }
}
