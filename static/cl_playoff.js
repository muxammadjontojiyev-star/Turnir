// ===== ChL PLAY-OFF (2026-07-20) =====
// Setka — Reyting sahifasida (WC bracket naqshi, wc-bracket-* CSS qayta ishlatiladi).
// Har juftlik UY+MEHMON (2 o'yin), final — 1 o'yin. Kubok — ChL kubogi (SVG).
// O'yinlar Profil sahifasida ("PLAY-OFF O'YINLARIM") kiritiladi/tasdiqlanadi.

const CLPO = {
  bracket: null,      // /cl/playoff/bracket javobi
  my: null,           // /cl/playoff/my-matches javobi
  activeMatch: null,  // modal ochilgan o'yin (obyekt)
};

const CLPO_ROUND_NAMES = { r16: "1/8 final", r8: "1/4 final", r4: "1/2 final", final: "Final" };
const CLPO_SIDE_ROUNDS = ["r16", "r8", "r4"];

// 2026-07-21: kubok — Sovrinlar sahifasidagi RASM (cl-trophy.png, clRenderPrizes
// bilan bir xil fayl); .wc-bracket-trophy klassi o'lcham/animatsiya beradi.
function clpoTrophySvg() {
  return `<img src="cl-trophy.png" alt="Chempionlar ligasi kubogi" class="wc-bracket-trophy" />`;
}

// ---- SETKA (Reyting sahifasi) ----

async function clpoLoadBracket() {
  const box = document.getElementById("cl-po-bracket-box");
  if (!box) return;
  try {
    CLPO.bracket = await apiFetch("/cl/playoff/bracket");
  } catch (_) { CLPO.bracket = null; }
  if (!CLPO.bracket || !CLPO.bracket.started) {
    box.innerHTML = `<div class="card">Play-off hali boshlanmagan. Guruh bosqichi tugagach, setka shu yerda paydo bo'ladi.</div>`;
    return;
  }
  box.innerHTML = clpoRenderBracket(CLPO.bracket);
  // 2026-07-21: kataklarni bog'lovchi chiziqlar (WC wcDrawBracketLines naqshi).
  // Layout o'lchamlari tayyor bo'lishi uchun keyingi kadr + zaxira kechikish.
  requestAnimationFrame(clpoDrawBracketLines);
  setTimeout(clpoDrawBracketLines, 250);
}

// Juftlikning bir tomoni (klub + @user + 2 o'yin hisobi + agregat)
function clpoTieSide(tie, side, mirror) {
  const p = side === "a" ? tie.a : tie.b;
  const won = tie.winner_id && p.user_id === tie.winner_id;
  const name = p.username ? "@" + p.username : (p.nickname || "—");
  const badge = p.club_name ? clClubBadge(p.club_name, 18) : "";
  // Hisoblar: sideA — leg1'da mehmon (score2), leg2'da uyda (score1)
  const l1 = tie.leg1, l2 = tie.leg2;
  const s = (m, key) => (m && m.status === "confirmed") ? m[key] : null;
  const legTxt = (tie.round === "final")
    ? [s(l1, side === "a" ? "score1" : "score2")]
    : [s(l1, side === "a" ? "score2" : "score1"), s(l2, side === "a" ? "score1" : "score2")];
  const scores = p.user_id ? legTxt.map(v => v === null ? "–" : v).join("·") : "";
  const agg = (side === "a" ? tie.agg_a : tie.agg_b);
  const aggTxt = agg === null || agg === undefined ? "" : `<b>${agg}</b>`;
  const inner = mirror
    ? `<span class="wc-bracket-score">${aggTxt || scores}</span><span class="wc-bracket-name">${escHtml(name)}</span><span class="wc-bracket-flag">${badge}</span>`
    : `<span class="wc-bracket-flag">${badge}</span><span class="wc-bracket-name">${escHtml(name)}</span><span class="wc-bracket-score">${aggTxt || scores}</span>`;
  return `<div class="wc-bracket-side ${won ? "winner" : ""}" title="O'yinlar: ${scores}">${inner}</div>`;
}

function clpoTieCard(tie, side) {
  const mirror = side === "right";
  const sideCls = mirror ? "wc-bracket-card--right" : "wc-bracket-card--left";
  return `
    <div class="wc-bracket-card ${sideCls}"
         data-br-round="${escHtml(tie.round)}" data-br-pos="${tie.position}" data-br-side="${side}">
      ${clpoTieSide(tie, "a", mirror)}
      ${clpoTieSide(tie, "b", mirror)}
    </div>`;
}

