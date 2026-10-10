// =============================================================
//  pt_replace.js — SHAXSIY turnir: ishtirokchini almashtirish (2026-10-10)
//  Sodda: a'zoni tanlash + yangi odamning Telegram ID / @username -> "Almashtirish".
//  O'rin, klub, o'yinlar va natijalar saqlanadi (backend pt_replace.py).
//  Tashkilotchi/turnir admini, turnir tugamaguncha. Global: PT, PTT, apiFetch, escHtml,
//  showToast, ptOpenDetail, ptIsManager, ptErrText.
// =============================================================

function ptReplaceHtml(t) {
  if (!ptIsManager(t) || !["recruiting", "running"].includes(t.status)) return "";
  const list = (t.members || []).filter(m => m.status === "approved" && m.user_id !== t.owner_user_id);
  if (!list.length) return "";
  const opts = list.map(m => {
    const label = (m.username ? "@" + m.username : (m.nickname || "#" + m.user_id)) + (m.team_name ? ` · ${m.team_name}` : "");
    return `<option value="${m.user_id}">${escHtml(label)}</option>`;
  }).join("");
  return `<div class="card pt-pay">
      <div class="pt-field-label">${escHtml(PTT("pt_replace_pick"))}</div>
      <select class="modal-input" id="pt-replace-old">${opts}</select>
      <input class="modal-input" id="pt-replace-new" maxlength="40" autocomplete="off"
             placeholder="${escHtml(PTT("pt_add_ph"))}" style="margin-top:8px">
      <div class="pt-hint">${escHtml(PTT("pt_replace_hint"))}</div>
      <button class="btn btn--primary" id="pt-replace-btn">${escHtml(PTT("pt_replace_btn"))}</button>
    </div>`;
}

function ptBindReplace(t) {
  document.getElementById("pt-replace-btn")?.addEventListener("click", () => void ptReplaceSubmit(t));
}

async function ptReplaceSubmit(t) {
  if (PT.busy) return;
  const sel = document.getElementById("pt-replace-old");
  const oldId = Number(sel?.value || 0);
  const query = (document.getElementById("pt-replace-new")?.value || "").trim();
  if (!oldId || !query) return;
  const oldLabel = sel.options[sel.selectedIndex]?.text || "";
  if (!window.confirm(PTT("pt_replace_ask", { old: oldLabel, new: query }))) return;
  PT.busy = true;
  try {
    await apiFetch(`/pt/${encodeURIComponent(t.id)}/members/${encodeURIComponent(oldId)}/replace`,
      { method: "POST", body: JSON.stringify({ query }) });
    showToast(PTT("pt_replaced_toast"));
    PT.busy = false;
    await ptOpenDetail(t.id);
  } catch (e) {
    showToast(ptErrText(e));
  } finally {
    PT.busy = false;
  }
}
