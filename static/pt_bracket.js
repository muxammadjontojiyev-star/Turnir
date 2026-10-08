// =============================================================
//  pt_bracket.js — SHAXSIY turnir: Reyting > "Setka" (2026-10-08)
//  Admin so'rovi: finalli turnirlarda (ChL / YeL / JCh / erkin) rasmiy ChL setkasi kabi setka.
//  Rasmiy naqsh va klasslar (cl_playoff.js clpoRenderBracket, .wc-bracket-*): ikki tomonlama
//  setka, markazda kubok + final + chempion, kataklar oldindan (bo'sh — "—"), SVG chiziqlar.
//  Juftlik: pt_matches.round = juftlik raqami (1 dan), keyingi bosqich juftligi = floor(i/2).
//  Ikki o'yinli juftlikda (erkin 2 doira) har o'yin hisobi alohida katakda (rasmiy kabi).
//  ChL/YeL "pley-off raundi" (po) — setka ustida alohida ro'yxat (rasmiy pley-in kabi).
//  Global: PT, PTT, escHtml, ptTeamBadge, ptTrophySrc, PT_STAGE_ORDER.
// =============================================================

const PT_BR_FIRST = { 64: "r64", 32: "r32", 16: "r16", 8: "qf", 4: "semi", 2: "final" };
const PT_BR_FORMATS = ["classic", "wc", "cl", "el"];          // finalli formatlar (liga — yo'q)

function ptHasBracket(p) { return !!p && PT_BR_FORMATS.includes(p.format || "classic"); }

// Setka bosqichlari: birinchi bosqichdan finalgacha [{stage, count}]
function ptBracketStages(size) {
  const order = ["r64", "r32", "r16", "qf", "semi", "final"];
  const first = PT_BR_FIRST[size] || "semi";
  return order.slice(order.indexOf(first)).map((s, i) => ({ stage: s, count: Math.max(1, (size >> 1) >> i) }));
}

// Juftlik (bosqich, 0-indeks): o'yinlar (leg tartibida); bo'sh bo'lsa — skelet
function ptBracketTie(p, stage, i) {
  const rows = (p.knockout || []).filter(m => m.stage === stage && m.round === i + 1)
    .sort((a, b) => (a.leg || 1) - (b.leg || 1));
  if (!rows.length) return { stage, i, rows: [], a: null, b: null, winner: null };
  const l1 = rows[0];
  const a = { id: l1.player1_id, user: l1.p1_username, nick: l1.p1_name, team: l1.p1_team };
  const b = { id: l1.player2_id, user: l1.p2_username, nick: l1.p2_name, team: l1.p2_team };
  const done = rows.every(m => m.status === "confirmed" && m.score1 != null);
  const goals = uid => rows.reduce((s, m) => s + (m.player1_id === uid ? m.score1 : m.score2), 0);
  const winner = done ? (goals(a.id) > goals(b.id) ? a.id : goals(b.id) > goals(a.id) ? b.id : null) : null;
  return { stage, i, rows, a, b, winner };
}

function ptBracketSideHtml(tie, who, mirror) {
  const pl = tie[who];
  if (!pl || !pl.id) {
    const empty = `<span class="wc-bracket-flag"></span><span class="wc-bracket-name pt-br-tbd">—</span>`;
    return `<div class="wc-bracket-side">${empty}</div>`;
  }
  // Har o'yin hisobi alohida katakda (shu o'yinchi nuqtai nazaridan); tasdiqlanmagan — "–"
  const cells = (tie.rows.length ? tie.rows : [null]).map(m => {
    const v = m && m.status === "confirmed" && m.score1 != null ? (m.player1_id === pl.id ? m.score1 : m.score2) : "–";
    return `<span class="clpo-leg-score">${v}</span>`;
  }).join("");
  const score = `<span class="wc-bracket-score clpo-leg-scores">${cells}</span>`;
  const name = `<span class="wc-bracket-name">${escHtml(pl.team || (pl.user ? "@" + pl.user : pl.nick || ""))}</span>`;
  const badge = `<span class="wc-bracket-flag">${pl.team ? ptTeamBadge(pl.team, "pt-br-logo") : ""}</span>`;
  const won = tie.winner && tie.winner === pl.id;
  const meCls = pl.id === PT.meId ? " pt-br-me" : "";
  return `<div class="wc-bracket-side clpo-side--clickable${won ? " winner" : ""}${meCls}" data-pt-player="${pl.id}"
      title="${escHtml(pl.user ? "@" + pl.user : pl.nick || "")}">${mirror ? score + name + badge : badge + name + score}</div>`;
}

function ptBracketCardHtml(tie, side) {
  const mirror = side === "right";
  return `<div class="wc-bracket-card wc-bracket-card--${mirror ? "right" : "left"}" data-br-round="${tie.stage}"
      data-br-pos="${tie.i}" data-br-side="${side}">${ptBracketSideHtml(tie, "a", mirror)}${ptBracketSideHtml(tie, "b", mirror)}</div>`;
}

function ptStageLabel(s) { return s === "final" ? PTT("pt_stage_final") : PTT(`pt_stage_${s}`); }

