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
  wrong_status: "pt_err_wrong_status", not_owner: "pt_err_not_owner", match_not_found: "pt_err_match_404",
  draw_not_allowed: "pt_err_draw", not_ready: "pt_err_not_ready", next_stage_played: "pt_err_next_played",
};

// O'yin bosqichi nomi (guruh turi yoki pley-off bosqichi) — karta va tuzatish oynasi uchun umumiy
function ptStageLabel(m) {
  if (m.stage === "final") return PTT("pt_stage_final");
  if (m.stage === "semi") return PTT("pt_stage_semi_n", { n: m.round });
  if (m.stage && m.stage !== "group") return PTT(`pt_stage_${m.stage}_n`, { n: m.round });
  return `${PTT("pt_round_short", { r: m.round })} · ${PTT("pt_group", { g: m.group_label })}`;
}
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
    const [play, unread] = await Promise.all([
      apiFetch(`/pt/${encodeURIComponent(tid)}/play`),
      apiFetch("/pt/matches/unread").catch(() => ({ by_match: {} })),   // rozetka ixtiyoriy
    ]);
    PT.play = play;
    PT.unread = unread.by_match || {};
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
  const head = `<div class="pt-match-head"><span>${escHtml(ptStageLabel(m))}</span>
                <span class="pt-muted">#${m.id}</span></div>`;
  const score = m.score1 != null ? `${m.score1} : ${m.score2}` : "— : —";
  const names = `<div class="pt-match-row"><b>${escHtml(ptNameOf(m, 1))}</b><span class="pt-score">${score}</span><b>${escHtml(ptNameOf(m, 2))}</b></div>`;
  let action = "";
  const open = m.stage === "group" ? m.round === p.current_round : true;   // pley-off: bosqich ochiq
  if (mine && m.status === "pending" && open && p.status === "running") {
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
  let tools = "";
  if (mine && m.player1_id && m.player2_id && (m.stage !== "group" || m.round <= p.current_round)) {
    const opp = m.player1_id === me ? ptNameOf(m, 2) : ptNameOf(m, 1);
    const n = (PT.unread || {})[m.id] || 0;
    tools = `<div class="pt-match-tools">
      <button class="pt-mini pt-mini--chat" data-pt-chat="${m.id}" data-pt-opp="${escHtml(opp)}">${escHtml(PTT("pt_chat"))}${n ? ` <span class="pt-badge">${n}</span>` : ""}</button>
      ${typeof roomCodeBtnHtml === "function" ? roomCodeBtnHtml(m.id, "pt") : ""}</div>`;
  }
  return `<div class="match-item pt-match ${m.status === "confirmed" ? "pt-match--done" : ""}">${head}${names}${action}${tools}</div>`;
}

// Guruh jadvallari: 26 guruhgacha bo'lishi mumkin — MENING guruhim birinchi va ochiq,
// qolganlari yig'iq (<details>), 4 tadan kam bo'lsa hammasi ochiq.
function ptStandingsHtml(standings, meId) {
  const entries = Object.entries(standings || {});
  const mine = entries.find(([, rows]) => rows.some(r => r.user_id === meId));
  const ordered = mine ? [mine, ...entries.filter(e => e !== mine)] : entries;
  const openAll = entries.length <= 3;
  return ordered.map(([g, rows]) => {
    const isMine = mine && g === mine[0];
    return `<details class="card pt-table-card" ${openAll || isMine ? "open" : ""}>
      <summary class="pt-table-title">${escHtml(PTT("pt_group", { g }))}${isMine ? ` · <span class="pt-muted">${escHtml(PTT("pt_my_group"))}</span>` : ""}</summary>
      <table class="pt-table"><thead><tr><th>#</th><th></th><th>${escHtml(PTT("pt_col_p"))}</th>
        <th>${escHtml(PTT("pt_col_gd"))}</th><th>${escHtml(PTT("pt_col_pts"))}</th></tr></thead><tbody>
      ${rows.map((r, i) => `<tr><td>${i + 1}</td><td class="pt-table-name">${escHtml(r.username ? "@" + r.username : r.nickname || "")}</td>
        <td>${r.played}</td><td>${r.goal_diff > 0 ? "+" : ""}${r.goal_diff}</td><td><b>${r.points}</b></td></tr>`).join("")}
      </tbody></table></details>`;
  }).join("");
}

// Tashkilotchi boshqaruvi: muddat (+ guruhda "Turni yopish") va natijani tuzatish.
// Guruh va pley-off uchun umumiy (qoida #26).
function ptOwnerControlsHtml(knockout) {
  return `
      <input class="modal-input" type="datetime-local" id="pt-deadline-input">
      <div class="pt-hint">${escHtml(PTT(knockout ? "pt_ko_deadline_hint" : "pt_deadline_hint"))}</div>
      <div class="pt-pay-actions${knockout ? " pt-pay-actions--one" : ""}">
        ${knockout ? "" : `<button class="btn btn--ghost" id="pt-close-round">${escHtml(PTT("pt_close_round"))}</button>`}
        <button class="btn btn--primary" id="pt-deadline-btn">${escHtml(PTT("pt_deadline_set"))}</button>
      </div>
      <div class="section-label pt-label">${escHtml(PTT("pt_fix_title"))}</div>
      <div class="pt-hint">${escHtml(PTT("pt_fix_hint"))}</div>
      <div class="pt-fix-row">
        <input class="modal-input" type="number" min="1" inputmode="numeric" id="pt-fix-id" placeholder="${escHtml(PTT("pt_fix_id_ph"))}">
        <button class="btn btn--ghost" id="pt-fix-load">${escHtml(PTT("pt_fix_load"))}</button>
      </div>
      <div id="pt-fix-box"></div>`;
}

