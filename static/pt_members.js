// =============================================================
//  pt_members.js — SHAXSIY turnirga qo'shilish (2026-10-02, 3-bosqich)
//  1) Taklif bilan kelgan foydalanuvchi: qo'shilish ekrani (?pt_join=<kod>).
//  2) Tashkilotchi (recruiting): taklif havolasi, ID/@username bilan qo'shish,
//     so'rovlarni qabul/rad etish, a'zoni chiqarish.
//  pt.js dan KEYIN ulanadi. Global: PT, PTT, apiFetch, escHtml, showToast,
//  ptRender, ptOpenDetail, ptCopy, ptLoadList.
// =============================================================

const PT_ERR_KEYS = {
  not_found: "pt_err_not_found", user_not_found: "pt_err_user_not_found",
  already_member: "pt_err_already", already_approved: "pt_err_already",
  full: "pt_err_full", not_recruiting: "pt_join_closed", team_taken: "pt_err_team_taken", bad_team: "pt_err_generic",
};
function ptErrText(e) { return PTT(PT_ERR_KEYS[e && e.message] || "pt_err_generic"); }

// Taklif kodi: URL ?pt_join=<kod> yoki Telegram startapp parametri (pt_<kod>).
// Bir marta o'qiladi va URL'dan olib tashlanadi (qayta ochilganda takrorlanmasin).
function ptConsumeInviteParam() {
  let code = null;
  try {
    const params = new URLSearchParams(window.location.search);
    code = params.get("pt_join");
    if (code) {
      params.delete("pt_join");
      const q = params.toString();
      window.history.replaceState(null, "", window.location.pathname + (q ? "?" + q : "") + window.location.hash);
    }
  } catch (_) { code = null; }
  if (!code) {
    const sp = window.Telegram?.WebApp?.initDataUnsafe?.start_param || "";
    if (sp.startsWith("pt_") && !PT._startParamUsed) { code = sp.slice(3); PT._startParamUsed = true; }
  }
  return code && /^[A-Za-z0-9_-]{4,40}$/.test(code) ? code : null;
}

// ---------------- Qo'shilish ekrani ----------------

async function ptOpenJoin(code) {
  PT.view = "join";
  PT.joinCode = code;
  PT.teamPick = { ...(PT.teamPick || {}), join: null };      // yangilangan band ro'yxati bilan qayta tanlanadi
  ptRender(`<div class="empty-state">${escHtml(PTT("pt_loading"))}</div>`);
  try {
    PT.invite = await apiFetch(`/pt/invite/${encodeURIComponent(code)}`);
    ptRenderJoin();
  } catch (e) {
    ptRender(`<div class="empty-state">${escHtml(ptErrText(e))}</div>`);
  }
}

function ptRenderJoin() {
  const p = PT.invite;
  const owner = p.owner_username ? "@" + p.owner_username : (p.owner_nickname || "");
  const full = p.approved_count >= p.max_players;
  let action;
  if (p.my_status === "approved") {
    action = `<div class="pt-note pt-note--ok">${escHtml(PTT("pt_join_member"))}</div>
      <button class="btn btn--primary" id="pt-join-open">${escHtml(PTT("pt_join_open"))}</button>`;
  } else if (p.my_status === "pending") {
    action = `<div class="pt-note">${escHtml(PTT("pt_join_pending"))}</div>`;
  } else if (p.status !== "recruiting") {
    action = `<div class="pt-warn">${escHtml(PTT("pt_join_closed"))}</div>`;
  } else if (full) {
    action = `<div class="pt-warn">${escHtml(PTT("pt_join_full"))}</div>`;
  } else {
    // 2026-10-07: jamoali formatlarda avval klub / terma jamoa tanlanadi
    const fmt = p.format || "classic";
    const needTeam = typeof ptUsesTeams === "function" && ptUsesTeams(fmt);
    const picked = (PT.teamPick || {}).join;
    action = (needTeam ? `<div class="section-label pt-label">${escHtml(PTT(fmt === "wc" ? "pt_team_pick_wc" : "pt_team_pick_club"))}</div>
        ${ptTeamPickerHtml({ id: "join", fmt, league: p.league_name, taken: p.taken_teams || [] })}` : "")
      + `<button class="btn btn--primary btn--glow" id="pt-join-btn" ${needTeam && !picked ? "disabled" : ""}>${escHtml(PTT("pt_join_btn"))}</button>`;
  }
  ptRender(`
    <div class="card pt-head">
      <div class="section-label pt-label">${escHtml(PTT("pt_join_title"))}</div>
      <div class="pt-head-name">${escHtml(p.name)}</div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_join_owner"))}</span><b>${escHtml(owner)}</b></div>
      <div class="pt-card-row"><span>${escHtml(PTT("pt_join_places"))}</span><b>${p.approved_count}/${p.max_players}</b></div>
      ${p.format && typeof ptFormatName === "function" ? `<div class="pt-card-row"><span>${escHtml(PTT("pt_join_format"))}</span>
        <b>${escHtml(ptFormatName(p.format))}${p.league_name ? " · " + escHtml(p.league_name) : ""}</b></div>` : ""}
      ${action}
    </div>`);
  document.getElementById("pt-join-btn")?.addEventListener("click", ptJoinSubmit);
  if (typeof ptBindTeamPicker === "function") {
    ptBindTeamPicker({ id: "join", fmt: p.format || "classic", league: p.league_name, taken: p.taken_teams || [] }, () => {
      const b = document.getElementById("pt-join-btn");
      if (b) b.disabled = false;
    });
  }
  document.getElementById("pt-join-open")?.addEventListener("click", () => void ptOpenDetail(p.id));
}

