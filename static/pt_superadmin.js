// =============================================================
//  pt_superadmin.js — bosh admin: BARCHA shaxsiy turnirlar (2026-10-07)
//  Admin so'rovi: bosh admin ochilgan turnirlarni ko'rsin va tushunmayotgan tashkilotchilarga
//  yordam berish uchun sozlamalarini o'zgartira olsin. Ro'yxat: GET /pt/admin/all (qidiruv + holat
//  filtri); turnir ochilganda bosh admin tashkilotchi huquqlarida (server: is_manager / can_own).
//  Global: PT, PTT, escHtml, apiFetch, ptRender, ptOpenDetail, ptStatusLabel, ptFormatName, ptFmt,
//  ptLeaguesText, PT_FORMAT_META.
// =============================================================

const PT_ALL_STATUSES = ["", "recruiting", "running", "awaiting_payment", "payment_review", "finished", "rejected"];

async function ptOpenAll() {
  PT.view = "all";
  PT.fromAll = true;
  PT.allQ = PT.allQ || "";
  PT.allStatus = PT.allStatus || "";
  ptRender(`<div class="empty-state">${escHtml(PTT("pt_loading"))}</div>`);
  await ptLoadAll();
}

async function ptLoadAll() {
  PT.allSel = new Set();   // 2026-10-13: filtr/qidiruv o'zgarsa tanlov tozalanadi (ko'rinmaydiganlar o'chmasin)
  try {
    const qs = new URLSearchParams({ q: PT.allQ || "", status: PT.allStatus || "" }).toString();
    PT.all = await apiFetch(`/pt/admin/all?${qs}`);
    ptRenderAll();
  } catch (e) {
    ptRender(`<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`);
  }
}

function ptAllCardHtml(t) {
  const f = ptFmt(t);
  const owner = t.owner_username ? "@" + t.owner_username : (t.owner_nickname || "");
  const date = String(t.created_at || "").slice(0, 10);
  const sel = PT.allSel && PT.allSel.has(t.id);
  // 2026-10-13: chapda "Tanlash" katakchasi (ko'plab o'chirish uchun)
  return `<div class="pt-all-item${sel ? " is-sel" : ""}">
    <button class="pt-all-check${sel ? " is-on" : ""}" data-pt-all-pick="${t.id}" title="${escHtml(PTT("pt_sel_pick"))}">${sel ? "✓" : ""}</button>
    <button class="pt-card pt-card--rich" data-pt-all-open="${t.id}">
      <div class="pt-card-top"><span class="pt-card-name">${escHtml(t.name)}</span><span class="pt-muted">#${t.id}</span></div>
      <div class="pt-card-fmt">${PT_FORMAT_META[f] ? PT_FORMAT_META[f].icon : ""} ${escHtml(ptFormatName(f))}${t.league_name ? " · " + escHtml(ptLeaguesText(t.league_name)) : ""}${t.legs === 2 ? " · " + escHtml(PTT("pt_legs_2_short")) : ""}</div>
      <div class="pt-card-meta"><span class="pt-status pt-status--${escHtml(t.status)}">${escHtml(ptStatusLabel(t.status))}</span>
        <span>${t.members_count}/${t.max_players} ${escHtml(PTT("pt_members"))}</span></div>
      <div class="pt-card-meta"><span>👤 ${escHtml(owner)} <span class="pt-muted">· ${escHtml(String(t.owner_telegram_id || ""))}</span></span><span class="pt-muted">${escHtml(date)}</span></div>
      <span class="pt-card-arrow">›</span></button></div>`;
}

// 2026-10-13: tanlov paneli — "Hammasini tanlash" va "O'chirish (k)"
function ptAllBulkBarHtml(list) {
  if (!list.length) return "";
  const n = (PT.allSel || new Set()).size;
  const allOn = n > 0 && list.every(t => PT.allSel.has(t.id));
  return `<div class="pt-bulk-bar">
      <button class="btn btn--ghost" id="pt-all-selall">${escHtml(allOn ? PTT("pt_sel_none") : PTT("pt_sel_all", { n: list.length }))}</button>
      <button class="btn btn--danger" id="pt-all-del"${n ? "" : " disabled"}>${escHtml(PTT("pt_sel_delete", { n }))}</button>
    </div>`;
}

