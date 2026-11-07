// =============================================================
//  tb_admin.js — "TEAMLAR JANGI": admin tabi (2026-10-15, 1-bosqich; 2026-10-16 — ligalar)
//  Teamlarni tasdiqlash / rad etish (sabab bilan, sardorga bot xabari) / o'chirish.
//  2026-10-16: tab bosh admin va liga adminlariga ko'rinadi; yuqorida liga tanlash va liga
//  boshqaruvi (tb_admin_league.js), so'ng mavsum (tb_admin_season.js), so'ng shu liga teamlari.
//  Backend: GET /tb/admin/teams?league_id=, POST /tb/admin/review, POST /tb/admin/delete,
//  POST /tb/admin/delete-bulk (2026-10-16: tanlanganlarni bir yo'la o'chirish).
//  tb.js dan KEYIN ulanadi. Global: TB, tbRender, tbErr, tbWho, apiFetch, escHtml, showToast.
// =============================================================

const TB_ADMIN_FILTERS = [["pending", "Kutilmoqda"], ["approved", "Tasdiqlangan"], ["rejected", "Rad etilgan"], ["all", "Hammasi"]];

async function tbAdminLoad() {
  tbRender(`<div class="empty-state">Yuklanmoqda…</div>`);
  TB.adminSel = new Set();          // 2026-10-16: qayta yuklanganda tanlov tozalanadi
  try {
    await tbAdminLeaguesLoad();                                              // 2026-10-16: ligalar
    const lid = TB.adminLeagueId;
    TB.adminTeams = lid ? (await apiFetch(`/tb/admin/teams?league_id=${lid}`)).teams || [] : [];
    if (lid && typeof tbAdminSeasonLoad === "function") await tbAdminSeasonLoad();
    if (lid && typeof tbReportsLoad === "function") await tbReportsLoad(lid);     // 2026-10-25: shikoyatlar
  } catch (e) {
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div>`);
    return;
  }
  tbAdminRender();
}

function tbAdminRender() {
  if (TB.adminFilter === "pending" && !TB.adminFilterUser                  // 2026-11-07: ariza yo'q — bo'sh ro'yxat emas
      && !(TB.adminTeams || []).some(t => t.status === "pending")) TB.adminFilter = "all";
  const f = TB.adminFilter;
  const list = TB.adminTeams.filter(t => f === "all" || t.status === f);
  const count = (s) => TB.adminTeams.filter(t => s === "all" || t.status === s).length;
  const chips = TB_ADMIN_FILTERS.map(([k, l]) =>
    `<button class="tb-chip${f === k ? " active" : ""}" data-tb-af="${k}">${escHtml(l)} <b>${count(k)}</b></button>`).join("");
  const sel = TB.adminSel || new Set();
  const rows = list.map(t => `
    <div class="tb-adm-item${sel.has(t.id) ? " is-sel" : ""}">
    <button class="pt-all-check${sel.has(t.id) ? " is-on" : ""}" data-tb-pick="${t.id}" title="Tanlash">${sel.has(t.id) ? "✓" : ""}</button>
    <div class="card tb-adm-row">
      <div class="tb-adm-top">
        <span class="tb-row-emoji">${tbLogo("team", t.id, t.logo_ver, t.emoji)}</span>
        <span class="tb-row-info"><b>${escHtml(t.name)}</b>
          <span>Sardor: ${escHtml(tbWho({ username: t.captain_username, nickname: t.captain_nickname }))} · ${t.members_count} a'zo · tarkib ${t.lineup_count}</span></span>
        <span class="tb-status tb-status--${t.status}">${t.status === "pending" ? "⏳" : t.status === "approved" ? "✅" : "❌"}</span>
      </div>
      ${t.reject_reason ? `<div class="tb-hint">Sabab: ${escHtml(t.reject_reason)}</div>` : ""}
      <div class="tb-act-grid">
        ${t.status !== "approved" ? `<button class="tb-act tb-act--ok" data-tb-adm="approve" data-id="${t.id}">✅ Tasdiqlash</button>` : ""}
        ${t.status !== "rejected" ? `<button class="tb-act tb-act--warn" data-tb-adm="reject" data-id="${t.id}">❌ Rad etish</button>` : ""}
        <button class="tb-act" data-tb-adm="view" data-id="${t.id}">👥 A'zolar</button>
        <button class="tb-act tb-act--danger" data-tb-adm="delete" data-id="${t.id}">🗑 O'chirish</button>
      </div>
    </div></div>`).join("");
  // 2026-11-07: dizayn — tepada liga tanlash, ostida bo'limlar paneli; bir vaqtda bitta bo'lim (tushunarli, qisqa)
  const chipsTop = tbAdminLeaguesHtml("chips");
  if (!TB.adminLeagueId) { tbRender(chipsTop); return; }
  const nRep = (TB.adminReports || []).length;
  if (!TB.adminSec) TB.adminSec = count("pending") ? "teams" : nRep ? "reports" : "teams";
  const segs = [["teams", "🛡", "Teamlar", count("pending")], ["season", "📅", "Mavsum", 0],
                ["reports", "🚩", "Shikoyat", nRep], ["league", "⚙️", "Liga", 0]];
  const seg = `<div class="tb-asec">${segs.map(([k, ic, l, n]) => `<button class="tb-asec-item${TB.adminSec === k ? " active" : ""}"
      data-tb-asec="${k}"><span>${ic}</span>${escHtml(l)}${n ? `<b class="tb-asec-badge">${n}</b>` : ""}</button>`).join("")}</div>`;
  let content;
  if (TB.adminSec === "season") content = typeof tbAdminSeasonHtml === "function" ? tbAdminSeasonHtml() : "";
  else if (TB.adminSec === "reports") content = typeof tbReportsAdminHtml === "function" ? tbReportsAdminHtml() : "";
  else if (TB.adminSec === "league") content = tbAdminLeaguesHtml("manage");
  else content = `<div class="tb-chips">${chips}</div>${tbAdminBulkBarHtml(list)}
    ${rows || `<div class="empty-state">Bu bo'limda team yo'q</div>`}`;
  tbRender(`${chipsTop}${seg}<div class="tb-asec-body">${content}</div>`);
  if (typeof chatLoadImages === "function") chatLoadImages(document.querySelector("#tb-root .tb-body"));
}

// 2026-10-16: ko'plab o'chirish (shaxsiy turnirdagi kabi) — faqat ko'rinib turgan ro'yxatdan
function tbAdminVisible() {
  const f = TB.adminFilter;
  return (TB.adminTeams || []).filter(t => f === "all" || t.status === f);
}

function tbAdminBulkBarHtml(list) {
  if (!list.length) return "";
  const sel = TB.adminSel || new Set();
  const n = list.filter(t => sel.has(t.id)).length;
  const allOn = n > 0 && n === list.length;
  return `<div class="pt-bulk-bar">
      <button class="btn btn--ghost" data-tb-bulk="all">${allOn ? "Tanlovni bekor qilish" : `Hammasini tanlash (${list.length})`}</button>
      <button class="btn btn--danger" data-tb-bulk="delete"${n ? "" : " disabled"}>🗑 O'chirish (${n})</button>
    </div>`;
}

function tbAdminRerender() { const y = window.scrollY; tbAdminRender(); window.scrollTo(0, y); }

async function tbAdminBulkDelete(btn) {
  const visible = new Set(tbAdminVisible().map(t => t.id));
  const ids = [...(TB.adminSel || [])].filter(id => visible.has(id));
  if (!ids.length) return;
  if (!confirm(TB.me.is_super
    ? `${ids.length} ta team butunlay o'chirilsinmi? A'zolari, bahslari, o'yinlari va chempionliklari ham o'chadi. Qaytarib bo'lmaydi!`
    : `${ids.length} ta team butunlay o'chirilsinmi? Barcha a'zolari chiqariladi. Mavsumda qatnashgan teamlar o'chirilmaydi.`)) return;
  btn.disabled = true;
  btn.textContent = "⏳";
  try {
    const r = await apiFetch("/tb/admin/delete-bulk", { method: "POST",
      body: JSON.stringify({ league_id: TB.adminLeagueId, ids }) });
    showToast(`✅ ${r.deleted} ta team o'chirildi` + ((r.failed || []).length ? ` · ${r.failed.length} tasi o'chirilmadi` : ""));
  } catch (e) {
    showToast("❌ " + tbErr(e));
  }
  await tbAdminLoad();
}

