// ===== ChL PLAY-OFF (2026-07-20) =====
// Setka — Reyting sahifasida (WC bracket naqshi, wc-bracket-* CSS qayta ishlatiladi).
// Har juftlik UY+MEHMON (2 o'yin), final — 1 o'yin. Kubok — ChL kubogi (SVG).
// O'yinlar Profil sahifasida ("PLAY-OFF O'YINLARIM") kiritiladi/tasdiqlanadi.

const CLPO = {
  bracket: null,      // /cl/playoff/bracket javobi
  my: null,           // /cl/playoff/my-matches javobi
  activeMatch: null,  // modal ochilgan o'yin (obyekt)
  chatOpened: null,   // Set: chat ochilgan o'yinlar (💬 → "Natija", guruh oqimi kabi)
  _lastMyJson: null,  // 2026-07-21: pir-pirashga qarshi — o'zgarmagan bo'lsa DOM yozilmaydi
};

const CLPO_ROUND_NAMES = { r16: "1/8 final", r8: "1/4 final", r4: "1/2 final", final: CT("clpo_final") };
const CLPO_SIDE_ROUNDS = ["r16", "r8", "r4"];

// 2026-07-21: kubok — Sovrinlar sahifasidagi RASM (cl-trophy.png, clRenderPrizes
// bilan bir xil fayl); .wc-bracket-trophy klassi o'lcham/animatsiya beradi.
function clpoTrophySvg() {
  return `<img src="cl-trophy.png" alt="${CT("cl_cup_title")}" class="wc-bracket-trophy" />`;
}

// ---- SETKA (Reyting sahifasi) ----

async function clpoLoadBracket() {
  const box = document.getElementById("cl-po-bracket-box");
  if (!box) return;
  try {
    CLPO.bracket = await apiFetch("/cl/playoff/bracket");
  } catch (_) { CLPO.bracket = null; }
  if (!CLPO.bracket || !CLPO.bracket.started) {
    box.innerHTML = `<div class="card">${CT("clpo_not_started")}</div>`;
    return;
  }
  box.innerHTML = clpoRenderBracket(CLPO.bracket);
  clpoBindBracketSides(box);
  // 2026-07-21: kataklarni bog'lovchi chiziqlar (WC wcDrawBracketLines naqshi).
  // Layout o'lchamlari tayyor bo'lishi uchun keyingi kadr + zaxira kechikish.
  requestAnimationFrame(clpoDrawBracketLines);
  setTimeout(clpoDrawBracketLines, 250);
}

