// =============================================================
//  pt_knockout.js — SHAXSIY turnir pley-offi (5-bosqich; 2026-10-03: setka 4..64)
//  pt_play.js ptPlayBodyHtml chaqiradi (p.phase bo'lsa):
//    ko_ready    — tashkilotchiga "Pley-offni boshlash" (setka hajmi bilan), boshqalarga kutish izohi
//    r64..final  — PLEY-OFF bloki: muddat, tashkilotchi boshqaruvi, bosqichlar
//                  (joriy bosqich ochiq, o'tganlari yig'iq)
//    finished    — chempion banneri + barcha bosqichlar (final ochiq)
//  Global: PTT, escHtml, PT, ptMatchCardHtml, ptOwnerControlsHtml, ptPlayAction.
// =============================================================

const PT_STAGE_ORDER = ["r64", "r32", "r16", "qf", "semi", "final"];

function ptChampionHtml(p) {
  const c = p.champion;
  if (!c) return "";
  const name = c.username ? "@" + c.username : (c.nickname || "");
  return `<div class="card pt-champion">
      <div class="pt-champion-cup">🏆</div>
      <div class="pt-champion-label">${escHtml(PTT("pt_champion_title"))}</div>
      <div class="pt-champion-name">${escHtml(name)}</div>
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

function ptKnockoutHtml(p) {
  if (p.phase === "ko_ready") {
    const body = p.is_owner
      ? `<div class="pt-hint">${escHtml(PTT("pt_semis_hint", { size: p.bracket_size }))}</div>
         <button class="btn btn--primary btn--glow" id="pt-semis-btn">${escHtml(PTT("pt_semis_btn"))}</button>`
      : `<div class="pt-note">${escHtml(PTT("pt_semis_wait"))}</div>`;
    return `<div class="card pt-pay">
        <div class="pt-note pt-note--ok">${escHtml(PTT("pt_groups_done"))}</div>${body}</div>`;
  }
  if (p.phase === "finished") {
    return `${ptChampionHtml(p)}${ptKnockoutStagesHtml(p)}`;
  }
  const owner = p.is_owner ? ptOwnerControlsHtml(true) : "";
  return `<div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_ko_title"))}</div>
      <div class="pt-hint">${escHtml(PTT("pt_ko_hint"))}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_deadline"))}</span>
        <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>
      ${owner}
    </div>
    ${ptKnockoutStagesHtml(p)}`;
}

function ptStartSemis(tid) {
  if (!window.confirm(PTT("pt_semis_ask"))) return;
  return ptPlayAction(tid, `/pt/${encodeURIComponent(tid)}/playoff/start`, null, "pt_semis_started");
}
