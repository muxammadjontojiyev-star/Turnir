// =============================================================
//  tb_season.js — "TEAMLAR JANGI": Jang va Jadval tablari (2026-10-16, 2-bosqich)
//  Jang  — mening ochiq 1v1 o'yinim: natija kiritish / raqib natijasini tasdiqlash,
//          raqibga Telegram'da yozish, teamimning shu turdagi bahsi (barcha juftliklar).
//  Jadval — divizion tanlash, jadval (O·G·D·M·1v1·Ochko), turlar bo'yicha bahslar.
//  Backend: /tb/season, /tb/my-games, /tb/season/table, /tb/season/fixtures, /tb/game/*.
//  tb.js dan KEYIN ulanadi. Global: TB, tbRender, tbErr, apiFetch, escHtml, showToast.
// =============================================================

const TBS = { info: null, games: null, division: null, round: null };

// 2026-10-16: emoji o'rniga galereyadan logo (tb_logo.js), logo yo'q bo'lsa — emoji
function tbsTeam(name, emoji, id, ver) { return `${tbLogo("team", id, ver, emoji, "tb-logo--sm")} ${escHtml(name || "?")}`; }

// 2026-10-18: format belgisi (UCL) va pley-off bosqichidami
function tbsFmtTag(s) { return s && s.format === "ucl" ? ` <span class="tb-fmt-tag">UCL</span>` : ""; }
function tbsIsKo(s, rnd) { return !!(s && s.format === "ucl" && (rnd || s.current_round) > (s.ucl_rounds || 0)); }

function tbsSeasonLine(s) {
  if (!s) return "Mavsum hali e'lon qilinmagan";
  if (s.status === "drawn") return `${s.number}-mavsum · qur'a o'tkazildi, turlar tez orada boshlanadi`;
  if (s.status === "finished") return `${s.number}-mavsum yakunlangan`;
  const r = Math.min(s.current_round, s.total_rounds);
  return `${s.number}-mavsum · ${r}/${s.total_rounds}-tur · deadline 23:30`;
}

async function tbsLoadInfo() {
  TBS.info = await apiFetch("/tb/season" + tbLeagueQ());
  return TBS.info;
}

