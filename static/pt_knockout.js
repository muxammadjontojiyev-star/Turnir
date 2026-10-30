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
  return `${ptKoRebuildHtml(p)}<div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_ko_title"))}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_deadline"))}</span>
        <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>
      ${ptOwnerControlsHtml(true)}</div>`;
}

// Pley-off boshlanishidan oldingi izoh: ChL/YeL — top-Q va pley-off raundi; guruhli — g'oliblar
function ptKoReadyHint(p) {
  if (p.format === "wc") return ptWcHint(p.bracket_size, Object.keys(p.standings || {}).length);
  if (!p.single_table) return PTT("pt_semis_hint", { size: p.bracket_size });
  const q = p.direct_count || p.bracket_size / 2;
  return PTT("pt_po_hint", { q, from: q + 1, to: 3 * q, size: p.bracket_size });
}

// 2026-10-30: JCh — g'oliblar + 2-o'rinlar + eng yaxshi 3-o'rinlar (setka < 2·G bo'lsa — klassik izoh)
function ptWcHint(size, g) {
  if (size < 2 * g) return PTT("pt_semis_hint", { size });
  return size > 2 * g ? PTT("pt_wc_hint", { size, thirds: size - 2 * g }) : PTT("pt_wc_hint2", { size });
}

// 2026-10-30: eski qoida bilan tuzilgan JCh setkasi (natijasiz) — qayta tuzish (server: ko_rebuildable)
function ptKoRebuildHtml(p) {
  if (!p.ko_rebuildable) return "";
  return `<div class="card pt-pay pt-ko-rebuild" style="margin-bottom:12px">
      <div class="pt-hint">⚠️ ${escHtml(PTT("pt_ko_rebuild_note", { size: p.bracket_size }))}</div>
      <div class="pt-hint">${escHtml(ptWcHint(p.bracket_size, Object.keys(p.standings || {}).length))}</div>
      <button class="btn btn--primary" data-pt-ko-rebuild="1">${escHtml(PTT("pt_ko_rebuild_btn"))}</button></div>`;
}

function ptKoRebuild(tid) {
  if (!window.confirm(PTT("pt_ko_rebuild_ask"))) return;
  return ptPlayAction(tid, `/pt/${encodeURIComponent(tid)}/playoff/rebuild`, null, "pt_ko_rebuilt");
}

if (typeof PT_PLAY_ERR !== "undefined") Object.assign(PT_PLAY_ERR, {
  ko_has_results: "pt_err_ko_results", nothing_to_change: "pt_err_ko_same",
  bad_format: "pt_err_ko_rebuild", not_started: "pt_err_ko_rebuild", not_running: "pt_err_ko_rebuild",
});

document.addEventListener("click", (e) => {
  const b = e.target.closest ? e.target.closest("[data-pt-ko-rebuild]") : null;
  if (b && PT.detailId != null) void ptKoRebuild(PT.detailId);
});

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
