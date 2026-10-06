// =============================================================
//  pt_play.js — SHAXSIY turnir o'yinlari (2026-10-02, 4-bosqich)
//  Tashkilotchi: "Turnirni boshlash", tur muddati, "Turni yopish".
//  Ishtirokchi: mening o'yinlarim (natija kiritish / tasdiqlash), guruh jadvallari.
//  pt.js ptRenderDetail chaqiradi. Global: PT, PTT, apiFetch, escHtml, showToast, ptOpenDetail.
// =============================================================

const PT_PLAY_ERR = {
  round_closed: "pt_err_round_closed", already_submitted: "pt_err_already_sub",
  deadline_in_past: "pt_err_deadline_past", deadline_too_far: "pt_err_deadline_far",
  bad_deadline: "pt_err_bad_deadline", not_enough_players: "pt_err_not_enough",
  wrong_status: "pt_err_wrong_status",
};
function ptPlayErr(e) { return PTT(PT_PLAY_ERR[e && e.message] || "pt_err_generic"); }

// Tafsilot sahifasidagi o'rin: recruiting — boshlash tugmasi; running — o'yin bloki
function ptPlayHtml(t) {
  if (t.is_owner && t.status === "recruiting") {
    const can = t.approved_count >= t.min_players;
    return `
      <div class="card pt-pay">
        <div class="pt-hint">${escHtml(PTT("pt_start_hint", { min: t.min_players }))}</div>
        <button class="btn btn--primary btn--glow" id="pt-start-btn" ${can ? "" : "disabled"}>
          ${escHtml(PTT("pt_start_btn"))}</button>
      </div>`;
  }
  if (t.status === "running" || t.status === "finished") {
    return `<div id="pt-play-box"><div class="empty-state">${escHtml(PTT("pt_loading"))}</div></div>`;
  }
  return "";
}

function ptBindPlay(t) {
  document.getElementById("pt-start-btn")?.addEventListener("click", () => void ptStart(t.id));
  if (document.getElementById("pt-play-box")) void ptLoadPlay(t.id);
}

async function ptStart(tid) {
  if (PT.busy || !window.confirm(PTT("pt_start_ask"))) return;
  PT.busy = true;
  try {
    await apiFetch(`/pt/${encodeURIComponent(tid)}/start`, { method: "POST" });
    showToast(PTT("pt_started_toast"));
  } catch (e) {
    showToast(ptPlayErr(e));
  } finally {
    PT.busy = false;
  }
  await ptOpenDetail(tid);
}

async function ptLoadPlay(tid) {
  const box = document.getElementById("pt-play-box");
  try {
    PT.play = await apiFetch(`/pt/${encodeURIComponent(tid)}/play`);
    if (box && document.body.contains(box)) { box.innerHTML = ptPlayBodyHtml(PT.play); ptBindPlayBody(tid); }
  } catch (e) {
    if (box) box.innerHTML = `<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`;
  }
}

function ptNameOf(m, side) {
  const u = m[`p${side}_username`];
  return u ? "@" + u : (m[`p${side}_name`] || "—");
}

function ptMatchCardHtml(m, p, mine) {
  const me = p.me_id;
  const head = `<div class="pt-match-head"><span>${escHtml(PTT("pt_round_short", { r: m.round }))} · ${escHtml(PTT("pt_group", { g: m.group_label }))}</span>
                <span class="pt-muted">#${m.id}</span></div>`;
  const score = m.score1 != null ? `${m.score1} : ${m.score2}` : "— : —";
  const names = `<div class="pt-match-row"><b>${escHtml(ptNameOf(m, 1))}</b><span class="pt-score">${score}</span><b>${escHtml(ptNameOf(m, 2))}</b></div>`;
  let action = "";
  if (mine && m.status === "pending" && m.round === p.current_round && p.status === "running") {
    action = `<div class="pt-res-form">
      <input class="modal-input pt-num" type="number" min="0" max="99" inputmode="numeric" id="pt-s1-${m.id}">
      <span>:</span>
      <input class="modal-input pt-num" type="number" min="0" max="99" inputmode="numeric" id="pt-s2-${m.id}">
      <button class="pt-mini pt-mini--ok" data-pt-submit="${m.id}">${escHtml(PTT("pt_submit"))}</button></div>`;
  } else if (mine && m.status === "awaiting_confirmation") {
    action = m.submitted_by === me
      ? `<div class="pt-muted">${escHtml(PTT("pt_wait_confirm"))}</div>`
      : `<div class="pt-row-actions">
           <button class="pt-mini pt-mini--ok" data-pt-confirm="${m.id}">${escHtml(PTT("pt_confirm"))}</button>
           <button class="pt-mini pt-mini--no" data-pt-rejectres="${m.id}">${escHtml(PTT("pt_reject_res"))}</button></div>`;
  }
  return `<div class="match-item pt-match ${m.status === "confirmed" ? "pt-match--done" : ""}">${head}${names}${action}</div>`;
}

