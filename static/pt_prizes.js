// =============================================================
//  pt_prizes.js — SHAXSIY turnir Sovrinlar sahifasi (2026-10-11)
//  Admin so'rovi: rasmiy turnir Sovrinlar sahifasi bilan bir xil bo'lsin —
//    1) Oltin Butsa — eng ko'p gol (to'purarlar 1-o'rni, ptScorerRows — pley-off gollari ham)
//    2) Oltin To'p — eng ko'p ochko (barcha jadvallar bo'yicha; rasmiy qoida: ochko > gol > farq)
//    3) Liga kubogi — tanlangan liga (LIGA BO'YICHA filtri) kubogi va jadval 1-o'rni;
//       boshqa formatlarda — turnir kubogi va chempion (avvalgi karta, final o'yini bilan).
//  Rasmiy sahifaning CSS klasslari (card--prize, prize-*) — ko'rinish bir xil.
//  Ma'lumot: o'yin API'si (p.standings, p.knockout, p.champion) — backend o'zgarmadi.
//  Global: PT, PTT, escHtml, ptLgT, ptTeamIndex, ptScorerRows, ptTrophySrc, ptUserLabel,
//          ptTeamBadge, ptMatchCardHtml, LEAGUE_TROPHIES, renderLeagueLogo, ptRenderDetailTabs.
// =============================================================

// Sovrin egasi: 1-qator @username (Telegram havolasi) yoki nik, 2-qator klub/terma logosi + nomi
function ptPrizeHolderHtml(u, suffix) {
  if (!u) return { holder: "—", club: "" };
  const name = u.username
    ? `<a class="prize-holder-link" href="https://t.me/${escHtml(u.username)}" target="_blank">@${escHtml(u.username)}</a>`
    : `<span class="prize-holder-name">${escHtml(u.nickname || "")}</span>`;
  const info = (u.team_name && typeof ptTeamIndex === "function" && ptTeamIndex()[u.team_name]) || {};
  const club = !u.team_name ? ""
    : info.logo ? `<img src="${escHtml(info.logo)}" alt="" class="prize-club-logo" onerror="this.style.display='none'"><span class="prize-club-name">${escHtml(u.team_name)}</span>`
    : `${info.flag ? `<span class="prize-club-flag">${info.flag}</span>` : ""}<span class="prize-club-name">${escHtml(u.team_name)}</span>`;
  return { holder: name + (suffix ? `<span class="prize-goals"> — ${escHtml(suffix)}</span>` : ""), club };
}

function ptPrizeCardHtml({ img, nameKey, nameDef, descKey, descDef, title, user, suffix, tone }) {
  const h = ptPrizeHolderHtml(user, suffix);
  return `<div class="card card--prize card--prize--${tone || "gold"}">
      <div class="prize-icon">${img ? `<img src="${escHtml(img)}" alt="" class="prize-icon-img" onerror="this.outerHTML='🏆'">` : "🏆"}</div>
      <div class="prize-info">
        <div class="prize-name">${escHtml(title || ptLgT(nameKey, nameDef))}</div>
        <div class="prize-desc">${escHtml(ptLgT(descKey, descDef))}</div>
        <div class="prize-holder">${h.holder}</div>
        <div class="prize-club">${h.club}</div>
      </div></div>`;
}

// Barcha jadval qatorlari (har ishtirokchi bitta jadvalda)
function ptAllTableRows(p) {
  return Object.values(p.standings || {}).flat();
}

function ptGoldenBoot(p) {
  const top = (typeof ptScorerRows === "function" ? ptScorerRows(p) : [])[0];
  return top && top.goals > 0 ? top : null;
}

function ptGoldenBall(p) {
  const rows = ptAllTableRows(p).filter(r => r.played > 0);
  if (!rows.length) return null;
  rows.sort((a, b) => b.points - a.points || b.goals_for - a.goals_for || b.goal_diff - a.goal_diff);
  return rows[0].points > 0 ? rows[0] : null;
}

function ptTabPrizesPage(t, p) {
  if (!p) return `<div class="empty-state">${escHtml(PTT("pt_prize_hint"))}</div>`;
  const boot = ptGoldenBoot(p);
  const ball = ptGoldenBall(p);
  const goalsWord = ptLgT("goals", "gol");
  let html = `<div class="section-label">${escHtml(ptLgT("prizes_title", "SOVRINLAR"))}</div>`
    + ptPrizeCardHtml({ img: "golden-boot.png?v=20260628c20", nameKey: "golden_boot", nameDef: "Oltin Butsa",
        descKey: "golden_boot_desc", descDef: "Eng ko'p gol urgan o'yinchi", user: boot,
        suffix: boot ? `${boot.goals} ${goalsWord}` : "" })
    + ptPrizeCardHtml({ img: "golden-ball.png?v=20260628c20", nameKey: "golden_ball", nameDef: "Oltin To'p",
        descKey: "golden_ball_desc", descDef: "Turnir g'olibi", user: ball });

  const leagues = p.format === "league" ? (p.leagues || []) : [];
  if (leagues.length) {
    if (!PT.prizeLeague || !leagues.includes(PT.prizeLeague)) PT.prizeLeague = leagues[0];
    const lg = PT.prizeLeague;
    const leader = ((p.standings || {})[lg] || [])[0];
    const champ = leader && leader.played > 0 ? leader : null;
    html += ptPrizeCardHtml({ img: (typeof LEAGUE_TROPHIES !== "undefined" && LEAGUE_TROPHIES[lg]) || null,
        title: `${lg} — ${ptLgT("league_trophy", "Liga Kubogi")}`, descKey: "league_trophy_desc",
        descDef: "Liga chempioni", user: champ, tone: "cyan" });
    if (leagues.length > 1) {
      html += `<div class="section-label">${escHtml(ptLgT("by_league", "LIGA BO'YICHA"))}</div>
        <div class="tab-filter">${leagues.map(l => `<button class="tab-btn${l === lg ? " active" : ""}" data-pt-prize-lg="${escHtml(l)}">${typeof renderLeagueLogo === "function" ? renderLeagueLogo(l, "tab-league-logo") : ""}<span>${escHtml(l)}</span></button>`).join("")}</div>`;
    }
    return html;
  }
  // Boshqa formatlar: turnir kubogi + chempion (rasmiy kubok kartasi ko'rinishida) va final o'yini
  const cup = typeof ptTrophySrc === "function" ? ptTrophySrc(t) : null;
  html += ptPrizeCardHtml({ img: cup, title: PTT("pt_prize_title"), descKey: "_none",
      descDef: PTT(p.champion ? "pt_champion_title" : "pt_prize_hint"), user: p.champion || null, tone: "cyan" });
  const final = (p.knockout || []).find(m => m.stage === "final");
  if (final && typeof ptMatchCardHtml === "function") {
    html += `<div class="section-label pt-label">${escHtml(PTT("pt_stage_final_h"))}</div>`
      + ptMatchCardHtml(final, p, final.player1_id === p.me_id || final.player2_id === p.me_id);
  }
  return html;
}

function ptBindPrizes() {
  document.querySelectorAll("#pt-root [data-pt-prize-lg]").forEach(b => b.addEventListener("click", () => {
    PT.prizeLeague = b.dataset.ptPrizeLg;
    ptRenderDetailTabs();
  }));
}