async function tbAdminAct(kind, id, btn) {
  let path, body;
  if (kind === "approve") { path = "/tb/admin/review"; body = { team_id: id, approve: true }; }
  else if (kind === "reject") {
    const reason = prompt("Rad etish sababi (sardorga yuboriladi):", "");
    if (reason === null) return;
    path = "/tb/admin/review"; body = { team_id: id, approve: false, reason };
  } else if (kind === "delete") {
    if (!confirm(TB.me.is_super                       // 2026-11-07: bosh admin — istalgan holatda (tb_force.py)
      ? "Team butunlay o'chirilsinmi? A'zolar, mavsumdagi bahslari, o'yinlari va chempionliklari ham o'chadi. Qaytarib bo'lmaydi!"
      : "Team butunlay o'chirilsinmi? Barcha a'zolar chiqariladi.")) return;
    path = "/tb/admin/delete"; body = { team_id: id };
  } else return;
  btn.disabled = true;
  try {
    await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    showToast(kind === "approve" ? "✅ Tasdiqlandi" : kind === "reject" ? "Rad etildi" : "O'chirildi");
    await tbAdminLoad();
  } catch (e) {
    showToast("❌ " + tbErr(e));
    btn.disabled = false;
  }
}

document.addEventListener("click", (e) => {
  if (!e.target.closest) return;
  const sec = e.target.closest("#tb-root [data-tb-asec]");
  if (sec) { TB.adminSec = sec.dataset.tbAsec; tbAdminRender(); window.scrollTo(0, 0); return; }
  const chip = e.target.closest("#tb-root [data-tb-af]");
  if (chip) { TB.adminFilter = chip.dataset.tbAf; TB.adminFilterUser = true; TB.adminSel = new Set(); tbAdminRender(); return; }
  const pick = e.target.closest("#tb-root [data-tb-pick]");
  if (pick) {
    if (!TB.adminSel) TB.adminSel = new Set();
    const id = +pick.dataset.tbPick;
    if (TB.adminSel.has(id)) TB.adminSel.delete(id); else TB.adminSel.add(id);
    tbAdminRerender();
    return;
  }
  const bulk = e.target.closest("#tb-root [data-tb-bulk]");
  if (bulk) {
    if (bulk.dataset.tbBulk === "delete") { void tbAdminBulkDelete(bulk); return; }
    const list = tbAdminVisible(), sel = TB.adminSel || new Set();
    const allOn = list.length > 0 && list.every(t => sel.has(t.id));
    TB.adminSel = allOn ? new Set() : new Set(list.map(t => t.id));
    tbAdminRerender();
    return;
  }
  const b = e.target.closest("#tb-root [data-tb-adm]");
  if (!b) return;
  const id = +b.dataset.id;
  if (b.dataset.tbAdm === "view") { if (typeof tbOpenTeam === "function") void tbOpenTeam(id); return; }
  void tbAdminAct(b.dataset.tbAdm, id, b);
});