function ptBracketHtml(t, p) {
  PT.meId = p.me_id;
  const size = p.bracket_size || 4;
  const stages = ptBracketStages(size);
  const leftCols = [], rightCols = [];
  stages.filter(s => s.stage !== "final").forEach(({ stage, count }) => {
    const ties = Array.from({ length: count }, (_, i) => ptBracketTie(p, stage, i));
    const half = Math.ceil(count / 2), label = `<div class="wc-bracket-round-label">${escHtml(ptStageLabel(stage))}</div>`;
    leftCols.push(`<div class="wc-bracket-col">${label}${ties.slice(0, half).map(x => ptBracketCardHtml(x, "left")).join("")}</div>`);
    rightCols.unshift(`<div class="wc-bracket-col">${label}${ties.slice(half).map(x => ptBracketCardHtml(x, "right")).join("")}</div>`);
  });
  const trophy = typeof ptTrophySrc === "function" ? ptTrophySrc(t) : null;
  const ch = p.champion;
  const champ = ch ? `<div class="pt-br-champ">${ch.team_name ? ptTeamBadge(ch.team_name, "pt-br-champ-logo") : ""}
      <div class="pt-br-champ-name">🏆 ${escHtml(ch.username ? "@" + ch.username : ch.nickname || "")}</div>
      <div class="pt-br-champ-label">${escHtml(PTT("pt_champion_title"))}</div></div>` : "";
  const center = `<div class="wc-bracket-col wc-bracket-col--center">
      ${trophy ? `<img src="${escHtml(trophy)}" alt="" class="wc-bracket-trophy">` : `<div class="pt-br-cup">🏆</div>`}
      <div class="wc-bracket-round-label wc-bracket-final-label">${escHtml(PTT("pt_stage_final"))}</div>
      ${ptBracketCardHtml(ptBracketTie(p, "final", 0), "center")}${champ}</div>`;
  const started = (p.knockout || []).length > 0;
  const note = started ? "" : `<div class="pt-br-note">${escHtml(PTT(p.single_table ? "pt_br_wait_table" : "pt_br_wait_groups"))}</div>`;
  return `${ptBracketPoHtml(p)}${note}<div class="section-label pt-label">${escHtml(PTT("pt_br_title"))}</div>
    <div class="wc-bracket-scroll pt-bracket"><div class="wc-bracket-inner">
      <svg class="wc-bracket-lines" preserveAspectRatio="none"></svg>
      <div class="wc-bracket wc-bracket--two-sided">${leftCols.join("")}${center}${rightCols.join("")}</div>
    </div></div>`;
}

// ChL/YeL pley-off raundi (Q+1..3Q) — setka ustida ro'yxat
function ptBracketPoHtml(p) {
  const n = (p.knockout || []).filter(m => m.stage === "po" && (m.leg || 1) === 1).length;
  if (!n) return "";
  const cards = Array.from({ length: n }, (_, i) => ptBracketCardHtml(ptBracketTie(p, "po", i), "left")).join("");
  return `<div class="section-label pt-label">${escHtml(PTT("pt_stage_po"))}</div><div class="pt-br-po">${cards}</div>`;
}

// Bog'lovchi chiziqlar (rasmiy clpoDrawBracketLines naqshi): juftlik -> keyingi bosqich floor(i/2)
function ptDrawBracketLines() {
  const inner = document.querySelector("#pt-root .pt-bracket .wc-bracket-inner");
  const svg = inner && inner.querySelector(".wc-bracket-lines");
  const br = inner && inner.querySelector(".wc-bracket");
  if (!svg || !br) return;
  const W = br.scrollWidth, H = br.scrollHeight, base = br.getBoundingClientRect(), map = {};
  svg.setAttribute("width", W); svg.setAttribute("height", H); svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = "";
  br.querySelectorAll(".wc-bracket-card[data-br-round]").forEach(c => {
    const r = c.getBoundingClientRect();
    map[`${c.dataset.brRound}:${c.dataset.brPos}:${c.dataset.brSide}`] = { top: r.top - base.top, left: r.left - base.left, w: r.width, h: r.height };
  });
  const NS = "http://www.w3.org/2000/svg";
  const line = (x1, y1, x2, y2) => {
    const path = document.createElementNS(NS, "path"), mid = (x1 + x2) / 2;
    path.setAttribute("d", `M ${x1} ${y1} H ${mid} V ${y2} H ${x2}`);
    path.setAttribute("fill", "none"); path.setAttribute("stroke", "rgba(255,255,255,0.22)"); path.setAttribute("stroke-width", "2");
    svg.appendChild(path);
  };
  const order = ["r64", "r32", "r16", "qf", "semi", "final"];
  Object.entries(map).forEach(([key, cur]) => {
    const [stage, pos, side] = key.split(":");
    if (side === "center" || !order.includes(stage)) return;
    const next = order[order.indexOf(stage) + 1], np = Math.floor(+pos / 2);
    const nxt = map[`${next}:${np}:${side}`] || map[`${next}:${np}:center`];
    if (!nxt) return;
    if (side === "left") line(cur.left + cur.w, cur.top + cur.h / 2, nxt.left, nxt.top + nxt.h / 2);
    else line(cur.left, cur.top + cur.h / 2, nxt.left + nxt.w, nxt.top + nxt.h / 2);
  });
}

function ptBindBracket() {
  if (!document.querySelector("#pt-root .pt-bracket")) return;
  requestAnimationFrame(ptDrawBracketLines);
  setTimeout(ptDrawBracketLines, 250);
}
