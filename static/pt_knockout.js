// =============================================================
//  pt_knockout.js — SHAXSIY turnir pley-offi (5-bosqich; 2026-10-03: setka 4..64)
//  2026-10-03 sahifalar (pt_tabs.js): Asosiy — pt_home.js (chempion: ptChampionHtml),
//  Jadval — ptKnockoutStagesHtml (joriy bosqich ochiq, o'tganlari yig'iq),
//  Admin — ptKnockoutAdminHtml (pley-offni boshlash yoki muddat + tuzatish).
//  Global: PTT, escHtml, PT, ptMatchCardHtml, ptOwnerControlsHtml, ptPlayAction.
// =============================================================

const PT_STAGE_ORDER = ["po", "r64", "r32", "r16", "qf", "semi", "final"];   // po — ChL/YeL pley-off raundi

function ptChampionHtml(p) {
  const c = p.champion;
  if (!c) return "";
  const name = c.username ? "@" + c.username : (c.nickname || "");
  return `<div class="card pt-champion">
      <div class="pt-champion-cup">🏆</div>
      <div class="pt-champion-label">${escHtml(PTT("pt_champion_title"))}</div>
      <div class="pt-champion-name">${escHtml(name)}</div>
      ${c.team_name && typeof ptTeamBadge === "function" ? `<div class="pt-champion-team">${ptTeamBadge(c.team_name)}${escHtml(c.team_name)}</div>` : ""}
    </div>`;
}

// Bosqichlar bo'yicha: oxirgi (joriy) bosqich ochiq, oldingilari yig'iq. Mening o'yinlarim — ajratilgan.
function ptKnockoutStagesHtml(p) {
  const me = p.me_id;
  const byStage = {};
  (p.knockout || []).forEach(m => { (byStage[m.stage] = byStage[m.stage] || []).push(m); });
  const stages = PT_STAGE_ORDER.filter(s => byStage[s]);
  const current = stages[stages.length - 1];
  return stages.slice().reverse().map(s => {
    const title = s === "final" ? PTT("pt_stage_final_h") : PTT(`pt_stage_${s}`);
    const cards = byStage[s].map(m => ptMatchCardHtml(m, p, me === m.player1_id || me === m.player2_id)).join("");
    return `<details class="pt-ko-stage" ${s === current ? "open" : ""}>
        <summary class="section-label pt-label">${escHtml(title)} (${byStage[s].length})</summary>${cards}</details>`;
  }).join("");
}

// Admin (tashkilotchi/admin): pley-offni boshlash yoki muddat + natija tuzatish
function ptKnockoutAdminHtml(p) {
  if (!p.is_manager || p.phase === "finished") return "";
  if (p.phase === "ko_ready") {
    return `<div class="card pt-pay">
        <div class="pt-hint">${escHtml(ptKoReadyHint(p))}</div>
        <button class="btn btn--primary btn--glow" id="pt-semis-btn">${escHtml(PTT("pt_semis_btn"))}</button></div>`;
  }
  return `<div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_ko_title"))}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_deadline"))}</span>
        <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>
      ${ptOwnerControlsHtml(true)}</div>`;
}

// Pley-off boshlanishidan oldingi izoh: ChL/YeL — top-Q va pley-off raundi; guruhli — g'oliblar
function ptKoReadyHint(p) {
  if (!p.single_table) return PTT("pt_semis_hint", { size: p.bracket_size });
  const q = p.direct_count || p.bracket_size / 2;
  return PTT("pt_po_hint", { q, from: q + 1, to: 3 * q, size: p.bracket_size });
}

function ptStartSemis(tid) {
  if (!window.confirm(PTT("pt_semis_ask"))) return;
  return ptPlayAction(tid, `/pt/${encodeURIComponent(tid)}/playoff/start`, null, "pt_semis_started");
}

// Javob o'yini (2-o'yin): 1-o'yin tasdiqlangan bo'lsa — yig'indi (shu o'yin uy egasi nuqtai nazaridan)
function ptAggHtml(m, p) {
  if ((m.leg || 1) !== 2) return "";
  const l1 = (p.knockout || []).find(x => x.stage === m.stage && x.round === m.round && (x.leg || 1) === 1);
  if (!l1 || l1.status !== "confirmed" || l1.score1 == null) return "";
  const prev1 = l1.player1_id === m.player1_id ? l1.score1 : l1.score2, prev2 = l1.player1_id === m.player1_id ? l1.score2 : l1.score1;
  const done = m.status === "confirmed" && m.score1 != null;
  return `<div class="pt-agg">${escHtml(PTT(done ? "pt_aggregate" : "pt_first_leg"))}: <b>${done ? prev1 + m.score1 : prev1} : ${done ? prev2 + m.score2 : prev2}</b></div>`;
}
