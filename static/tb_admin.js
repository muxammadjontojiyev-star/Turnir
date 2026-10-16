// =============================================================
//  tb_admin.js — "TEAMLAR JANGI": admin tabi (2026-10-15, 1-bosqich; 2026-10-16 — ligalar)
//  Teamlarni tasdiqlash / rad etish (sabab bilan, sardorga bot xabari) / o'chirish.
//  2026-10-16: tab bosh admin va liga adminlariga ko'rinadi; yuqorida liga tanlash va liga
//  boshqaruvi (tb_admin_league.js), so'ng mavsum (tb_admin_season.js), so'ng shu liga teamlari.
//  Backend: GET /tb/admin/teams?league_id=, POST /tb/admin/review, POST /tb/admin/delete.
//  tb.js dan KEYIN ulanadi. Global: TB, tbRender, tbErr, tbWho, apiFetch, escHtml, showToast.
// =============================================================

const TB_ADMIN_FILTERS = [["pending", "Kutilmoqda"], ["approved", "Tasdiqlangan"], ["rejected", "Rad etilgan"], ["all", "Hammasi"]];

async function tbAdminLoad() {
  tbRender(`<div class="empty-state">Yuklanmoqda…</div>`);
  try {
    await tbAdminLeaguesLoad();                                              // 2026-10-16: ligalar
    const lid = TB.adminLeagueId;
    TB.adminTeams = lid ? (await apiFetch(`/tb/admin/teams?league_id=${lid}`)).teams || [] : [];
    if (lid && typeof tbAdminSeasonLoad === "function") await tbAdminSeasonLoad();
  } catch (e) {
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div>`);
    return;
  }
  tbAdminRender();
}

function tbAdminRender() {
  const f = TB.adminFilter;
  const list = TB.adminTeams.filter(t => f === "all" || t.status === f);
  const count = (s) => TB.adminTeams.filter(t => s === "all" || t.status === s).length;
  const chips = TB_ADMIN_FILTERS.map(([k, l]) =>
    `<button class="tb-chip${f === k ? " active" : ""}" data-tb-af="${k}">${escHtml(l)} <b>${count(k)}</b></button>`).join("");
  const rows = list.map(t => `
    <div class="card tb-adm-row">
      <div class="tb-adm-top">
        <span class="tb-row-emoji">${escHtml(t.emoji || "⚔️")}</span>
        <span class="tb-row-info"><b>${escHtml(t.name)}</b>
          <span>Sardor: ${escHtml(tbWho({ username: t.captain_username, nickname: t.captain_nickname }))} · ${t.members_count} a'zo · tarkib ${t.lineup_count}</span></span>
        <span class="tb-status tb-status--${t.status}">${t.status === "pending" ? "⏳" : t.status === "approved" ? "✅" : "❌"}</span>
      </div>
      ${t.reject_reason ? `<div class="tb-hint">Sabab: ${escHtml(t.reject_reason)}</div>` : ""}
      <div class="tb-adm-acts">
        ${t.status !== "approved" ? `<button class="tb-mini tb-mini--ok" data-tb-adm="approve" data-id="${t.id}">✅ Tasdiqlash</button>` : ""}
        ${t.status !== "rejected" ? `<button class="tb-mini tb-mini--danger" data-tb-adm="reject" data-id="${t.id}">❌ Rad etish</button>` : ""}
        <button class="tb-mini" data-tb-adm="view" data-id="${t.id}">👥 A'zolar</button>
        <button class="tb-mini tb-mini--danger" data-tb-adm="delete" data-id="${t.id}">🗑 O'chirish</button>
      </div>
    </div>`).join("");
  const leagues = tbAdminLeaguesHtml();
  if (!TB.adminLeagueId) { tbRender(leagues); return; }
  const season = typeof tbAdminSeasonHtml === "function" ? tbAdminSeasonHtml() : "";
  tbRender(`${leagues}${season}<div class="tb-chips">${chips}</div>
    ${rows || `<div class="empty-state">Bu bo'limda team yo'q</div>`}`);
}

async function tbAdminAct(kind, id, btn) {
  let path, body;
  if (kind === "approve") { path = "/tb/admin/review"; body = { team_id: id, approve: true }; }
  else if (kind === "reject") {
    const reason = prompt("Rad etish sababi (sardorga yuboriladi):", "");
    if (reason === null) return;
    path = "/tb/admin/review"; body = { team_id: id, approve: false, reason };
  } else if (kind === "delete") {
    if (!confirm("Team butunlay o'chirilsinmi? Barcha a'zolar chiqariladi.")) return;
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
  const chip = e.target.closest("#tb-root [data-tb-af]");
  if (chip) { TB.adminFilter = chip.dataset.tbAf; tbAdminRender(); return; }
  const b = e.target.closest("#tb-root [data-tb-adm]");
  if (!b) return;
  const id = +b.dataset.id;
  if (b.dataset.tbAdm === "view") { if (typeof tbOpenTeam === "function") void tbOpenTeam(id); return; }
  void tbAdminAct(b.dataset.tbAdm, id, b);
});