function ptPlayBodyHtml(p) {
  let head;
  if (p.phase && typeof ptKnockoutHtml === "function") {
    head = ptKnockoutHtml(p);                               // pt_knockout.js (5-bosqich)
  } else if (p.groups_finished) {
    head = `<div class="pt-note pt-note--ok">${escHtml(PTT("pt_groups_done"))}</div>`;
  } else {
    const owner = p.is_owner ? ptOwnerControlsHtml(false) : "";
    head = `<div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_round_title", { round: p.current_round, total: p.total_rounds }))}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_deadline"))}</span>
        <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>${owner}</div>`;
  }
  // Pley-off o'yinlari yuqoridagi PLEY-OFF blokida — bu yerda faqat guruh o'yinlari
  const mine = (p.my_matches || []).filter(m => m.stage === "group").map(m => ptMatchCardHtml(m, p, true)).join("");
  const mineIds = new Set((p.my_matches || []).map(m => m.id));
  const others = (p.round_matches || []).filter(m => !mineIds.has(m.id)).map(m => ptMatchCardHtml(m, p, false)).join("");
  return `${head}
    ${mine ? `<div class="section-label pt-label">${escHtml(PTT("pt_my_matches"))}</div>${mine}` : ""}
    <div class="section-label pt-label">${escHtml(PTT("pt_groups_title"))}</div>${ptStandingsHtml(p.standings, p.me_id)}
    ${others ? `<div class="section-label pt-label">${escHtml(PTT("pt_round_matches"))}</div>${others}` : ""}`;
}

function ptBindPlayBody(tid) {
  const q = (sel, fn) => document.querySelectorAll(`#pt-play-box ${sel}`).forEach(fn);
  q("[data-pt-submit]", b => b.addEventListener("click", () => void ptSubmitResult(tid, b.dataset.ptSubmit)));
  q("[data-pt-confirm]", b => b.addEventListener("click", () => void ptConfirmResult(tid, b.dataset.ptConfirm, true)));
  q("[data-pt-rejectres]", b => b.addEventListener("click", () => void ptConfirmResult(tid, b.dataset.ptRejectres, false)));
  document.getElementById("pt-deadline-btn")?.addEventListener("click", () => void ptSetDeadline(tid));
  document.getElementById("pt-close-round")?.addEventListener("click", () => void ptCloseRound(tid));
  q("[data-pt-chat]", b => b.addEventListener("click", () => {
    b.querySelector(".pt-badge")?.remove();                 // ochilgach o'qildi deb hisoblanadi
    openWebChat(Number(b.dataset.ptChat), b.dataset.ptOpp, "/pt/matches");
  }));
  document.getElementById("pt-fix-load")?.addEventListener("click", () => void ptFixLoad(tid));
  document.getElementById("pt-semis-btn")?.addEventListener("click", () => void ptStartSemis(tid));
}

// ---------------- Tashkilotchi: natijani tuzatish (Match ID bo'yicha) ----------------

async function ptFixLoad(tid) {
  const id = Number(document.getElementById("pt-fix-id")?.value || 0);
  const box = document.getElementById("pt-fix-box");
  if (!id || !box) return;
  try {
    const m = await apiFetch(`/pt/owner/match/${encodeURIComponent(id)}`);
    box.innerHTML = `
      <div class="match-item pt-match">
        <div class="pt-match-head"><span>${escHtml(ptStageLabel(m))}</span><span class="pt-muted">#${m.id}</span></div>
        <div class="pt-match-row"><b>${escHtml(m.player1 || "—")}</b><span class="pt-score">${m.score1 != null ? `${m.score1} : ${m.score2}` : "— : —"}</span><b>${escHtml(m.player2 || "—")}</b></div>
        <div class="pt-res-form">
          <input class="modal-input pt-num" type="number" min="0" max="99" inputmode="numeric" id="pt-fix-s1" value="${m.score1 ?? ""}">
          <span>:</span>
          <input class="modal-input pt-num" type="number" min="0" max="99" inputmode="numeric" id="pt-fix-s2" value="${m.score2 ?? ""}">
          <button class="pt-mini pt-mini--ok" id="pt-fix-save">${escHtml(PTT("pt_fix_save"))}</button>
        </div>
        ${m.can_cancel && m.status !== "pending" ? `<button class="pt-mini pt-mini--no" id="pt-fix-cancel">${escHtml(PTT("pt_fix_cancel"))}</button>` : ""}
      </div>`;
    document.getElementById("pt-fix-save").addEventListener("click", () => {
      const s1 = document.getElementById("pt-fix-s1").value, s2 = document.getElementById("pt-fix-s2").value;
      if (s1 === "" || s2 === "") return;
      void ptPlayAction(tid, `/pt/owner/match/${id}/set`, { score1: Number(s1), score2: Number(s2) }, "pt_fix_saved");
    });
    document.getElementById("pt-fix-cancel")?.addEventListener("click", () =>
      void ptPlayAction(tid, `/pt/owner/match/${id}/cancel`, null, "pt_fix_cancelled"));
  } catch (e) {
    box.innerHTML = "";
    showToast(ptPlayErr(e));
  }
}

async function ptPlayAction(tid, path, body, okKey) {
  if (PT.busy) return;
  PT.busy = true;
  let finished = false;
  try {
    const r = await apiFetch(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
    finished = !!(r && r.event === "finished");       // final hal bo'ldi — sarlavha holati ham o'zgaradi
    if (okKey) showToast(PTT(okKey));
  } catch (e) {
    showToast(ptPlayErr(e));
  } finally {
    PT.busy = false;
  }
  if (finished) await ptOpenDetail(tid);
  else await ptLoadPlay(tid);
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
