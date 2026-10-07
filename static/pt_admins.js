// =============================================================
//  pt_admins.js — SHAXSIY turnir adminlari (2026-10-03)
//  Tashkilotchi: admin qo'shish (Telegram ID / @username) va olib tashlash (cheksiz).
//  Adminlar ro'yxatni ko'radi (o'zgartira olmaydi). Admin huquqlari: a'zolar, boshlash,
//  muddat, natija tuzatish, pley-off; admin qo'shish, sig'im, to'lov — faqat tashkilotchida.
//  Global: PT, PTT, apiFetch, escHtml, showToast, ptOpenDetail.
// =============================================================

const PT_ADMIN_ERR = {
  user_not_found: "pt_err_user_not_found", is_owner: "pt_err_admin_owner", already_admin: "pt_err_admin_already",
  not_owner: "pt_err_not_owner", finished: "pt_err_wrong_status", admin_not_found: "pt_err_wrong_status",
};

function ptAdminsHtml(t) {
  const finished = ["finished", "cancelled"].includes(t.status);
  if (!t.is_manager && !t.is_owner) return "";
  const list = (t.admins || []).map(a => `
    <div class="match-item pt-member">
      <span>${escHtml(a.nickname || "")}${a.username ? ` <span class="pt-muted">@${escHtml(a.username)}</span>` : ""}</span>
      ${(t.can_own || t.is_owner) && !finished ? `<button class="pt-mini pt-mini--no" data-pt-arem="${a.user_id}" data-pt-who="${escHtml(a.nickname || "")}">${escHtml(PTT("pt_remove"))}</button>`
        : `<span class="pt-tag pt-tag--admin">${escHtml(PTT("pt_admin_tag"))}</span>`}
    </div>`).join("");
  const add = (t.can_own || t.is_owner) && !finished ? `
    <div class="card pt-pay">
      <div class="pt-hint">${escHtml(PTT("pt_admins_hint"))}</div>
      <div class="pt-fix-row">
        <input class="modal-input" id="pt-admin-input" maxlength="40" autocomplete="off" placeholder="${escHtml(PTT("pt_add_ph"))}">
        <button class="btn btn--ghost" id="pt-admin-add">${escHtml(PTT("pt_add_btn"))}</button>
      </div>
    </div>` : "";
  if (!list && !add) return "";
  return `<div class="section-label pt-label">🛡 ${escHtml(PTT("pt_admins_title"))} (${(t.admins || []).length})</div>
    ${add}${list}`;
}

function ptBindAdmins(t) {
  document.getElementById("pt-admin-add")?.addEventListener("click", () => void ptAdminAdd(t.id));
  document.querySelectorAll("#pt-root [data-pt-arem]").forEach(b => b.addEventListener("click", () => {
    if (!window.confirm(PTT("pt_admin_remove_ask", { who: b.dataset.ptWho || "" }))) return;
    void ptAdminAction(t.id, `/pt/${encodeURIComponent(t.id)}/admins/${encodeURIComponent(b.dataset.ptArem)}/remove`, null, "pt_admin_removed");
  }));
}

function ptAdminAdd(tid) {
  const query = (document.getElementById("pt-admin-input")?.value || "").trim();
  if (!query) return;
  return ptAdminAction(tid, `/pt/${encodeURIComponent(tid)}/admins/add`, { query }, "pt_admin_added");
}

async function ptAdminAction(tid, path, body, okKey) {
  if (PT.busy) return;
  PT.busy = true;
  try {
    await apiFetch(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
    showToast(PTT(okKey));
  } catch (e) {
    showToast(PTT(PT_ADMIN_ERR[e && e.message] || "pt_err_generic"));
  } finally {
    PT.busy = false;
  }
  await ptOpenDetail(tid);
}