// 2026-07-22 (talab 2): setkadagi ishtirokchi tomoniga bosilganda profil ochiladi
// (cl_player.js clOpenPlayerFromBracket — reytingda topilsa to'liq, topilmasa minimal).
function clpoBindBracketSides(box) {
  box.querySelectorAll(".clpo-side--clickable").forEach(el => {
    el.addEventListener("click", () => {
      const uid = parseInt(el.dataset.clpoPlayer, 10);
      if (!uid || typeof clOpenPlayerFromBracket !== "function") return;
      clOpenPlayerFromBracket(uid, {
        nickname: el.dataset.clpoNick || "",
        username: el.dataset.clpoUser || "",
        club_name: el.dataset.clpoClub || "",
      });
    });
  });
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
  // 2026-07-22 (talab 2): ishtirokchi aniq bo'lsa — bosilganda profili ochiladi.
  // Bo'sh tomon (hali aniqlanmagan) bosilmaydi; ma'lumot data-atributlarda.
  const cls = "wc-bracket-side" + (won ? " winner" : "")
    + (p.user_id ? " clpo-side--clickable" : "");
  const dataAttrs = p.user_id
    ? ` data-clpo-player="${p.user_id}"`
      + ` data-clpo-nick="${escHtml(p.nickname || "")}"`
      + ` data-clpo-user="${escHtml(p.username || "")}"`
      + ` data-clpo-club="${escHtml(p.club_name || "")}"`
    : "";
  return `<div class="${cls}"${dataAttrs} title="O'yinlar: ${scores}">${inner}</div>`;
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

async function clpoLoadMyMatches(force = false) {
  const box = document.getElementById("cl-po-my-box");
  if (!box) return;
  try {
    CLPO.my = await apiFetch("/cl/playoff/my-matches");
  } catch (_) { CLPO.my = null; }
  // 2026-07-21: PIR-PIRASH TUZATISH — har profil renderida qayta yozish o'rniga
  // ma'lumot O'ZGARMAGAN bo'lsa DOM tegilmaydi (JSON solishtiruv).
  const json = JSON.stringify(CLPO.my && CLPO.my.matches);
  if (!force && json === CLPO._lastMyJson && box.innerHTML !== "") return;
  CLPO._lastMyJson = json;
  clpoRenderMyBox();
}

// Faqat renderlash (fetch'siz) — chat ochilganda 💬 → "Natija" almashinuvi uchun
function clpoRenderMyBox() {
  const box = document.getElementById("cl-po-my-box");
  if (!box) return;
  if (!CLPO.my || !CLPO.my.started || !CLPO.my.matches.length) { box.innerHTML = ""; return; }
  box.innerHTML = `
    <div class="section-label">PLAY-OFF O'YINLARIM</div>
    <div class="matches-list">${CLPO.my.matches.map(clpoMyMatchItem).join("")}</div>`;
  if (typeof applyIcons === "function") applyIcons(box);
  box.querySelectorAll("[data-clpo-result]").forEach(b =>
    b.addEventListener("click", () => clpoOpenResultModal(parseInt(b.dataset.clpoResult))));
  box.querySelectorAll("[data-clpo-chat]").forEach(b =>
    b.addEventListener("click", () => clpoChatThenResult(parseInt(b.dataset.clpoChat))));
  box.querySelectorAll("[data-clpo-open-match]").forEach(b =>
    b.addEventListener("click", () => clpoChatThenResult(parseInt(b.dataset.clpoOpenMatch))));
  box.querySelectorAll("[data-clpo-confirm]").forEach(b =>
    b.addEventListener("click", () => void clpoConfirm(parseInt(b.dataset.clpoConfirm), true)));
  box.querySelectorAll("[data-clpo-reject]").forEach(b =>
    b.addEventListener("click", () => void clpoConfirm(parseInt(b.dataset.clpoReject), false)));
}

// 💬 yoki logolar bosilganda: VS-oyna (ikkita chat) + "Natija" tugmasi ochiladi
// (guruh clOpenChatThenResult oqimi). Faqat LOKAL box qayta chiziladi —
// to'liq renderChampionsLeague chaqirilmaydi (pir-pirash bo'lmasin).
function clpoChatThenResult(matchId) {
  if (!CLPO.chatOpened) CLPO.chatOpened = new Set();
  CLPO.chatOpened.add(matchId);
  clpoOpenOpponentModal(matchId);
  clpoRenderMyBox();
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

  // 2026-07-21: o'qilmagan chat rozetka — RAQIB logosi ustida (guruh kartasi kabi,
  // play-off kalitlari "p{id}" — /cl/matches/unread endi ularni ham qaytaradi)
  const unreadCount = (typeof CL !== "undefined" && CL.unread && CL.unread.by_match
    && CL.unread.by_match["p" + m.id]) || 0;
  const unreadBadge = unreadCount > 0
    ? `<span class="chat-badge">${unreadCount > 9 ? "9+" : unreadCount}</span>`
    : "";
  const center = `
    <span class="cl-mc-logo match-badge-wrap">${clClubBadge(m.p1_club, 26)}${isHome ? "" : unreadBadge}</span>
    <span class="match-score">${score}</span>
    <span class="cl-mc-logo match-badge-wrap">${clClubBadge(m.p2_club, 26)}${isHome ? unreadBadge : ""}</span>`;

  let statusCls = "status--pending", statusText = "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  let action = "";
  if (m.status === "pending") {
    // 2026-07-21: guruh oqimi bilan bir xil — avval 💬 chat, chat ochilgach "Natija"
    action = (CLPO.chatOpened && CLPO.chatOpened.has(m.id))
      ? `<button class="match-action-btn" data-clpo-result="${m.id}">${CT("cl_result")}</button>`
      : `<button class="match-action-btn match-chat-btn" data-clpo-chat="${m.id}" title="Avval raqib bilan kelishing">${ICON.get("chat", 18)}</button>`;
  } else if (m.status === "awaiting_confirmation") {
    action = mine
      ? `<span class="match-waiting">${CT("cl_pending")}</span>`
      : `<button class="match-action-btn" data-clpo-confirm="${m.id}">${ICON.get("check", 16)}</button>`;
  }
  const reject = (m.status === "awaiting_confirmation" && !mine)
    ? `<div class="cl-score-row"><button class="btn" data-clpo-reject="${m.id}">${ICON.get("cross", 15)} ${CT("cl_reject")}</button></div>` : "";

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
        <div class="match-center match-center--clickable" data-clpo-open-match="${m.id}">${center}</div>
        ${action}
      </div>
      ${ctx}
      ${reject}
    </div>`;
}

// ---- VS-oyna: IKKITA chat (bot chati + Telegram) — cl_chat.js clOpenOpponentModal naqshi ----
// 2026-07-21: logolar juftligi yoki 💬 bosilganda ochiladi. WebApp chati
// /cl/playoff/matches prefiksi bilan ishlaydi (guruh chatidan alohida jadval).

function clpoOpenOpponentModal(matchId) {
  const m = (CLPO.my?.matches || []).find(x => x.id === matchId);
  if (!m) return;
  const t = APP.t || {};
  const meId = CLPO.my.me_id;
  const iAmP1 = m.player1_id === meId;

  const me  = { nick: iAmP1 ? m.p1_nick : m.p2_nick,
                club: iAmP1 ? m.p1_club : m.p2_club,
                username: iAmP1 ? m.p1_user : m.p2_user };
  const opp = { nick: iAmP1 ? m.p2_nick : m.p1_nick,
                club: iAmP1 ? m.p2_club : m.p1_club,
                username: iAmP1 ? m.p2_user : m.p1_user };

  let modal = document.getElementById("modal-clpo-opponent");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-clpo-opponent";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }

  const side = (p) => `
    <div class="opp-side">
      <div class="cl-vs-logo">${clClubBadge(p.club, 72)}</div>
      <div class="opp-club">${escHtml(p.club || p.nick || "—")}</div>
      <div class="opp-user">${p.username ? "@" + escHtml(p.username) : "—"}</div>
    </div>`;

  const tgBtn = opp.username
    ? `<button class="opp-chat-btn" id="clpo-opp-tg">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;

  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="clpo-opp-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">
        ${side(me)}
        <div class="opp-vs-sep">VS</div>
        ${side(opp)}
      </div>
      <button class="opp-chat-btn opp-webchat-btn" id="clpo-opp-webchat">
        ${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}
      </button>
      ${tgBtn}
    </div>`;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  const close = () => modal.classList.add("hidden");
  document.getElementById("clpo-opp-close").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });

  document.getElementById("clpo-opp-webchat").addEventListener("click", () => {
    close();
    openWebChat(m.id, opp.nick || "Raqib", "/cl/playoff/matches");   // api.js webchat (DRY)
  });
  document.getElementById("clpo-opp-tg")?.addEventListener("click", () => {
    const tg = window.Telegram?.WebApp;
    const link = `https://t.me/${String(opp.username).replace(/^@/, "")}`;
    if (tg?.openTelegramLink) {
      try { tg.openTelegramLink(link); } catch (_) { window.open(link, "_blank"); }
    } else {
      window.open(link, "_blank");
    }
    close();
  });
}

