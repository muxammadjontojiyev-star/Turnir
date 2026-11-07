// =============================================================
//  tb_my.js — "TEAMLAR JANGI": «Teamim» sahifasi YANGI TUZILISHI (2026-11-07, egasi: «ichki tugmalar joylashuvi
//  dizaynini juda chiroyli, hammaga tushunarli va qulay qilib yarating»).
//  Team kartasi → plitkalar (sardor: Taklif · Tarkib · A'zolar · Logo; a'zo: Tarkib · A'zolar) → bitta ochiq panel →
//  pastda alohida «Xavfli amallar» (tarqatish / chiqish). Uzun sahifa o'rniga — bir qarashda tushunarli menyu.
//  tb.js (tbTeamHeadHtml, tbMemberRowHtml) va tb_team.js (tbCap*Html) dan KEYIN ulanadi.
//  Global: TB, escHtml, tbI18nApply, tbRerenderMyTeam.
// =============================================================

const TB_MY_SECS = {
  invite: { ic: "🔗", t: "Taklif qilish", cap: true },
  lineup: { ic: "📋", t: "Asosiy tarkib" },
  members: { ic: "👥", t: "A'zolar" },
  logo: { ic: "🖼", t: "Team logosi", cap: true },
};

function tbMySecDefault(t) {
  const lineup = t.members.filter(m => m.in_lineup).length;
  if (t.is_captain && t.members.length < TB.me.lineup_min) return "invite";      // a'zo yetmaydi — avval taklif
  if (t.is_captain && lineup < TB.me.lineup_min) return "members";             // «＋» bilan tarkib yig'ish
  return lineup < TB.me.lineup_min ? "lineup" : "members";
}

function tbMyTileHtml(key, t) {
  const s = TB_MY_SECS[key];
  const lineup = t.members.filter(m => m.in_lineup).length;
  const lmin = TB.me.lineup_min;
  const sub = {
    invite: "Do'stlarni chaqiring",
    lineup: `${lineup} / ${lmin}–${TB.me.lineup_max}`,
    members: `${t.members.length} kishi`,
    logo: "Galereyadan",
  }[key];
  const warn = key === "lineup" && lineup < lmin;
  return `<button class="tb-tile${TB.mySec === key ? " active" : ""}${warn ? " warn" : ""}" data-tb-sec="${key}">
      <span class="tb-tile-ic">${s.ic}</span>
      <span class="tb-tile-t">${escHtml(s.t)}</span>
      <span class="tb-tile-s">${escHtml(sub)}</span>
    </button>`;
}

function tbMyPanelHtml(key, t) {
  const cap = t.is_captain;
  if (key === "invite" && cap) return tbCapInviteHtml(t);
  if (key === "logo" && cap) return tbCapLogoHtml(t);
  if (key === "lineup") {
    if (cap && typeof tbCapLineupHtml === "function") return tbCapLineupHtml(t);
    const lineup = t.members.filter(m => m.in_lineup).sort((a, b) => a.lineup_pos - b.lineup_pos);
    const short = lineup.length < TB.me.lineup_min
      ? `<div class="tb-warn">Asosiy tarkib to'liq emas: ${lineup.length}/${TB.me.lineup_min}. Sardor tarkibni tuzishi kerak.</div>` : "";
    return `${short}<div class="card tb-list">${lineup.length ? lineup.map(m => tbMemberRowHtml(m, t, false)).join("")
      : `<div class="tb-hint">Tarkib hali tuzilmagan</div>`}</div>`;
  }
  const head = cap ? tbLineupBarHtml(t) : "";
  return `${head}<div class="card tb-list">${t.members.map(m => tbMemberRowHtml(m, t, cap)).join("")}</div>`;
}

// ---- 2026-11-07 (egasi): sardor a'zolar ro'yxatidan «＋» bilan asosiy tarkibga qo'shadi; liga maksimumidan ko'p — yo'q ----
function tbLineupIds(t) {
  return t.members.filter(m => m.in_lineup).sort((a, b) => a.lineup_pos - b.lineup_pos).map(m => m.user_id);
}