async function ptAllDeleteSelected(btn) {
  const ids = [...(PT.allSel || [])];
  if (!ids.length) { showToast(PTT("pt_sel_empty")); return; }
  const list = (PT.all && PT.all.tournaments) || [];
  const live = list.filter(t => ids.includes(t.id) && ["recruiting", "running", "finished"].includes(t.status)).length;
  const ask = PTT("pt_sel_ask", { n: ids.length }) + (live ? PTT("pt_sel_ask_running", { n: live }) : "");
  if (!window.confirm(ask)) return;
  btn.disabled = true;
  btn.textContent = "⏳";
  try {
    const r = await apiFetch("/pt/admin/delete-bulk", { method: "POST", body: JSON.stringify({ ids }) });
    showToast(PTT("pt_sel_done", { n: r.deleted }) + ((r.failed || []).length ? " · " + PTT("pt_sel_failed", { n: r.failed.length }) : ""));
  } catch (e) {
    showToast(PTT("pt_load_err"));
  }
  await ptLoadAll();
}

function ptRenderAll() {
  PT.view = "all";
  const d = PT.all || { tournaments: [], counts: {}, total: 0 };
  const chip = s => {
    const n = s ? (d.counts[s] || 0) : d.total;
    return `<button class="tab-btn${(PT.allStatus || "") === s ? " active" : ""}" data-pt-all-status="${s}">${escHtml(s ? ptStatusLabel(s) : PTT("pt_all_any"))} · ${n}</button>`;
  };
  ptRender(`
    <div class="card pt-pay pt-super-head">
      <div class="pt-next-kicker">🛡 ${escHtml(PTT("pt_all_title"))}</div>
      <div class="pt-hint">${escHtml(PTT("pt_all_hint"))}</div>
      <div class="pt-fix-row"><input class="modal-input" id="pt-all-q" autocomplete="off" placeholder="${escHtml(PTT("pt_all_search"))}" value="${escHtml(PT.allQ || "")}">
        <button class="btn btn--ghost" id="pt-all-find">${escHtml(PTT("pt_all_find"))}</button></div>
    </div>
    <div class="tab-filter pt-all-filter">${PT_ALL_STATUSES.map(chip).join("")}</div>
    ${ptAllBulkBarHtml(d.tournaments)}
    ${d.tournaments.length ? d.tournaments.map(ptAllCardHtml).join("") : `<div class="empty-state">${escHtml(PTT("pt_all_none"))}</div>`}`);
  const find = () => { PT.allQ = (document.getElementById("pt-all-q").value || "").trim(); void ptLoadAll(); };
  document.getElementById("pt-all-find").addEventListener("click", find);
  document.getElementById("pt-all-q").addEventListener("keydown", e => { if (e.key === "Enter") find(); });
  document.querySelectorAll("#pt-root [data-pt-all-status]").forEach(b => b.addEventListener("click", () => {
    PT.allStatus = b.dataset.ptAllStatus; void ptLoadAll();
  }));
  document.querySelectorAll("#pt-root [data-pt-all-open]").forEach(b => b.addEventListener("click", () => {
    PT.fromAll = true; void ptOpenDetail(b.dataset.ptAllOpen);
  }));
  // 2026-10-13: tanlash / hammasini tanlash / o'chirish — skroll joyi saqlanadi
  const rerender = () => { const y = window.scrollY; ptRenderAll(); window.scrollTo(0, y); };
  document.querySelectorAll("#pt-root [data-pt-all-pick]").forEach(b => b.addEventListener("click", () => {
    if (!PT.allSel) PT.allSel = new Set();
    const id = Number(b.dataset.ptAllPick);
    if (PT.allSel.has(id)) PT.allSel.delete(id); else PT.allSel.add(id);
    rerender();
  }));
  document.getElementById("pt-all-selall")?.addEventListener("click", () => {
    const list = d.tournaments;
    const allOn = PT.allSel && PT.allSel.size > 0 && list.every(t => PT.allSel.has(t.id));
    PT.allSel = allOn ? new Set() : new Set(list.map(t => t.id));
    rerender();
  });
  document.getElementById("pt-all-del")?.addEventListener("click", e => void ptAllDeleteSelected(e.currentTarget));
}