// ------------------------------------------------------------------ JANG
async function tbBattleLoad() {
  tbRender(`<div class="empty-state">Yuklanmoqda…</div>`);
  try {
    const [info, my] = await Promise.all([tbsLoadInfo(), apiFetch("/tb/my-games")]);
    TBS.games = my.games || [];
    TBS.me = my.user_id;
    try { TBS.unread = (await apiFetch("/tb/matches/unread")).by_match || {}; } catch (_) { TBS.unread = {}; }
    let fixtureHtml = "";
    const s = info.season;
    if (s && s.status === "running" && info.my_division && s.current_round <= s.total_rounds) {
      const div = tbsIsKo(s) ? 0 : info.my_division;            // 2026-10-18: pley-off bahslari — division 0
      const d = await apiFetch(`/tb/season/fixtures?division=${div}&round=${s.current_round}${tbLeagueQ("&")}`);
      const mine = (d.fixtures || []).find(f => f.home_team_id === info.my_team_id || f.away_team_id === info.my_team_id);
      fixtureHtml = mine ? `<div class="section-label">TEAMIMNING BAHSI (${s.current_round}-TUR)</div>${tbsFixtureHtml(mine, true)}`
        : `<div class="tb-note">Bu turda teamingiz dam oladi (raqib yo'q).</div>`;
    }
    const gamesHtml = TBS.games.length ? TBS.games.map(tbsGameCardHtml).join("")
      : `<div class="card tb-hint tb-hint--center">${s && s.status === "running"
          ? "Hozir ochiq o'yiningiz yo'q. Asosiy tarkibga kirgan o'yinchilar juftlanadi."
          : "O'yinlar mavsum boshlangach shu yerda chiqadi."}</div>`;
    tbRender(`<div class="card tb-season-line">${ICON.get("swords", 16)} ${escHtml(tbsSeasonLine(s))}${tbsFmtTag(s)}</div>
      <div class="section-label">MENING O'YINIM</div>${gamesHtml}${fixtureHtml}`);
  } catch (e) {
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div>`);
  }
}

function tbsGameCardHtml(g) {
  const iAmHome = g.home_user_id === TBS.me;
  const myTeam = iAmHome ? tbsTeam(g.home_team, g.home_emoji, g.home_team_id, g.home_logo_ver) : tbsTeam(g.away_team, g.away_emoji, g.away_team_id, g.away_logo_ver);
  const opTeam = iAmHome ? tbsTeam(g.away_team, g.away_emoji, g.away_team_id, g.away_logo_ver) : tbsTeam(g.home_team, g.home_emoji, g.home_team_id, g.home_logo_ver);
  const opUser = iAmHome ? g.away_username : g.home_username;
  const opName = opUser ? "@" + opUser : (iAmHome ? g.away_nick : g.home_nick);
  const mine = iAmHome ? g.score1 : g.score2, theirs = iAmHome ? g.score2 : g.score1;
  let body;
  if (g.status === "confirmed") {
    body = `<div class="tb-g-final">${mine} : ${theirs}</div><div class="tb-hint tb-hint--center">✅ Tasdiqlangan</div>`;
  } else if (g.status === "awaiting_confirmation" && g.submitted_by === TBS.me) {
    body = `<div class="tb-g-final">${mine} : ${theirs}</div><div class="tb-hint tb-hint--center">⏳ Raqib tasdig'i kutilmoqda</div>`;
  } else if (g.status === "awaiting_confirmation") {
    body = `<div class="tb-note">Raqib natija kiritdi: <b>${mine} : ${theirs}</b> (sizning hisobingiz birinchi)</div>
      <div class="tb-g-acts">
        <button class="btn btn--primary" data-tbs-confirm="${g.id}" data-accept="1">✅ Tasdiqlash</button>
        <button class="btn btn--ghost" data-tbs-confirm="${g.id}" data-accept="0">❌ Rad etish</button>
      </div>`;
  } else {
    body = `<div class="tb-g-score">
        <div><span>Siz</span><input class="score-input" type="number" inputmode="numeric" min="0" max="30" value="0" id="tbs-m-${g.id}"></div>
        <b>:</b>
        <div><span>Raqib</span><input class="score-input" type="number" inputmode="numeric" min="0" max="30" value="0" id="tbs-o-${g.id}"></div>
      </div>
      <button class="btn btn--primary" data-tbs-submit="${g.id}">Natijani yuborish</button>`;
  }
  // 3-bosqich: ilova ichidagi chat (rasm yuborish bilan) + Telegram'da yozish
  const unread = (TBS.unread || {})[g.id] || 0;
  const tg = `<span class="tb-g-btns">
      <button class="tb-mini" data-tbs-chat="${g.id}" data-name="${escHtml(opName || "Raqib")}">💬 Chat${unread ? ` <i class="tb-unread">${unread}</i>` : ""}</button>
      ${opUser ? `<button class="tb-mini" data-tbs-tg="${escHtml(opUser)}">✈️ Telegram</button>` : ""}
    </span>`;
  return `<div class="card tb-game">
      <div class="tb-g-head"><span>${g.round}-tur · ${g.slot}-juftlik</span>${tg}</div>
      <div class="tb-g-vs">
        <div class="tb-g-side"><b>Siz</b><span>${myTeam}</span></div>
        <div class="tb-g-x">VS</div>
        <div class="tb-g-side"><b>${escHtml(opName || "—")}</b><span>${opTeam}</span></div>
      </div>
      ${body}
    </div>`;
}

function tbsFixtureHtml(f, open) {
  const score = f.status === "scheduled" ? "—" : `${f.home_wins} : ${f.away_wins}`;
  const tech = f.technical ? `<div class="tb-hint tb-hint--center">Texnik natija: ${
    f.technical === "both" ? "ikkala teamning tarkibi yetmadi" : (f.technical === "home" ? f.home_team : f.away_team) + " tarkibi yetmadi"}</div>` : "";
  const games = (f.games || []).map(g => {
    const sc = g.status === "confirmed" ? `${g.score1}:${g.score2}` : g.status === "awaiting_confirmation" ? "⏳" : "–";
    const gid = TB.me && tbCanManageCur() ? `<i class="tb-pair-id">#${g.id}</i>` : "";
    return `<div class="tb-pair">${gid}<span>${escHtml(g.home)}</span><b>${sc}</b><span>${escHtml(g.away)}</span></div>`;
  }).join("");
  return `<details class="card tb-fx"${open ? " open" : ""}>
      <summary class="tb-fx-head">
        <span class="tb-fx-team">${tbsTeam(f.home_team, f.home_emoji, f.home_team_id, f.home_logo_ver)}</span>
        <span class="tb-fx-score${f.status === "finished" ? " done" : ""}">${score}</span>
        <span class="tb-fx-team tb-fx-team--away">${tbsTeam(f.away_team, f.away_emoji, f.away_team_id, f.away_logo_ver)}</span>
      </summary>
      ${tech}${games ? `<div class="tb-pairs">${games}</div>` : (f.status === "scheduled" ? `<div class="tb-hint tb-hint--center">Juftliklar tur ochilganda tuziladi</div>` : "")}
    </details>`;
}