function ptStandingsHtml(standings) {
  return Object.entries(standings || {}).map(([g, rows]) => `
    <div class="card pt-table-card">
      <div class="pt-table-title">${escHtml(PTT("pt_group", { g }))}</div>
      <table class="pt-table"><thead><tr><th>#</th><th></th><th>${escHtml(PTT("pt_col_p"))}</th>
        <th>${escHtml(PTT("pt_col_gd"))}</th><th>${escHtml(PTT("pt_col_pts"))}</th></tr></thead><tbody>
      ${rows.map((r, i) => `<tr><td>${i + 1}</td><td class="pt-table-name">${escHtml(r.username ? "@" + r.username : r.nickname || "")}</td>
        <td>${r.played}</td><td>${r.goal_diff > 0 ? "+" : ""}${r.goal_diff}</td><td><b>${r.points}</b></td></tr>`).join("")}
      </tbody></table></div>`).join("");
}

function ptPlayBodyHtml(p) {
  let head;
  if (p.groups_finished) {
    head = `<div class="pt-note pt-note--ok">${escHtml(PTT("pt_groups_done"))}</div>`;
  } else {
    const owner = p.is_owner ? `
      <input class="modal-input" type="datetime-local" id="pt-deadline-input">
      <div class="pt-hint">${escHtml(PTT("pt_deadline_hint"))}</div>
      <div class="pt-pay-actions">
        <button class="btn btn--ghost" id="pt-close-round">${escHtml(PTT("pt_close_round"))}</button>
        <button class="btn btn--primary" id="pt-deadline-btn">${escHtml(PTT("pt_deadline_set"))}</button>
      </div>` : "";
    head = `<div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_round_title", { round: p.current_round, total: p.total_rounds }))}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_deadline"))}</span>
        <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>${owner}</div>`;
  }
  const mine = (p.my_matches || []).map(m => ptMatchCardHtml(m, p, true)).join("");
  const mineIds = new Set((p.my_matches || []).map(m => m.id));
  const others = (p.round_matches || []).filter(m => !mineIds.has(m.id)).map(m => ptMatchCardHtml(m, p, false)).join("");
  return `${head}
    ${mine ? `<div class="section-label pt-label">${escHtml(PTT("pt_my_matches"))}</div>${mine}` : ""}
    <div class="section-label pt-label">${escHtml(PTT("pt_groups_title"))}</div>${ptStandingsHtml(p.standings)}
    ${others ? `<div class="section-label pt-label">${escHtml(PTT("pt_round_matches"))}</div>${others}` : ""}`;
}

function ptBindPlayBody(tid) {
  const q = (sel, fn) => document.querySelectorAll(`#pt-play-box ${sel}`).forEach(fn);
  q("[data-pt-submit]", b => b.addEventListener("click", () => void ptSubmitResult(tid, b.dataset.ptSubmit)));
  q("[data-pt-confirm]", b => b.addEventListener("click", () => void ptConfirmResult(tid, b.dataset.ptConfirm, true)));
  q("[data-pt-rejectres]", b => b.addEventListener("click", () => void ptConfirmResult(tid, b.dataset.ptRejectres, false)));
  document.getElementById("pt-deadline-btn")?.addEventListener("click", () => void ptSetDeadline(tid));
  document.getElementById("pt-close-round")?.addEventListener("click", () => void ptCloseRound(tid));
}

async function ptPlayAction(tid, path, body, okKey) {
  if (PT.busy) return;
  PT.busy = true;
  try {
    await apiFetch(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
    if (okKey) showToast(PTT(okKey));
  } catch (e) {
    showToast(ptPlayErr(e));
  } finally {
    PT.busy = false;
  }
  await ptLoadPlay(tid);
}

function ptSubmitResult(tid, mid) {
  const s1 = document.getElementById(`pt-s1-${mid}`)?.value;
  const s2 = document.getElementById(`pt-s2-${mid}`)?.value;
  if (s1 === "" || s2 === "" || s1 == null || s2 == null) return;
  return ptPlayAction(tid, `/pt/match/${encodeURIComponent(mid)}/result`,
    { score1: Number(s1), score2: Number(s2) }, "pt_result_sent");
}

function ptConfirmResult(tid, mid, accept) {
  return ptPlayAction(tid, `/pt/match/${encodeURIComponent(mid)}/confirm`, { accept },
    accept ? "pt_result_confirmed" : "pt_result_rejected");
}

function ptSetDeadline(tid) {
  const v = document.getElementById("pt-deadline-input")?.value || "";
  return ptPlayAction(tid, `/pt/${encodeURIComponent(tid)}/deadline`, { deadline: v }, "pt_deadline_saved");
}

function ptCloseRound(tid) {
  if (!window.confirm(PTT("pt_close_ask"))) return;
  return ptPlayAction(tid, `/pt/${encodeURIComponent(tid)}/close-round`, null, "pt_round_closed");
}
