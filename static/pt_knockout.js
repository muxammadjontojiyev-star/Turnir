// =============================================================
//  pt_knockout.js — SHAXSIY turnir pley-offi (2026-10-02, 5-bosqich)
//  pt_play.js ptPlayBodyHtml chaqiradi (p.phase bo'lsa):
//    semi_ready — tashkilotchiga "Yarim finalni boshlash", boshqalarga kutish izohi
//    semi/final — PLEY-OFF bloki: muddat, o'yin kartalari (natija/chat), tashkilotchi boshqaruvi
//    finished   — chempion banneri + yakuniy o'yinlar
//  Global: PTT, escHtml, apiFetch, showToast, PT, ptMatchCardHtml, ptOwnerControlsHtml,
//          ptPlayAction, ptNameOf.
// =============================================================

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

function ptKnockoutCardsHtml(p) {
  const me = p.me_id;
  return (p.knockout || [])
    .map(m => ptMatchCardHtml(m, p, me === m.player1_id || me === m.player2_id))
    .join("");
}

function ptKnockoutHtml(p) {
  if (p.phase === "semi_ready") {
    const body = p.is_owner
      ? `<div class="pt-hint">${escHtml(PTT("pt_semis_hint"))}</div>
         <button class="btn btn--primary btn--glow" id="pt-semis-btn">${escHtml(PTT("pt_semis_btn"))}</button>`
      : `<div class="pt-note">${escHtml(PTT("pt_semis_wait"))}</div>`;
    return `<div class="card pt-pay">
        <div class="pt-note pt-note--ok">${escHtml(PTT("pt_groups_done"))}</div>${body}</div>`;
  }
  if (p.phase === "finished") {
    return `${ptChampionHtml(p)}
      <div class="section-label pt-label">${escHtml(PTT("pt_ko_title"))}</div>${ptKnockoutCardsHtml(p)}`;
  }
  // semi | final
  const owner = p.is_owner ? ptOwnerControlsHtml(true) : "";
  return `<div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_ko_title"))}</div>
      <div class="pt-hint">${escHtml(PTT("pt_ko_hint"))}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_deadline"))}</span>
        <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>
      ${owner}
    </div>
    ${ptKnockoutCardsHtml(p)}`;
}

function ptStartSemis(tid) {
  if (!window.confirm(PTT("pt_semis_ask"))) return;
  return ptPlayAction(tid, `/pt/${encodeURIComponent(tid)}/semis/start`, null, "pt_semis_started");
}