// Har bosqichdagi juftliklar soni (bo'sh bosqichlar ham SKELET sifatida chiziladi —
// 2026-07-21: kubokkacha boradigan barcha kataklar oldindan ko'rinadi, chiziqlar ulanadi)
const CLPO_TIE_COUNTS = { r16: 8, r8: 4, r4: 2, final: 1 };

function clpoGetTie(rounds, rnd, pos) {
  const found = (rounds[rnd] || []).find(t => t.position === pos);
  return found || { round: rnd, position: pos, a: {}, b: {}, leg1: null, leg2: null,
                    agg_a: null, agg_b: null, winner_id: null };
}

function clpoRenderBracket(data) {
  const rounds = data.rounds || {};
  const leftCols = [], rightCols = [];
  for (const rnd of CLPO_SIDE_ROUNDS) {
    const total = CLPO_TIE_COUNTS[rnd];
    const ties = [];
    for (let pos = 0; pos < total; pos++) ties.push(clpoGetTie(rounds, rnd, pos));
    const half = Math.ceil(ties.length / 2);
    const left = ties.slice(0, half), right = ties.slice(half);
    leftCols.push(`<div class="wc-bracket-col">
      <div class="wc-bracket-round-label">${CLPO_ROUND_NAMES[rnd]}</div>
      ${left.map(t => clpoTieCard(t, "left")).join("")}</div>`);
    rightCols.unshift(`<div class="wc-bracket-col">
      <div class="wc-bracket-round-label">${CLPO_ROUND_NAMES[rnd]}</div>
      ${right.map(t => clpoTieCard(t, "right")).join("")}</div>`);
  }
  const finals = [clpoGetTie(rounds, "final", 0)];
  const champ = data.champion;
  const champHtml = champ ? `
    <div class="cl-po-champion">
      ${champ.club_name ? clClubBadge(champ.club_name, 30) : ""}
      <div class="cl-po-champion-name">🏆 ${escHtml(champ.username ? "@" + champ.username : (champ.nickname || ""))}</div>
      <div class="cl-po-champion-label">CHEMPION</div>
    </div>` : "";
  const centerCol = `<div class="wc-bracket-col wc-bracket-col--center">
    ${clpoTrophySvg()}
    <div class="wc-bracket-round-label wc-bracket-final-label">Final</div>
    ${finals.map(t => clpoTieCard(t, "center")).join("")}
    ${champHtml}
  </div>`;
  return `
    <div class="section-label">PLAY-OFF SETKASI</div>
    <div class="wc-bracket-scroll">
      <div class="wc-bracket-inner">
        <svg class="wc-bracket-lines" preserveAspectRatio="none"></svg>
        <div class="wc-bracket wc-bracket--two-sided">
          ${leftCols.join("")}
          ${centerCol}
          ${rightCols.join("")}
        </div>
      </div>
    </div>`;
}

// ---- PROFIL: PLAY-OFF O'YINLARIM ----
// 2026-07-21: dizayn va natija oqimi guruh o'yinlari ("MENING O'YINLARIM",
// clRenderMatchItem) bilan BIR XIL: .cl-match-wrap karta, umumiy #modal-result
// modali (klub logolari + input-score1/2), tasdiqlash — bir bosishda, rad — alohida qator.

async function clpoLoadMyMatches() {
  const box = document.getElementById("cl-po-my-box");
  if (!box) return;
  try {
    CLPO.my = await apiFetch("/cl/playoff/my-matches");
  } catch (_) { CLPO.my = null; }
  if (!CLPO.my || !CLPO.my.started || !CLPO.my.matches.length) { box.innerHTML = ""; return; }
  box.innerHTML = `
    <div class="section-label">PLAY-OFF O'YINLARIM</div>
    <div class="matches-list">${CLPO.my.matches.map(clpoMyMatchItem).join("")}</div>`;
  box.querySelectorAll("[data-clpo-result]").forEach(b =>
    b.addEventListener("click", () => clpoOpenResultModal(parseInt(b.dataset.clpoResult))));
  box.querySelectorAll("[data-clpo-confirm]").forEach(b =>
    b.addEventListener("click", () => void clpoConfirm(parseInt(b.dataset.clpoConfirm), true)));
  box.querySelectorAll("[data-clpo-reject]").forEach(b =>
    b.addEventListener("click", () => void clpoConfirm(parseInt(b.dataset.clpoReject), false)));
}

