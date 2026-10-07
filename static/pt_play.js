// =============================================================
//  pt_play.js — SHAXSIY turnir o'yinlari (2026-10-02, 4-bosqich)
//  Tashkilotchi: boshlash, tur muddati, "Turni yopish". Ishtirokchi: natija / tasdiq, jadvallar.
//  2026-10-03: bo'laklar sahifalarga taqsimlanadi (pt_tabs.js; 2026-10-07 Asosiy — pt_home.js),
//  Jadval — ptStandingsHtml + ptRoundOthersHtml, O'yinlarim — ptMyMatchesHtml, Admin — ptPlayHtml
//  (boshlash) + ptAdminPlayHtml. Global: PT, PTT, apiFetch, escHtml, showToast, ptOpenDetail.
// =============================================================

const PT_PLAY_ERR = {
  round_closed: "pt_err_round_closed", already_submitted: "pt_err_already_sub",
  deadline_in_past: "pt_err_deadline_past", deadline_too_far: "pt_err_deadline_far",
  bad_deadline: "pt_err_bad_deadline", not_enough_players: "pt_err_not_enough", not_multiple: "pt_err_not_multiple",
  wrong_status: "pt_err_wrong_status", not_owner: "pt_err_not_owner", match_not_found: "pt_err_match_404",
  draw_not_allowed: "pt_err_draw", not_ready: "pt_err_not_ready", next_stage_played: "pt_err_next_played",
};

// O'yin bosqichi nomi (guruh turi yoki pley-off bosqichi) — karta va tuzatish oynasi uchun umumiy
function ptStageLabel(m) {
  if (m.stage === "final") return PTT("pt_stage_final");
  if (m.stage === "po") return PTT("pt_stage_po_n", { n: m.round });                 // ChL/YeL pley-off raundi
  if (m.stage === "group" && m.group_label === "L" && PT.play && PT.play.single_table) {
    return PTT("pt_round_short", { r: m.round });                                     // liga/ChL/YeL: guruhsiz
  }
  if (m.stage === "semi") return PTT("pt_stage_semi_n", { n: m.round });
  if (m.stage && m.stage !== "group") return PTT(`pt_stage_${m.stage}_n`, { n: m.round });
  return `${PTT("pt_round_short", { r: m.round })} · ${PTT("pt_group", { g: m.group_label })}`;
}
function ptPlayErr(e) { return PTT(PT_PLAY_ERR[e && e.message] || "pt_err_generic"); }

// Tafsilot sahifasidagi o'rin: recruiting — boshlash tugmasi; running — o'yin bloki
function ptPlayHtml(t) {
  if ((t.is_manager || t.is_owner) && t.status === "recruiting") {   // tashkilotchi yoki admin
    const can = !t.start_block;                      // server hisoblaydi: kamida 8 va 4 ga karrali
    const n = t.approved_count, g = t.group_size || 4, rem = n % g;
    const need = {                                   // 2026-10-07: formatga xos sabablar ham
      not_enough_players: () => PTT("pt_start_min", { n, min: t.min_players }),
      not_multiple: () => PTT("pt_start_need", { n, add: g - rem, remove: rem }),
      not_even: () => PTT("pt_block_even", { n }),
      league_not_full: () => PTT("pt_block_league", { n, max: t.max_players }),
      teams_missing: () => PTT("pt_block_teams", { n: (t.members || []).filter(m => m.status === "approved" && !m.team_name).length }),
    }[t.start_block]?.() || "";
    return `
      <div class="card pt-pay">
        <div class="pt-hint">${escHtml(PTT(t.format && t.format !== "classic" && t.format !== "wc" ? "pt_start_hint_" + (t.format === "league" ? "league" : "cl") : "pt_start_hint", { min: t.min_players, max: t.max_players }))}</div>
        ${need ? `<div class="pt-note">${escHtml(need)}</div>` : ""}
        <button class="btn btn--primary btn--glow" id="pt-start-btn" ${can ? "" : "disabled"}>
          ${escHtml(PTT("pt_start_btn"))}</button>
      </div>`;
  }
  return "";
}

