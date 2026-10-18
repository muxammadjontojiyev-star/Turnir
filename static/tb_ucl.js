// =============================================================
//  tb_ucl.js — "TEAMLAR JANGI": UCL pley-off to'ri (Jadval sahifasi pastida, 2026-10-18)
//  Bosqichlar (1/8, chorak, yarim, final): juftliklar, har o'yin natijasi (1v1 g'alabalar),
//  yig'indi, g'olib. Teng juftlikda liga admini g'olibni belgilaydi (⚖️ tugmalar).
//  Backend: GET /tb/season/ko, POST /tb/admin/ko/decide (tb_ucl_view.py).
//  Global: TB, TBS, apiFetch, escHtml, tbLogo, tbToast, tbConfirm, tbErr, tbCanManageCur, tbCurLeague, tbsRenderTable.
// =============================================================

const TB_UCL_STAGE = { 16: "1/8 final", 8: "Chorak final", 4: "Yarim final", 2: "Final" };

function tbUclTeam(t, win) {
  if (!t) return `<span class="tb-ko-team">?</span>`;
  return `<span class="tb-ko-team${win ? " is-win" : ""}">${tbLogo("team", t.id, t.logo_ver, t.emoji, "tb-logo--sm")} ${escHtml(t.name)}</span>`;
}

function tbUclTieHtml(t, manage) {
  const done = !!t.winner_team_id;
  const legs = t.legs.map((l, i) => `<span class="tb-ko-leg">${i + 1}-o'yin: ${l.status === "finished" ? `${l.a}:${l.b}` : "—"}</span>`).join("");
  const decide = t.needs_admin && manage && t.a && t.b
    ? `<div class="tb-ko-decide"><div class="tb-warn">⚖️ Teng: g'alabalar ${t.agg_a}:${t.agg_b}, gollar ${t.goals_a}:${t.goals_b}. Kim o'tadi?</div>
        <div class="tb-ko-decide-acts">
          <button class="tb-mini tb-mini--ok" data-tbk-win="${t.a.id}" data-tie="${t.id}" data-name="${escHtml(t.a.name)}">${escHtml(t.a.name)}</button>
          <button class="tb-mini tb-mini--ok" data-tbk-win="${t.b.id}" data-tie="${t.id}" data-name="${escHtml(t.b.name)}">${escHtml(t.b.name)}</button>
        </div></div>`
    : (t.needs_admin ? `<div class="tb-hint tb-hint--center">⚖️ Teng — liga admini qarori kutilmoqda</div>` : "");
  return `<div class="card tb-ko-tie${done ? " is-done" : ""}">
      <div class="tb-ko-row">${tbUclTeam(t.a, done && t.winner_team_id === (t.a && t.a.id))}<b class="tb-ko-agg">${t.agg_a}</b></div>
      <div class="tb-ko-row">${tbUclTeam(t.b, done && t.winner_team_id === (t.b && t.b.id))}<b class="tb-ko-agg">${t.agg_b}</b></div>
      <div class="tb-ko-legs">${legs}</div>
      ${decide}
    </div>`;
}

function tbUclBracketHtml(ko) {
  const stages = (ko && ko.stages) || [];
  if (!stages.length) return "";
  const manage = typeof tbCanManageCur === "function" && tbCanManageCur();
  const final = stages.find(s => s.size === 2);
  const champ = final && final.ties[0] && final.ties[0].winner_team_id
    ? [final.ties[0].a, final.ties[0].b].find(x => x && x.id === final.ties[0].winner_team_id) : null;
  const body = stages.map(st => `
      <div class="tb-ko-stage-title">${escHtml(TB_UCL_STAGE[st.size] || `1/${st.size / 2} final`)}</div>
      ${st.ties.length ? st.ties.map(t => tbUclTieHtml(t, manage)).join("")
        : `<div class="tb-hint tb-hint--center">Juftliklar oldingi bosqichdan keyin aniqlanadi</div>`}`).join("");
  return `<div class="section-label">PLEY-OFF</div>
    ${champ ? `<div class="card tb-ko-champ">🏆 ${tbLogo("team", champ.id, champ.logo_ver, champ.emoji, "tb-logo--lg")} <b>${escHtml(champ.name)}</b></div>` : ""}
    <div class="tb-hint">Raqam — 1v1 g'alabalar yig'indisi. Teng bo'lsa: gol farqi → liga admini qarori.</div>
    ${body}`;
}

document.addEventListener("click", async (e) => {
  const b = e.target.closest ? e.target.closest("#tb-root [data-tbk-win]") : null;
  if (!b || !tbConfirm(`«${b.dataset.name}» keyingi bosqichga o'tsinmi?`)) return;
  b.disabled = true;
  try {
    const r = await apiFetch("/tb/admin/ko/decide", { method: "POST", body: JSON.stringify({
      league_id: tbCurLeague(), tie_id: +b.dataset.tie, winner_team_id: +b.dataset.tbkWin }) });
    tbToast(r.opened_round ? `✅ Qaror saqlandi — ${r.opened_round}-tur ochildi` : "✅ Qaror saqlandi");
    await tbsRenderTable();
  } catch (err) {
    tbToast("❌ " + tbErr(err));
    b.disabled = false;
  }
});