// ---- Natija modali: guruh o'yinlaridagi UMUMIY #modal-result (clOpenResultModal naqshi) ----

function clpoOpenResultModal(matchId) {
  const m = (CLPO.my?.matches || []).find(x => x.id === matchId);
  if (!m) { showToast(CT("cl_match_404")); return; }
  const modal = document.getElementById("modal-result");
  if (!modal) { showToast(CT("cl_modal_404")); return; }

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
  draw_not_allowed: CT("clpo_err_draw"),
  aggregate_draw_not_allowed: CT("clpo_err_agg_draw"),
  wrong_status: CT("clpo_err_status"),
  not_participant: CT("clpo_err_not_part"),
  cannot_confirm_own: CT("clpo_err_own"),
  already_started: CT("clpo_err_started"),
  groups_not_finished: CT("clpo_err_groups"),
  not_drawn: CT("clpo_err_not_drawn"),
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
    showToast(CT("cl_toast_result_sent"));
    void clpoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (CLPO_ERRORS[e.message] || e.message));
  }
}

async function clpoConfirm(matchId, accept) {
  try {
    await apiFetch(`/cl/playoff/confirm-result?match_id=${matchId}&accept=${accept}`, { method: "POST" });
    showToast(accept ? CT("clpo_confirmed") : CT("clpo_rejected"));
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
  if (!confirm(CT("clpo_start_ask"))) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/cl/admin/playoff/start", { method: "POST" });
    showToast(`✅ ${CT("clpo_started")} (${r.created})`);
    if (typeof clRenderAdminPage === "function") void clRenderAdminPage();
  } catch (e) {
    showToast("❌ " + (CLPO_ERRORS[e.message] || e.message));
    btn.disabled = false;
  }
}
