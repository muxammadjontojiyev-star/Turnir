// =============================================================
//  tb_form.js — "TEAMLAR JANGI": O'YINCHILAR FORMASI va 10 BALLIK BAHO (2026-11-07, server: tb_form.py)
//  * tbFormMount(teamId) — #tb-form-box ga team a'zolari formasi (oxirgi 5 o'yin bahosi, o'rtacha, MVP soni).
//  * tbRatingHtml(r) — rangli baho belgisi (Jadval → bahs juftliklari ham ishlatadi).
//  Global: TB, apiFetch, escHtml, tbI18nApply.
// =============================================================

const TBF = { cache: {}, at: {} };
const TBF_TTL_MS = 60 * 1000;
const TBF_LEVELS = [[8, "top"], [6.5, "good"], [5, "mid"], [0, "low"]];   // baho → rang darajasi

function tbRatingCls(r) { return (TBF_LEVELS.find(([min]) => r >= min) || TBF_LEVELS[3])[1]; }

function tbRatingHtml(r, big) {
  if (r == null) return "";
  return `<i class="tb-rt tb-rt--${tbRatingCls(r)}${big ? " tb-rt--big" : ""}">${Number(r).toFixed(1)}</i>`;
}

function tbFormBoxHtml() { return `<div id="tb-form-box"><div class="tb-hint tb-hint--center">Yuklanmoqda…</div></div>`; }

function tbFormHtml(d) {
  const rows = (d.members || []);
  const legend = `<div class="tb-form-legend">${"Har bir 1v1 o'yinga 10 ballik baho: g'alaba, urgan va o'tkazgan gollar, quruq o'yin hisobga olinadi. 4+ gol urib, gol o'tkazmagan —"} <b>10</b>. Forma — oxirgi ${Number(d.form_last) || 5} o'yin o'rtachasi.</div>`;
  if (!rows.some(m => m.games)) return legend + `<div class="card tb-hint tb-hint--center">Hali baholangan o'yin yo'q — birinchi tur o'ynalgach forma chiqadi</div>`;
  return legend + `<div class="card tb-form-list">${rows.map((m, i) => `
    <div class="tb-form-row">
      <span class="tb-form-n">${m.games ? i + 1 : "–"}</span>
      <span class="tb-form-info"><b>${escHtml(m.name)}</b>
        <span class="tb-form-last">${(m.last || []).map(r => tbRatingHtml(r)).join("") || `<small>o'yin yo'q</small>`}</span>
        ${m.games ? `<small>${m.games} o'yin · ${m.w}G ${m.d}D ${m.l}M · ${m.gf}:${m.ga}${m.mvp ? ` · ⭐ MVP ×${m.mvp}` : ""}</small>` : ""}</span>
      <span class="tb-form-score">${m.form != null ? tbRatingHtml(m.form, true) : "<i class='tb-rt tb-rt--none'>—</i>"}</span>
    </div>`).join("")}</div>`;
}

async function tbFormMount(teamId) {
  const box = document.getElementById("tb-form-box");
  if (!box || !teamId) return;
  if (!TBF.cache[teamId] || Date.now() - (TBF.at[teamId] || 0) > TBF_TTL_MS) {
    try { TBF.cache[teamId] = await apiFetch(`/tb/teams/${Number(teamId)}/form`); TBF.at[teamId] = Date.now(); }
    catch (_) { TBF.cache[teamId] = { members: [] }; }
  }
  const el = document.getElementById("tb-form-box");
  if (!el) return;
  el.innerHTML = tbFormHtml(TBF.cache[teamId]);
  tbI18nApply(el);
}