function clpoLegLabel(m) {
  const r = CLPO_ROUND_NAMES[m.round] || m.round;
  return m.round === "final" ? r : `${r} · ${m.leg}-o'yin`;
}

// Guruh o'yinlari kartasi (clRenderMatchItem) bilan bir xil tuzilma
function clpoMyMatchItem(m) {
  const meId = CLPO.my.me_id;
  const isHome = m.player1_id === meId;                 // player1 = uy egasi
  const mine = m.submitted_by === meId;
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";

  const center = `
    <span class="cl-mc-logo">${clClubBadge(m.p1_club, 26)}</span>
    <span class="match-score">${score}</span>
    <span class="cl-mc-logo">${clClubBadge(m.p2_club, 26)}</span>`;

  let statusCls = "status--pending", statusText = "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  let action = "";
  if (m.status === "pending") {
    action = `<button class="match-action-btn" data-clpo-result="${m.id}">Natija</button>`;
  } else if (m.status === "awaiting_confirmation") {
    action = mine
      ? `<span class="match-waiting">Kutilmoqda</span>`
      : `<button class="match-action-btn" data-clpo-confirm="${m.id}">${ICON.get("check", 16)}</button>`;
  }
  const reject = (m.status === "awaiting_confirmation" && !mine)
    ? `<div class="cl-score-row"><button class="btn" data-clpo-reject="${m.id}">${ICON.get("cross", 15)} Rad etish</button></div>` : "";

  const venue = isHome
    ? `<span class="cl-venue cl-venue--home">UY</span>`
    : `<span class="cl-venue cl-venue--away">MEHMON</span>`;

  // 2-o'yinda 1-o'yin hisobi (agregat konteksti)
  const ctx = (m.leg === 2 && m.other_leg_score1 !== null && m.other_leg_score1 !== undefined)
    ? `<div class="cl-po-ctx">1-o'yin: ${m.other_leg_score1} : ${m.other_leg_score2}</div>` : "";

  return `
    <div class="cl-match-wrap">
      <div class="cl-match-head">
        <span class="cl-match-round">${escHtml(clpoLegLabel(m))}</span><span class="cl-match-id">#${m.id}</span>
        ${venue}
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="cl-match-body">
        <div class="match-center">${center}</div>
        ${action}
      </div>
      ${ctx}
      ${reject}
    </div>`;
}

// ---- Natija modali: guruh o'yinlaridagi UMUMIY #modal-result (clOpenResultModal naqshi) ----

function clpoOpenResultModal(matchId) {
  const m = (CLPO.my?.matches || []).find(x => x.id === matchId);
  if (!m) { showToast("O'yin topilmadi"); return; }
  const modal = document.getElementById("modal-result");
  if (!modal) { showToast("Modal topilmadi"); return; }

  CLPO._resultMatchId = matchId;   // submitMatchResult() shu flag orqali play-off'ga yo'naltiradi
  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  const setLogo = (id, club) => {
    const el = document.getElementById(id);
    if (!el) return;
    const logo = (typeof clClubLogo === "function") ? clClubLogo(club) : null;
    if (logo) { el.src = logo; el.alt = club || ""; el.style.display = ""; }
    else { el.removeAttribute("src"); el.style.display = "none"; }
  };
  setLogo("result-logo1", m.p1_club);
  setLogo("result-logo2", m.p2_club);

  const s1 = document.getElementById("input-score1");
  const s2 = document.getElementById("input-score2");
  if (s1) s1.value = "0";
  if (s2) s2.value = "0";
  modal.classList.remove("hidden");
}

const CLPO_ERRORS = {
  draw_not_allowed: "Finalda durang bo'lmaydi — o'yinni penaltigacha yakunlang",
  aggregate_draw_not_allowed: "Agregat teng bo'lishi mumkin emas — o'yinni qo'shimcha vaqt/penaltigacha yakunlab, YAKUNIY hisobni kiriting",
  wrong_status: "O'yin holati o'zgargan — sahifani yangilang",
  not_participant: "Siz bu o'yin ishtirokchisi emassiz",
  cannot_confirm_own: "O'z natijangizni o'zingiz tasdiqlay olmaysiz",
  already_started: "Play-off allaqachon boshlangan",
  groups_not_finished: "Guruh o'yinlari hali tugamagan",
  not_drawn: "Qur'a hali o'tkazilmagan",
};