// ------------------------------------------------------------------ JADVAL
async function tbTableLoad() {
  tbRender(`<div class="empty-state">Yuklanmoqda…</div>`);
  try {
    const info = await tbsLoadInfo();
    const s = info.season;
    if (!s) { tbRender(`<div class="empty-state">Mavsum hali e'lon qilinmagan</div>`); return; }
    const divs = info.divisions || [];
    if (!TBS.division || !divs.some(d => d.division === TBS.division)) TBS.division = info.my_division || (divs[0] && divs[0].division);
    if (!TBS.round) TBS.round = Math.max(1, Math.min(s.current_round || 1, tbsLastTableRound(s)));
    await tbsRenderTable();
  } catch (e) {
    tbRender(`<div class="empty-state">${escHtml(tbErr(e))}</div>`);
  }
}

async function tbsRenderTable() {
  const s = TBS.info.season, divs = TBS.info.divisions || [];
  const ucl = s.format === "ucl";
  TBS.round = Math.min(TBS.round, tbsLastTableRound(s));
  const [t, fx, ko] = await Promise.all([
    apiFetch(`/tb/season/table?division=${TBS.division}${tbLeagueQ("&")}`),
    apiFetch(`/tb/season/fixtures?division=${TBS.division}&round=${TBS.round}${tbLeagueQ("&")}`),
    ucl ? apiFetch("/tb/season/ko" + tbLeagueQ()) : Promise.resolve(null),   // 2026-10-18: pley-off
  ]);
  const myTeam = TBS.info.my_team_id;
  // 3-bosqich: ko'tarilish (yashil) / tushish (qizil) zonalari
  const promo = TBS.info.promo || 0, lastDiv = divs.length ? divs[divs.length - 1].division : 1;
  const nRows = (t.table || []).length;
  const zone = (i) => {
    if (ucl) return i < (s.ucl_qualify || 0) ? " tb-zone-up" : "";
    if (!promo || nRows < 2 * promo) return "";
    if (TBS.division > 1 && i < promo) return " tb-zone-up";
    if (TBS.division < lastDiv && i >= nRows - promo) return " tb-zone-down";
    return "";
  };
  const rows = (t.table || []).map((r, i) => `
    <tr class="${r.team_id === myTeam ? "is-me" : ""}${zone(i)}">
      <td>${i + 1}</td>
      <td class="tb-tt-name">${tbsTeam(r.name, r.emoji, r.team_id, r.logo_ver)}</td>
      <td>${r.played}</td><td>${r.wins}</td><td>${r.draws}</td><td>${r.losses}</td>
      <td>${r.gw - r.gl >= 0 ? "+" : ""}${r.gw - r.gl}</td>
      <td class="pts">${r.points}</td>
    </tr>`).join("");
  const chips = divs.map(d => `<button class="tb-chip${d.division === TBS.division ? " active" : ""}" data-tbs-div="${d.division}">${d.division}-divizion <b>${d.teams}</b></button>`).join("");
  tbRender(`
    <div class="card tb-season-line">${ICON.get("swords", 16)} ${escHtml(tbsSeasonLine(s))}${tbsFmtTag(s)}</div>
    ${ucl ? `<div class="section-label">LIGA BOSQICHI</div>` : `<div class="tb-chips">${chips}</div>`}
    <div class="card card--table tb-table-card">
      <table class="rating-table tb-table">
        <thead><tr><th>#</th><th>Team</th><th>O</th><th>G</th><th>D</th><th>M</th><th title="1v1 g'alabalar farqi">1v1</th><th>Och</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <div class="tb-hint">Ochko: g'alaba 3 · durang 1. Teng bo'lsa: 1v1 g'alabalar farqi → gol farqi.</div>
    ${ucl ? `<div class="tb-zone-legend"><span><i class="tb-zl tb-zl--up"></i>Pley-offga chiqadi (${s.ucl_qualify})</span></div>` : ""}
    ${!ucl && divs.length > 1 ? `<div class="tb-zone-legend">${TBS.division > 1 ? `<span><i class="tb-zl tb-zl--up"></i>Yuqori divizionga ko'tariladi (${promo})</span>` : ""}
      ${TBS.division < lastDiv ? `<span><i class="tb-zl tb-zl--down"></i>Quyi divizionga tushadi (${promo})</span>` : ""}</div>` : ""}
    <div class="tb-round-nav">
      <button class="tb-mini" data-tbs-round="-1" ${TBS.round <= 1 ? "disabled" : ""}>◀</button>
      <b>${TBS.round}-tur</b>
      <button class="tb-mini" data-tbs-round="1" ${TBS.round >= tbsLastTableRound(s) ? "disabled" : ""}>▶</button>
    </div>
    ${(fx.fixtures || []).map(f => tbsFixtureHtml(f, false)).join("") || `<div class="tb-hint tb-hint--center">Bu turda bahs yo'q</div>`}
    ${ko && typeof tbUclBracketHtml === "function" ? tbUclBracketHtml(ko) : ""}`);
}

// Jadval sahifasidagi tur tanlash chegarasi: UCL'da faqat liga bosqichi turlari (pley-off — alohida blokda)
function tbsLastTableRound(s) {
  return Math.max(1, s.format === "ucl" ? (s.ucl_rounds || 1) : (s.total_rounds || 1));
}

// ------------------------------------------------------------------ amallar
async function tbsPost(path, body, okMsg, btn) {
  if (btn) btn.disabled = true;
  try {
    await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
    if (okMsg) tbToast(okMsg);
    await tbBattleLoad();
  } catch (e) {
    tbToast("❌ " + tbErr(e));
    if (btn) btn.disabled = false;
  }
}

document.addEventListener("click", (e) => {
  if (!e.target.closest) return;
  const root = e.target.closest("#tb-root");
  if (!root) return;
  const sub = e.target.closest("[data-tbs-submit]");
  if (sub) {
    const id = +sub.dataset.tbsSubmit;
    const m = document.getElementById(`tbs-m-${id}`)?.value, o = document.getElementById(`tbs-o-${id}`)?.value;
    if (m === "" || o === "") { tbToast("Hisobni kiriting"); return; }
    if (!tbConfirm(`Natija: Siz ${m} : ${o} Raqib. Yuborilsinmi?`)) return;
    void tbsPost("/tb/game/submit", { game_id: id, my_score: +m, opp_score: +o }, "✅ Yuborildi — raqib tasdiqlaydi", sub);
    return;
  }
  const cf = e.target.closest("[data-tbs-confirm]");
  if (cf) {
    const accept = cf.dataset.accept === "1";
    if (!accept && !tbConfirm("Natija rad etilsinmi? Raqib qayta kiritadi.")) return;
    void tbsPost("/tb/game/confirm", { game_id: +cf.dataset.tbsConfirm, accept }, accept ? "✅ Tasdiqlandi" : "Rad etildi", cf);
    return;
  }
  const ch = e.target.closest("[data-tbs-chat]");
  if (ch) {
    if (typeof openWebChat === "function") openWebChat(+ch.dataset.tbsChat, ch.dataset.name || "Raqib", "/tb/matches");
    return;
  }
  const tg = e.target.closest("[data-tbs-tg]");
  if (tg) {
    const url = `https://t.me/${encodeURIComponent(tg.dataset.tbsTg)}`;
    const w = window.Telegram?.WebApp;
    if (w?.openTelegramLink) w.openTelegramLink(url); else window.open(url, "_blank");
    return;
  }
  const dv = e.target.closest("[data-tbs-div]");
  if (dv) { TBS.division = +dv.dataset.tbsDiv; void tbsRenderTable().catch(err => tbToast("❌ " + tbErr(err))); return; }
  const rn = e.target.closest("[data-tbs-round]");
  if (rn) { TBS.round += +rn.dataset.tbsRound; void tbsRenderTable().catch(err => tbToast("❌ " + tbErr(err))); }
});