function tbLineupBarHtml(t) {
  const n = tbLineupIds(t).length, { lineup_min: lmin, lineup_max: lmax } = TB.me;
  const cls = n > lmax ? "tb-bad" : n >= lmin ? "tb-ok" : "tb-bad";
  return `<div class="tb-lu-bar">
      <span>Asosiy tarkib: <b class="${cls}">${n}</b> / ${lmax}</span>
      <small>${n >= lmax ? "Tarkib to'ldi" : `«＋» — tarkibga qo'shish${n < lmin ? ` · kamida ${lmin} kishi kerak` : ""}`}</small>
    </div>`;
}

function tbLineupToggleHtml(m, t) {
  const ids = tbLineupIds(t);
  const pos = ids.indexOf(m.user_id);
  if (pos >= 0) {
    return `<button class="tb-lu-tog on" data-tb-lutog="${m.user_id}" title="Tarkibdan olish" aria-label="Tarkibdan olish">✓<i>${pos + 1}</i></button>`;
  }
  const full = ids.length >= TB.me.lineup_max;
  return `<button class="tb-lu-tog${full ? " full" : ""}" data-tb-lutog="${m.user_id}" ${full ? "disabled" : ""}
      title="${full ? "Tarkib to'ldi" : "Tarkibga qo'shish"}" aria-label="Tarkibga qo'shish">＋</button>`;
}

async function tbLineupToggle(btn) {
  const t = TB.me && TB.me.team;
  if (!t || !t.is_captain || btn.disabled) return;
  const id = +btn.dataset.tbLutog;
  const ids = tbLineupIds(t);
  const next = ids.includes(id) ? ids.filter(x => x !== id) : ids.concat(id);
  if (next.length > TB.me.lineup_max) { tbToast(`Ko'pi bilan ${TB.me.lineup_max} kishi`); return; }
  const ok = await tbAction("/tb/lineup", { user_ids: next }, ids.includes(id) ? "Tarkibdan olindi" : "✅ Tarkibga qo'shildi", btn);
  if (ok) TB.mySec = "members";
}

function tbMyTeamHtml(t) {
  const cap = t.is_captain;
  const keys = Object.keys(TB_MY_SECS).filter(k => cap || !TB_MY_SECS[k].cap);
  if (!keys.includes(TB.mySec)) TB.mySec = tbMySecDefault(t);
  return `
    ${tbTeamHeadHtml(t)}
    ${t.status === "pending" ? `<div class="tb-note">Team admin tasdig'ini kutmoqda. Shu vaqtda a'zolarni yig'ib, tarkibni tuzib qo'ying.</div>` : ""}
    <div class="tb-tiles tb-tiles--${keys.length}">${keys.map(k => tbMyTileHtml(k, t)).join("")}</div>
    <div class="tb-panel">
      <div class="tb-panel-title">${TB_MY_SECS[TB.mySec].ic} <span>${escHtml(TB_MY_SECS[TB.mySec].t)}</span></div>
      ${tbMyPanelHtml(TB.mySec, t)}
    </div>
    <details class="tb-danger-zone"><summary>⚠️ Xavfli amallar</summary>
      ${cap
        ? `<div class="tb-hint">Team butunlay o'chadi, barcha a'zolar chiqariladi. Mavsum davomida tarqatib bo'lmaydi.</div>
           <button class="btn btn--ghost tb-danger-btn" data-tb="dissolve">Teamni tarqatish</button>`
        : `<button class="btn btn--ghost tb-danger-btn" data-tb="leave">Teamdan chiqish</button>`}
    </details>`;
}

document.addEventListener("click", (e) => {
  const tog = e.target.closest ? e.target.closest("#tb-root [data-tb-lutog]") : null;
  if (tog) { e.preventDefault(); e.stopPropagation(); void tbLineupToggle(tog); return; }
  const tile = e.target.closest ? e.target.closest("#tb-root [data-tb-sec]") : null;
  if (!tile || !TB.me || !TB.me.team) return;
  TB.mySec = tile.dataset.tbSec;
  if (typeof tbRerenderMyTeam === "function") tbRerenderMyTeam();
  document.querySelector("#tb-root .tb-panel")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
});