// Umumiy modaldagi "Yuborish" shu funksiyaga yo'naltiriladi (api.js submitMatchResult)
async function clpoSubmitResultFromModal() {
  const id = CLPO._resultMatchId;
  const s1 = Number(document.getElementById("input-score1").value || 0);
  const s2 = Number(document.getElementById("input-score2").value || 0);
  try {
    await apiFetch(`/cl/playoff/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`, { method: "POST" });
    CLPO._resultMatchId = null;
    closeResultModal();
    showToast("Natija yuborildi");
    void clpoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (CLPO_ERRORS[e.message] || e.message));
  }
}

async function clpoConfirm(matchId, accept) {
  try {
    await apiFetch(`/cl/playoff/confirm-result?match_id=${matchId}&accept=${accept}`, { method: "POST" });
    showToast(accept ? "✅ Tasdiqlandi" : "Rad etildi — natija qayta kiritilsin");
    void clpoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (CLPO_ERRORS[e.message] || e.message));
  }
}

// ---- Kataklarni bog'lovchi chiziqlar (2026-07-21, WC wcDrawBracketLines naqshi) ----
// ChL bosqichlari: r16 → r8 → r4 → final. Keyingi juftlik pos = floor(pos/2).
// Final markazda (side="center") — chap 1/2 final unga o'ngdan, o'ng 1/2 final chapdan ulanadi.
function clpoDrawBracketLines() {
  const box = document.getElementById("cl-po-bracket-box");
  const inner = box ? box.querySelector(".wc-bracket-inner") : null;
  const svg = inner ? inner.querySelector(".wc-bracket-lines") : null;
  const bracket = inner ? inner.querySelector(".wc-bracket") : null;
  if (!inner || !svg || !bracket) return;

  const W = bracket.scrollWidth, H = bracket.scrollHeight;
  svg.setAttribute("width", W);
  svg.setAttribute("height", H);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = "";

  const base = bracket.getBoundingClientRect();
  const map = {};
  bracket.querySelectorAll(".wc-bracket-card[data-br-round]").forEach(c => {
    const rc = c.getBoundingClientRect();
    map[`${c.dataset.brRound}:${c.dataset.brPos}:${c.dataset.brSide}`] = {
      top: rc.top - base.top, left: rc.left - base.left, w: rc.width, h: rc.height,
    };
  });

  const NS = "http://www.w3.org/2000/svg";
  function line(x1, y1, x2, y2) {
    const path = document.createElementNS(NS, "path");
    const midX = (x1 + x2) / 2;
    path.setAttribute("d", `M ${x1} ${y1} H ${midX} V ${y2} H ${x2}`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "rgba(255,255,255,0.22)");
    path.setAttribute("stroke-width", "2");
    svg.appendChild(path);
  }

  const HOPS = [["r16", "r8"], ["r8", "r4"], ["r4", "final"]];
  for (const [r, nextR] of HOPS) {
    for (const key of Object.keys(map)) {
      const [rr, posStr, side] = key.split(":");
      if (rr !== r) continue;
      const cur = map[key];
      const childPos = Math.floor(parseInt(posStr) / 2);
      // Keyingi katak o'z tomonida, topilmasa markazda (final)
      const nxt = map[`${nextR}:${childPos}:${side}`] || map[`${nextR}:${childPos}:center`];
      if (!nxt) continue;
      if (side === "left") {
        line(cur.left + cur.w, cur.top + cur.h / 2, nxt.left, nxt.top + nxt.h / 2);
      } else {
        line(cur.left, cur.top + cur.h / 2, nxt.left + nxt.w, nxt.top + nxt.h / 2);
      }
    }
  }
}

// ---- ADMIN: Play-off boshlash ----

async function clpoAdminStart(btn) {
  if (!confirm("Play-off boshlansinmi? Har guruhdan top-2 (16 o'yinchi) 1/8 setkasiga joylanadi.")) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/cl/admin/playoff/start", { method: "POST" });
    showToast(`✅ Play-off boshlandi (${r.created} ta 1/8 o'yin)`);
    if (typeof clRenderAdminPage === "function") void clRenderAdminPage();
  } catch (e) {
    showToast("❌ " + (CLPO_ERRORS[e.message] || e.message));
    btn.disabled = false;
  }
}