async function ptJoinSubmit() {
  if (PT.busy) return;
  PT.busy = true;
  const btn = document.getElementById("pt-join-btn");
  if (btn) btn.disabled = true;
  try {
    const team = (PT.teamPick || {}).join || null;
    await apiFetch("/pt/join", { method: "POST", body: JSON.stringify({ code: PT.joinCode, team }) });
    showToast(PTT("pt_join_sent"));
  } catch (e) {
    showToast(ptErrText(e));
  } finally {
    PT.busy = false;
  }
  await ptOpenJoin(PT.joinCode);
}

// ---------------- Tashkilotchi boshqaruvi (pt.js ptRenderDetail chaqiradi) ----------------

// Tashkilotchi YOKI turnir admini (2026-10-03); to'lov va sig'im — faqat tashkilotchi (pt.js/pt_size.js)
function ptCanManage(t) { return (t.is_manager || t.is_owner) && t.status === "recruiting"; }

function ptManageHtml(t) {
  if (!ptCanManage(t)) return "";
  return `
    <div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_invite_title"))}</div>
      <div class="pt-hint">${escHtml(PTT("pt_invite_hint"))}</div>
      <div class="pt-link-box" id="pt-invite-link">${escHtml(PTT("pt_loading"))}</div>
      <div class="pt-pay-actions">
        <button class="btn btn--ghost" id="pt-link-copy" disabled>${escHtml(PTT("pt_copy"))}</button>
        <button class="btn btn--primary" id="pt-link-share" disabled>${escHtml(PTT("pt_share"))}</button>
      </div>
    </div>
    <div class="card pt-pay">
      <div class="section-label pt-label">${escHtml(PTT("pt_add_title"))}</div>
      <input class="modal-input" id="pt-add-input" maxlength="40" autocomplete="off"
             placeholder="${escHtml(PTT("pt_add_ph"))}">
      <div class="pt-hint">${escHtml(PTT("pt_add_hint"))}</div>
      <button class="btn btn--primary" id="pt-add-btn">${escHtml(PTT("pt_add_btn"))}</button>
    </div>`;
}

function ptMemberRowHtml(t, m) {
  const who = (m.team_name && typeof ptTeamBadge === "function" ? ptTeamBadge(m.team_name) : "")
    + escHtml(m.nickname || "") + (m.username ? ` <span class="pt-muted">@${escHtml(m.username)}</span>` : "")
    + (m.team_name ? ` <span class="pt-muted">· ${escHtml(m.team_name)}</span>` : "");
  let actions = "";
  if (ptCanManage(t) && m.user_id !== t.owner_user_id) {
    actions = m.status === "pending"
      ? `<span class="pt-row-actions">
           <button class="pt-mini pt-mini--ok" data-pt-mapprove="${m.user_id}">${escHtml(PTT("pt_approve_short"))}</button>
           <button class="pt-mini pt-mini--no" data-pt-mremove="${m.user_id}">${escHtml(PTT("pt_reject_short"))}</button>
         </span>`
      : `<button class="pt-mini pt-mini--no" data-pt-mremove="${m.user_id}" data-pt-confirm="1"
                 data-pt-who="${escHtml(m.nickname || "")}">${escHtml(PTT("pt_remove"))}</button>`;
  } else if (m.status === "pending") {
    actions = `<span class="pt-status pt-status--payment_review">${escHtml(PTT("pt_pending"))}</span>`;
  } else if (m.user_id === t.owner_user_id) {
    actions = `<span class="pt-tag">${escHtml(PTT("pt_owner_tag"))}</span>`;
  }
  if (m.user_id !== t.owner_user_id && (t.admins || []).some(a => a.user_id === m.user_id)) {
    actions = `<span class="pt-tag pt-tag--admin">${escHtml(PTT("pt_admin_tag"))}</span>` + actions;
  }
  return `<div class="match-item pt-member"><span>${who}</span>${actions}</div>`;
}