function ptBindPlay(t) {
  document.getElementById("pt-start-btn")?.addEventListener("click", () => void ptStart(t.id));
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

// O'yin ma'lumoti + o'qilmagan xabarlar (sahifalar shu keshdan chiziladi)
async function ptFetchPlay(tid) {
  try {
    const [play, unread] = await Promise.all([
      apiFetch(`/pt/${encodeURIComponent(tid)}/play`),
      apiFetch("/pt/matches/unread").catch(() => ({ by_match: {} })),   // rozetka ixtiyoriy
    ]);
    PT.play = play;
    PT.unread = unread.by_match || {};
  } catch (e) {
    PT.play = null;
  }
}

// Amaldan keyin: o'yin ma'lumoti yangilanadi va JORIY sahifa qayta chiziladi
async function ptLoadPlay(tid) {
  await ptFetchPlay(tid);
  if (PT.view === "detail" && String(PT.detailId) === String(tid)) ptRenderDetail();
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
  const side = k => {                                   // 2026-10-07: klub/terma jamoa logosi + nom
    const team = m[`p${k}_team`];
    const badge = team && typeof ptTeamBadge === "function" ? ptTeamBadge(team) : "";
    return `<b class="pt-mside pt-mside--${k}" ${team ? `title="${escHtml(team)}"` : ""}>${k === 2 ? `<span>${escHtml(ptNameOf(m, k))}</span>${badge}` : `${badge}<span>${escHtml(ptNameOf(m, k))}</span>`}</b>`;
  };
  const names = `<div class="pt-match-row">${side(1)}<span class="pt-score">${score}</span>${side(2)}</div>`;
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
  if (PT.play && PT.play.single_table && typeof ptTableHtml === "function") return ptTableHtml(PT.play, meId);
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
      ${rows.map((r, i) => `<tr class="pt-row-link" data-pt-player="${r.user_id}"><td>${i + 1}</td><td class="pt-table-name">${r.team_name && typeof ptTeamBadge === "function" ? ptTeamBadge(r.team_name) : ""}${escHtml(r.username ? "@" + r.username : r.nickname || "")}</td>
        <td>${r.played}</td><td>${r.goal_diff > 0 ? "+" : ""}${r.goal_diff}</td><td><b>${r.points}</b></td></tr>`).join("")}
      </tbody></table></details>`;
  }).join("");
}

// Tashkilotchi boshqaruvi: muddat (tezkor tanlash + kalendar) va guruhda "Turni yopish".
// Guruh va pley-off uchun umumiy (qoida #26). Natijani tuzatish — alohida karta (ptFixCardHtml).
const PT_DL_PRESETS = [[1, "pt_dl_1d"], [2, "pt_dl_2d"], [3, "pt_dl_3d"], [7, "pt_dl_7d"]];

function ptOwnerControlsHtml(knockout) {
  return `
      <div class="pt-field-label">${escHtml(PTT("pt_dl_quick"))}</div>
      <div class="pt-chips">${PT_DL_PRESETS.map(([d, k]) =>
        `<button class="pt-chip" data-pt-dl="${d}">${escHtml(PTT(k))}</button>`).join("")}</div>
      <input class="modal-input" type="datetime-local" id="pt-deadline-input">
      <div class="pt-hint">${escHtml(PTT(knockout ? "pt_ko_deadline_hint" : "pt_deadline_hint"))}</div>
      <div class="pt-pay-actions${knockout ? " pt-pay-actions--one" : ""}">
        ${knockout ? "" : `<button class="btn btn--ghost" id="pt-close-round">${escHtml(PTT("pt_close_round"))}</button>`}
        <button class="btn btn--primary" id="pt-deadline-btn">${escHtml(PTT("pt_deadline_set"))}</button>
      </div>`;
}

// Tezkor muddat: Toshkent vaqti bilan bugundan N kun keyin, 23:59 (server Toshkent vaqtini kutadi)
function ptPresetDeadline(days) {
  const d = new Date(Date.now() + 5 * 3600 * 1000 + days * 86400 * 1000);   // UTC+5 "soat" sifatida
  const pad = n => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T23:59`;
}

function ptFixCardHtml() {
  return `<div class="card pt-pay">
      <div class="pt-hint">${escHtml(PTT("pt_fix_hint"))}</div>
      <div class="pt-fix-row">
        <input class="modal-input" type="number" min="1" inputmode="numeric" id="pt-fix-id" placeholder="${escHtml(PTT("pt_fix_id_ph"))}">
        <button class="btn btn--ghost" id="pt-fix-load">${escHtml(PTT("pt_fix_load"))}</button>
      </div>
      <div id="pt-fix-box"></div></div>`;
}

// --- Sahifa bo'laklari (pt_tabs.js) ---

// Admin: guruh bosqichida tur boshqaruvi; pley-offda pt_knockout.js
function ptAdminPlayHtml(p) {
  if (!p.is_manager) return "";
  if (p.phase && typeof ptKnockoutAdminHtml === "function") return ptKnockoutAdminHtml(p);
  if (p.groups_finished) return "";
  return `<div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_round_title", { round: p.current_round, total: p.total_rounds }))}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_deadline"))}</span>
        <b>${escHtml(p.deadline_local || PTT("pt_no_deadline"))}</b></div>${ptOwnerControlsHtml(false)}</div>`;
}

// O'yinlarim: guruh + pley-off o'yinlarim (natija, tasdiq, chat, xona ID)
function ptMyMatchesHtml(p) {
  const mine = (p.my_matches || []).map(m => ptMatchCardHtml(m, p, true)).join("");
  return mine || `<div class="empty-state">${escHtml(PTT("pt_no_my_matches"))}</div>`;
}

// Jadval: joriy turning boshqa o'yinlari
function ptRoundOthersHtml(p) {
  const mineIds = new Set((p.my_matches || []).map(m => m.id));
  const others = (p.round_matches || []).filter(m => !mineIds.has(m.id)).map(m => ptMatchCardHtml(m, p, false)).join("");
  return others ? `<div class="section-label pt-label">${escHtml(PTT("pt_round_matches"))}</div>${others}` : "";
}

function ptBindPlayBody(tid) {
  const q = (sel, fn) => document.querySelectorAll(`#pt-root ${sel}`).forEach(fn);
  q("[data-pt-submit]", b => b.addEventListener("click", () => void ptSubmitResult(tid, b.dataset.ptSubmit)));
  q("[data-pt-confirm]", b => b.addEventListener("click", () => void ptConfirmResult(tid, b.dataset.ptConfirm, true)));
  q("[data-pt-rejectres]", b => b.addEventListener("click", () => void ptConfirmResult(tid, b.dataset.ptRejectres, false)));
  document.getElementById("pt-deadline-btn")?.addEventListener("click", () => void ptSetDeadline(tid));
  document.getElementById("pt-close-round")?.addEventListener("click", () => void ptCloseRound(tid));
  q("[data-pt-dl]", b => b.addEventListener("click", () => {
    const inp = document.getElementById("pt-deadline-input");
    if (inp) inp.value = ptPresetDeadline(Number(b.dataset.ptDl));
    document.querySelectorAll("#pt-root [data-pt-dl]").forEach(x => x.classList.toggle("active", x === b));
  }));
  q("[data-pt-chat]", b => b.addEventListener("click", () => {
    b.querySelector(".pt-badge")?.remove();                 // ochilgach o'qildi deb hisoblanadi
    openWebChat(Number(b.dataset.ptChat), b.dataset.ptOpp, "/pt/matches");
  }));
  document.getElementById("pt-fix-load")?.addEventListener("click", () => void ptFixLoad(tid));
  document.getElementById("pt-semis-btn")?.addEventListener("click", () => void ptStartSemis(tid));
}

// Natijani tuzatish (Match ID bo'yicha) — pt_fix.js (2026-10-07, qoida #21)

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