function ptMembersHtml(t) {
  const members = t.members || [];
  const pending = members.filter(m => m.status === "pending");
  const approved = members.filter(m => m.status === "approved");
  const req = pending.length ? `
    <div class="section-label pt-label">${escHtml(PTT("pt_requests_title"))} (${pending.length})</div>
    ${pending.map(m => ptMemberRowHtml(t, m)).join("")}` : "";
  return `${req}
    <div class="section-label pt-label">${escHtml(PTT("pt_members_title"))} (${approved.length}/${t.max_players})</div>
    ${approved.map(m => ptMemberRowHtml(t, m)).join("")}`;
}

function ptBindManage(t) {
  if (!ptCanManage(t)) return;
  if (document.getElementById("pt-invite-link")) void ptLoadInviteLink(t);   // faqat Admin sahifasida
  document.getElementById("pt-add-btn")?.addEventListener("click", () => void ptAddMember(t.id));
  document.querySelectorAll("#pt-root [data-pt-mapprove]").forEach(b =>
    b.addEventListener("click", () => void ptMemberAction(t.id, b.dataset.ptMapprove, "approve")));
  document.querySelectorAll("#pt-root [data-pt-mremove]").forEach(b =>
    b.addEventListener("click", () => {
      if (b.dataset.ptConfirm && !window.confirm(PTT("pt_remove_ask", { who: b.dataset.ptWho || "" }))) return;
      void ptMemberAction(t.id, b.dataset.ptMremove, "remove");
    }));
}

async function ptLoadInviteLink(t) {
  const box = document.getElementById("pt-invite-link");
  try {
    const { link } = await apiFetch(`/pt/${encodeURIComponent(t.id)}/invite-link`);
    if (!box) return;
    box.textContent = link;
    const copy = document.getElementById("pt-link-copy");
    const share = document.getElementById("pt-link-share");
    copy.disabled = false;
    share.disabled = false;
    copy.addEventListener("click", () => ptCopy(link));
    share.addEventListener("click", () => {
      const url = "https://t.me/share/url?url=" + encodeURIComponent(link)
        + "&text=" + encodeURIComponent(PTT("pt_share_text", { name: t.name }));
      const tg = window.Telegram?.WebApp;
      if (tg && typeof tg.openTelegramLink === "function") tg.openTelegramLink(url);
      else window.open(url, "_blank");
    });
  } catch (e) {
    if (box) box.textContent = PTT("pt_load_err");
  }
}

async function ptAddMember(tid) {
  if (PT.busy) return;
  const input = document.getElementById("pt-add-input");
  const query = (input?.value || "").trim();
  if (!query) return;
  PT.busy = true;
  try {
    await apiFetch(`/pt/${encodeURIComponent(tid)}/members/add`, { method: "POST", body: JSON.stringify({ query }) });
    showToast(PTT("pt_added_toast"));
    PT.busy = false;
    await ptOpenDetail(tid);
  } catch (e) {
    showToast(ptErrText(e));
  } finally {
    PT.busy = false;
  }
}

async function ptMemberAction(tid, userId, action) {
  if (PT.busy) return;
  PT.busy = true;
  try {
    await apiFetch(`/pt/${encodeURIComponent(tid)}/members/${encodeURIComponent(userId)}/${action}`, { method: "POST" });
  } catch (e) {
    showToast(ptErrText(e));
  } finally {
    PT.busy = false;
  }
  await ptOpenDetail(tid);
}
