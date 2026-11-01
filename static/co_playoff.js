// ===== KL PLAY-OFF (2026-07-20) =====
// Setka — Reyting sahifasida (WC bracket naqshi, wc-bracket-* CSS qayta ishlatiladi).
// Har juftlik UY+MEHMON (2 o'yin), final — 1 o'yin. Kubok — KL kubogi (SVG).
// O'yinlar Profil sahifasida ("PLAY-OFF O'YINLARIM") kiritiladi/tasdiqlanadi.

const COPO = {
  bracket: null,      // /co/playoff/bracket javobi
  my: null,           // /co/playoff/my-matches javobi
  activeMatch: null,  // modal ochilgan o'yin (obyekt)
  chatOpened: null,   // Set: chat ochilgan o'yinlar (💬 → "Natija", guruh oqimi kabi)
  _lastMyJson: null,  // 2026-07-21: pir-pirashga qarshi — o'zgarmagan bo'lsa DOM yozilmaydi
};

const COPO_ROUND_NAMES = { playin: "Pley-in", r16: "1/8 final", r8: "1/4 final", r4: "1/2 final", final: COT("copo_final") };
const COPO_SIDE_ROUNDS = ["r16", "r8", "r4"];

// 2026-07-21: kubok — Sovrinlar sahifasidagi RASM (co-trophy.png, coRenderPrizes
// bilan bir xil fayl); .wc-bracket-trophy klassi o'lcham/animatsiya beradi.
function copoTrophySvg() {
  return `<img src="co-trophy.png?v=2" alt="${COT("co_cup_title")}" class="wc-bracket-trophy" />`;
}

// ---- SETKA (Reyting sahifasi) ----

async function copoLoadBracket() {
  const box = document.getElementById("co-po-bracket-box");
  if (!box) return;
  try {
    COPO.bracket = await apiFetch("/co/playoff/bracket");
  } catch (_) { COPO.bracket = null; }
  if (!COPO.bracket || !COPO.bracket.started) {
    box.innerHTML = `<div class="card">${COT("copo_not_started")}</div>`;
    return;
  }
  box.innerHTML = copoRenderBracket(COPO.bracket);
  copoBindBracketSides(box);
  // 2026-07-21: kataklarni bog'lovchi chiziqlar (WC wcDrawBracketLines naqshi).
  // Layout o'lchamlari tayyor bo'lishi uchun keyingi kadr + zaxira kechikish.
  requestAnimationFrame(copoDrawBracketLines);
  setTimeout(copoDrawBracketLines, 250);
}

// 2026-07-22 (talab 2): setkadagi ishtirokchi tomoniga bosilganda profil ochiladi
// (co_player.js coOpenPlayerFromBracket — reytingda topilsa to'liq, topilmasa minimal).
function copoBindBracketSides(box) {
  box.querySelectorAll(".copo-side--clickable").forEach(co => {
    co.addEventListener("click", () => {
      const uid = parseInt(co.dataset.copoPlayer, 10);
      if (!uid || typeof coOpenPlayerFromBracket !== "function") return;
      coOpenPlayerFromBracket(uid, {
        nickname: co.dataset.copoNick || "",
        username: co.dataset.copoUser || "",
        club_name: co.dataset.copoClub || "",
      });
    });
  });
}

// Juftlikning bir tomoni (klub + @user + IKKI O'YIN natijasi alohida ustunlarda)
// 2026-07-22: agregat o'rniga 1-o'yin va 2-o'yin natijalari YONMA-YON alohida
// ko'rsatiladi (masalan: Tojiyev  2  6 / Xusanov  1  4). Final — bitta o'yin.
function copoTieSide(tie, side, mirror) {
  const p = side === "a" ? tie.a : tie.b;
  const won = tie.winner_id && p.user_id === tie.winner_id;
  const name = p.username ? "@" + p.username : (p.nickname || "—");
  const badge = p.club_name ? coClubBadge(p.club_name, 18) : "";
  // Hisoblar: sideA — leg1'da mehmon (score2), leg2'da uyda (score1)
  const l1 = tie.leg1, l2 = tie.leg2;
  const s = (m, key) => (m && m.status === "confirmed") ? m[key] : null;
  const legVals = (tie.round === "final")
    ? [s(l1, side === "a" ? "score1" : "score2")]
    : [s(l1, side === "a" ? "score2" : "score1"), s(l2, side === "a" ? "score1" : "score2")];
  // Har o'yin uchun alohida katak (bo'sh/o'ynalmagan bo'lsa "–")
  const legCells = p.user_id
    ? legVals.map(v => `<span class="copo-leg-score">${v === null ? "–" : v}</span>`).join("")
    : "";
  const scoresText = p.user_id ? legVals.map(v => v === null ? "–" : v).join("·") : "";
  const scoreBlock = `<span class="wc-bracket-score copo-leg-scores">${legCells}</span>`;
  const inner = mirror
    ? `${scoreBlock}<span class="wc-bracket-name">${escHtml(name)}</span><span class="wc-bracket-flag">${badge}</span>`
    : `<span class="wc-bracket-flag">${badge}</span><span class="wc-bracket-name">${escHtml(name)}</span>${scoreBlock}`;
  // 2026-07-22 (talab 2): ishtirokchi aniq bo'lsa — bosilganda profili ochiladi.
  // Bo'sh tomon (hali aniqlanmagan) bosilmaydi; ma'lumot data-atributlarda.
  const cls = "wc-bracket-side" + (won ? " winner" : "")
    + (p.user_id ? " copo-side--clickable" : "");
  const dataAttrs = p.user_id
    ? ` data-copo-player="${p.user_id}"`
      + ` data-copo-nick="${escHtml(p.nickname || "")}"`
      + ` data-copo-user="${escHtml(p.username || "")}"`
      + ` data-copo-club="${escHtml(p.club_name || "")}"`
    : "";
  return `<div class="${cls}"${dataAttrs} title="O'yinlar: ${scoresText}">${inner}</div>`;
}

function copoTieCard(tie, side) {
  const mirror = side === "right";
  const sideCls = mirror ? "wc-bracket-card--right" : "wc-bracket-card--left";
  return `
    <div class="wc-bracket-card ${sideCls}"
         data-br-round="${escHtml(tie.round)}" data-br-pos="${tie.position}" data-br-side="${side}">
      ${copoTieSide(tie, "a", mirror)}
      ${copoTieSide(tie, "b", mirror)}
    </div>`;
}

// Har bosqichdagi juftliklar soni (bo'sh bosqichlar ham SKELET sifatida chiziladi —
// 2026-07-21: kubokkacha boradigan barcha kataklar oldindan ko'rinadi, chiziqlar ulanadi)
const COPO_TIE_COUNTS = { r16: 8, r8: 4, r4: 2, final: 1 };

function copoGetTie(rounds, rnd, pos) {
  const found = (rounds[rnd] || []).find(t => t.position === pos);
  return found || { round: rnd, position: pos, a: {}, b: {}, leg1: null, leg2: null,
                    agg_a: null, agg_b: null, winner_id: null };
}

function copoRenderBracket(data) {
  const rounds = data.rounds || {};
  const leftCols = [], rightCols = [];
  for (const rnd of COPO_SIDE_ROUNDS) {
    const total = COPO_TIE_COUNTS[rnd];
    const ties = [];
    for (let pos = 0; pos < total; pos++) ties.push(copoGetTie(rounds, rnd, pos));
    const half = Math.ceil(ties.length / 2);
    const left = ties.slice(0, half), right = ties.slice(half);
    leftCols.push(`<div class="wc-bracket-col">
      <div class="wc-bracket-round-label">${COPO_ROUND_NAMES[rnd]}</div>
      ${left.map(t => copoTieCard(t, "left")).join("")}</div>`);
    rightCols.unshift(`<div class="wc-bracket-col">
      <div class="wc-bracket-round-label">${COPO_ROUND_NAMES[rnd]}</div>
      ${right.map(t => copoTieCard(t, "right")).join("")}</div>`);
  }
  const finals = [copoGetTie(rounds, "final", 0)];
  const champ = data.champion;
  const champHtml = champ ? `
    <div class="co-po-champion">
      ${champ.club_name ? coClubBadge(champ.club_name, 30) : ""}
      <div class="co-po-champion-name">🏆 ${escHtml(champ.username ? "@" + champ.username : (champ.nickname || ""))}</div>
      <div class="co-po-champion-label">CHEMPION</div>
    </div>` : "";
  const centerCol = `<div class="wc-bracket-col wc-bracket-col--center">
    ${copoTrophySvg()}
    <div class="wc-bracket-round-label wc-bracket-final-label">Final</div>
    ${finals.map(t => copoTieCard(t, "center")).join("")}
    ${champHtml}
  </div>`;
  // Pley-in bloki (yangi format): 9-24 o'rin juftliklari setka ustida alohida
  // ro'yxat. Faqat playin bosqichi mavjud bo'lsa ko'rsatiladi (copoTieCard — DRY).
  const playinTies = rounds.playin || [];
  const playinHtml = playinTies.length ? `
    <div class="section-label">${COT("copo_playin_label")}</div>
    <div class="co-po-playin-list">
      ${playinTies
        .slice()
        .sort((a, b) => a.position - b.position)
        .map(t => copoTieCard({ ...t, round: "playin" }, "left"))
        .join("")}
    </div>` : "";

  return `
    ${playinHtml}
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

// ---- QAYTA TASNIF (pley-in, 9-24 o'rin) — alohida tab (2026-08) ----
// Ro'yxat ko'rinishi: chap klub | ikki leg hisobi | o'ng klub. G'olib ajratiladi.
// Ma'lumot manbai setka bilan bir xil (/co/playoff/bracket) — qoida #26 DRY.
async function copoLoadPlayin() {
  const box = document.getElementById("co-po-playin-box");
  if (!box) return;
  if (!COPO.bracket) {
    try { COPO.bracket = await apiFetch("/co/playoff/bracket"); }
    catch (_) { COPO.bracket = null; }
  }
  const br = COPO.bracket;
  if (!br || !br.started) {
    box.innerHTML = `<div class="card">${COT("copo_not_started")}</div>`;
    return;
  }
  const ties = (br.rounds && br.rounds.playin) || [];
  if (!ties.length) {
    box.innerHTML = `<div class="card">Qayta tasnif juftliklari hali yaratilmagan.</div>`;
    return;
  }
  box.innerHTML = `
    <div class="section-label">${COT("copo_playin_label")}</div>
    <div class="copo-playin-list">
      ${ties.slice().sort((x, y) => x.position - y.position).map(copoPlayinRow).join("")}
    </div>`;
  if (typeof copoBindBracketSides === "function") copoBindBracketSides(box);
}

// Bitta pley-in juftligi qatori (ikki o'yin hisobi bilan)
function copoPlayinRow(tie) {
  const l1 = tie.leg1, l2 = tie.leg2;
  // sideA = yuqori o'rin: leg1'da MEHMON (score2), leg2'da UYDA (score1)
  const a1 = (l1 && l1.score1 != null) ? l1.score2 : null;
  const b1 = (l1 && l1.score1 != null) ? l1.score1 : null;
  const a2 = (l2 && l2.score1 != null) ? l2.score1 : null;
  const b2 = (l2 && l2.score1 != null) ? l2.score2 : null;
  const line = (x, y) => (x == null || y == null)
    ? `<div class="copo-pi-score copo-pi-score--pending">—<span class="copo-pi-dash">:</span>—</div>`
    : `<div class="copo-pi-score">${x}<span class="copo-pi-dash">:</span>${y}</div>`;

  const sideHtml = (p, won, align) => {
    if (!p || !p.user_id) {
      return `<div class="copo-pi-side copo-pi-side--${align}"><span class="copo-pi-name">—</span></div>`;
    }
    const nm = escHtml(p.username ? "@" + p.username : (p.nickname || ""));
    return `
      <div class="copo-pi-side copo-pi-side--${align}${won ? " winner" : ""} copo-side--clickable"
           data-copo-player="${p.user_id}"
           data-copo-nick="${escHtml(p.nickname || "")}"
           data-copo-user="${escHtml(p.username || "")}"
           data-copo-club="${escHtml(p.club_name || "")}">
        ${coClubBadge(p.club_name, 26)}
        <span class="copo-pi-name">${nm}</span>
      </div>`;
  };

  const aWon = tie.winner_id && tie.a && tie.a.user_id === tie.winner_id;
  const bWon = tie.winner_id && tie.b && tie.b.user_id === tie.winner_id;

  return `
    <div class="copo-pi-row">
      ${sideHtml(tie.a, aWon, "left")}
      <div class="copo-pi-scores">${line(a1, b1)}${line(a2, b2)}</div>
      ${sideHtml(tie.b, bWon, "right")}
    </div>`;
}

// ---- PROFIL: PLAY-OFF O'YINLARIM ----
// 2026-07-21: dizayn va natija oqimi guruh o'yinlari ("MENING O'YINLARIM",
// coRenderMatchItem) bilan BIR XIL: .co-match-wrap karta, umumiy #modal-result
// modali (klub logolari + input-score1/2), tasdiqlash — bir bosishda, rad — alohida qator.

async function copoLoadMyMatches(force = false) {
  const box = document.getElementById("co-po-my-box");
  if (!box) return;
  try {
    COPO.my = await apiFetch("/co/playoff/my-matches");
  } catch (_) { COPO.my = null; }
  // 2026-07-21: PIR-PIRASH TUZATISH — har profil renderida qayta yozish o'rniga
  // ma'lumot O'ZGARMAGAN bo'lsa DOM tegilmaydi (JSON solishtiruv).
  const json = JSON.stringify(COPO.my && COPO.my.matches);
  if (!force && json === COPO._lastMyJson && box.innerHTML !== "") return;
  COPO._lastMyJson = json;
  copoRenderMyBox();
}

// Faqat renderlash (fetch'siz) — chat ochilganda 💬 → "Natija" almashinuvi uchun
function copoRenderMyBox() {
  const box = document.getElementById("co-po-my-box");
  if (!box) return;
  if (!COPO.my || !COPO.my.started || !COPO.my.matches.length) { box.innerHTML = ""; return; }
  box.innerHTML = `
    <div class="section-label">PLAY-OFF O'YINLARIM</div>
    <div class="matches-list">${COPO.my.matches.map(copoMyMatchItem).join("")}</div>`;
  if (typeof applyIcons === "function") applyIcons(box);
  box.querySelectorAll("[data-copo-result]").forEach(b =>
    b.addEventListener("click", () => copoOpenResultModal(parseInt(b.dataset.copoResult))));
  box.querySelectorAll("[data-copo-chat]").forEach(b =>
    b.addEventListener("click", () => copoChatThenResult(parseInt(b.dataset.copoChat))));
  box.querySelectorAll("[data-copo-open-match]").forEach(b =>
    b.addEventListener("click", () => copoChatThenResult(parseInt(b.dataset.copoOpenMatch))));
  box.querySelectorAll("[data-copo-confirm]").forEach(b =>
    b.addEventListener("click", () => void copoConfirm(parseInt(b.dataset.copoConfirm), true)));
  box.querySelectorAll("[data-copo-reject]").forEach(b =>
    b.addEventListener("click", () => void copoConfirm(parseInt(b.dataset.copoReject), false)));
}

// 💬 yoki logolar bosilganda: VS-oyna (ikkita chat) + "Natija" tugmasi ochiladi
// (guruh coOpenChatThenResult oqimi). Faqat LOKAL box qayta chiziladi —
// to'liq renderConferenceLeague chaqirilmaydi (pir-pirash bo'lmasin).
function copoChatThenResult(matchId) {
  if (!COPO.chatOpened) COPO.chatOpened = new Set();
  COPO.chatOpened.add(matchId);
  copoOpenOpponentModal(matchId);
  copoRenderMyBox();
}

function copoLegLabel(m) {
  const r = COPO_ROUND_NAMES[m.round] || m.round;
  return m.round === "final" ? r : `${r} · ${m.leg}-o'yin`;
}

// Guruh o'yinlari kartasi (coRenderMatchItem) bilan bir xil tuzilma
function copoMyMatchItem(m) {
  const meId = COPO.my.me_id;
  const isHome = m.player1_id === meId;                 // player1 = uy egasi
  const mine = m.submitted_by === meId;
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";

  // 2026-07-21: o'qilmagan chat rozetka — RAQIB logosi ustida (guruh kartasi kabi,
  // play-off kalitlari "p{id}" — /co/matches/unread endi ularni ham qaytaradi)
  const unreadCount = (typeof CO !== "undefined" && CO.unread && CO.unread.by_match
    && CO.unread.by_match["p" + m.id]) || 0;
  const unreadBadge = unreadCount > 0
    ? `<span class="chat-badge">${unreadCount > 9 ? "9+" : unreadCount}</span>`
    : "";
  const center = `
    <span class="co-mc-logo match-badge-wrap">${coClubBadge(m.p1_club, 26)}${isHome ? "" : unreadBadge}</span>
    <span class="match-score">${score}</span>
    <span class="co-mc-logo match-badge-wrap">${coClubBadge(m.p2_club, 26)}${isHome ? unreadBadge : ""}</span>`;

  let statusCls = "status--pending", statusText = "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  let action = "";
  if (m.status === "pending") {
    // 2026-10-11: soddalashtirildi — "Natija" darhol, yonida 💬 (VS-oyna: xona ID / bot chati / Telegram)
    action = `<button class="match-action-btn" data-copo-result="${m.id}">${COT("co_result")}</button>`
      + `<button class="match-action-btn match-chat-btn" data-copo-chat="${m.id}" title="Avval raqib bilan kelishing">${ICON.get("chat", 18)}</button>`;
  } else if (m.status === "awaiting_confirmation") {
    action = mine
      ? `<span class="match-waiting">${COT("co_pending")}</span>`
      : `<button class="match-action-btn" data-copo-confirm="${m.id}">${ICON.get("check", 16)}</button>`;
  }
  const reject = (m.status === "awaiting_confirmation" && !mine)
    ? `<div class="co-score-row"><button class="btn" data-copo-reject="${m.id}">${ICON.get("cross", 15)} ${COT("co_reject")}</button></div>` : "";

  const venue = isHome
    ? `<span class="co-venue co-venue--home">UY</span>`
    : `<span class="co-venue co-venue--away">MEHMON</span>`;

  // 2-o'yinda 1-o'yin hisobi (agregat konteksti)
  const ctx = (m.leg === 2 && m.other_leg_score1 !== null && m.other_leg_score1 !== undefined)
    ? `<div class="co-po-ctx">1-o'yin: ${m.other_leg_score1} : ${m.other_leg_score2}</div>` : "";

  return `
    <div class="co-match-wrap">
      <div class="co-match-head">
        <span class="co-match-round">${escHtml(copoLegLabel(m))}</span><span class="co-match-id">#${m.id}</span>
        ${venue}
        ${m.status === "pending" ? "" : `<span class="match-status ${statusCls}">${statusText}</span>`}
      </div>
      <div class="co-match-body">
        <div class="match-center match-center--clickable" data-copo-open-match="${m.id}">${center}</div>
        ${action}
      </div>
      ${ctx}
      ${reject}
    </div>`;
}

// ---- VS-oyna: IKKITA chat (bot chati + Telegram) — co_chat.js coOpenOpponentModal naqshi ----
// 2026-07-21: logolar juftligi yoki 💬 bosilganda ochiladi. WebApp chati
// /co/playoff/matches prefiksi bilan ishlaydi (guruh chatidan alohida jadval).

function copoOpenOpponentModal(matchId) {
  const m = (COPO.my?.matches || []).find(x => x.id === matchId);
  if (!m) return;
  const t = APP.t || {};
  const meId = COPO.my.me_id;
  const iAmP1 = m.player1_id === meId;

  const me  = { nick: iAmP1 ? m.p1_nick : m.p2_nick,
                club: iAmP1 ? m.p1_club : m.p2_club,
                username: iAmP1 ? m.p1_user : m.p2_user };
  const opp = { nick: iAmP1 ? m.p2_nick : m.p1_nick,
                club: iAmP1 ? m.p2_club : m.p1_club,
                username: iAmP1 ? m.p2_user : m.p1_user };

  let modal = document.getElementById("modal-copo-opponent");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-copo-opponent";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }

  const side = (p) => `
    <div class="opp-side">
      <div class="co-vs-logo">${coClubBadge(p.club, 72)}</div>
      <div class="opp-club">${escHtml(p.club || p.nick || "—")}</div>
      <div class="opp-user">${p.username ? "@" + escHtml(p.username) : "—"}</div>
    </div>`;

  const tgBtn = opp.username
    ? `<button class="opp-chat-btn" id="copo-opp-tg">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;

  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="copo-opp-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">
        ${side(me)}
        <div class="opp-vs-sep">VS</div>
        ${side(opp)}
      </div>
      ${typeof roomCodeBtnHtml === "function" ? roomCodeBtnHtml(matchId, "co_po") : ""}
      <button class="opp-chat-btn opp-webchat-btn" id="copo-opp-webchat">
        ${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}
      </button>
      ${tgBtn}
    </div>`;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  const close = () => modal.classList.add("hidden");
  document.getElementById("copo-opp-close").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });

  document.getElementById("copo-opp-webchat").addEventListener("click", () => {
    close();
    openWebChat(m.id, opp.nick || "Raqib", "/co/playoff/matches");   // api.js webchat (DRY)
  });
  document.getElementById("copo-opp-tg")?.addEventListener("click", () => {
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

// ---- Natija modali: guruh o'yinlaridagi UMUMIY #modal-result (coOpenResultModal naqshi) ----

function copoOpenResultModal(matchId) {
  const m = (COPO.my?.matches || []).find(x => x.id === matchId);
  if (!m) { showToast(COT("co_match_404")); return; }
  const modal = document.getElementById("modal-result");
  if (!modal) { showToast(COT("co_modal_404")); return; }

  COPO._resultMatchId = matchId;   // submitMatchResult() shu flag orqali play-off'ga yo'naltiradi
  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  const setLogo = (id, club) => {
    const co = document.getElementById(id);
    if (!co) return;
    const logo = (typeof coClubLogo === "function") ? coClubLogo(club) : null;
    if (logo) { co.src = logo; co.alt = club || ""; co.style.display = ""; }
    else { co.removeAttribute("src"); co.style.display = "none"; }
  };
  setLogo("result-logo1", m.p1_club);
  setLogo("result-logo2", m.p2_club);

  const s1 = document.getElementById("input-score1");
  const s2 = document.getElementById("input-score2");
  if (s1) s1.value = "0";
  if (s2) s2.value = "0";
  modal.classList.remove("hidden");
}

const COPO_ERRORS = {
  draw_not_allowed: COT("copo_err_draw"),
  aggregate_draw_not_allowed: COT("copo_err_agg_draw"),
  wrong_status: COT("copo_err_status"),
  not_participant: COT("copo_err_not_part"),
  cannot_confirm_own: COT("copo_err_own"),
  already_started: COT("copo_err_started"),
  groups_not_finished: COT("copo_err_groups"),
  not_drawn: COT("copo_err_not_drawn"),
  // 2026-08: setka bosqichi (2-bosqich) xatolari
  playin_not_started: "Avval qayta tasnifni boshlang.",
  playin_not_finished: "Qayta tasnif hali tugamagan — barcha 16 o'yin tasdiqlanishi kerak.",
  bracket_already_started: "Setka allaqachon ochilgan.",
  not_enough_players: "Reytingda yetarli ishtirokchi yo'q (24 ta kerak).",
  bracket_failed: "Setkani ochishda xatolik.",
};

// Umumiy modaldagi "Yuborish" shu funksiyaga yo'naltiriladi (api.js submitMatchResult)
async function copoSubmitResultFromModal() {
  const id = COPO._resultMatchId;
  const s1 = Number(document.getElementById("input-score1").value || 0);
  const s2 = Number(document.getElementById("input-score2").value || 0);
  try {
    await apiFetch(`/co/playoff/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`, { method: "POST" });
    COPO._resultMatchId = null;
    closeResultModal();
    showToast(COT("co_toast_result_sent"));
    void copoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (COPO_ERRORS[e.message] || e.message));
  }
}

async function copoConfirm(matchId, accept) {
  try {
    await apiFetch(`/co/playoff/confirm-result?match_id=${matchId}&accept=${accept}`, { method: "POST" });
    showToast(accept ? COT("copo_confirmed") : COT("copo_rejected"));
    void copoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (COPO_ERRORS[e.message] || e.message));
  }
}

// ---- Kataklarni bog'lovchi chiziqlar (2026-07-21, WC wcDrawBracketLines naqshi) ----
// KL bosqichlari: r16 → r8 → r4 → final. Keyingi juftlik pos = floor(pos/2).
// Final markazda (side="center") — chap 1/2 final unga o'ngdan, o'ng 1/2 final chapdan ulanadi.
function copoDrawBracketLines() {
  const box = document.getElementById("co-po-bracket-box");
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

async function copoAdminStart(btn) {
  if (!confirm(COT("copo_start_ask"))) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/co/admin/playoff/start", { method: "POST" });
    showToast(`✅ Qayta tasnif boshlandi (${r.playin_pairs} juftlik)`);
    if (typeof coRenderAdminPage === "function") void coRenderAdminPage();
  } catch (e) {
    // 2026-08-28: "Guruh o'yinlari hali tugamagan" xabari qaysi o'yin
    // bloklayotganini aytmaydi — diagnostikani so'rab, adminga ro'yxatni
    // ko'rsatamiz (faqat o'qish, hech narsa o'zgarmaydi).
    if (e.message === "groups_not_finished") {
      await copoShowGroupBlocking(btn);
      return;   // btn holati copoShowGroupBlocking ichida boshqariladi
    } else {
      showToast("❌ " + (COPO_ERRORS[e.message] || e.message));
    }
    btn.disabled = false;
  }
}

// Bloklayotgan o'yinlarni ko'rsatadi va majburiy yopishni taklif qiladi.
// 2026-08-28: admin 23:30 deadline'ni kutmasin — ro'yxatni ko'rib, tasdiqlasa
// o'yinlar darhol yopiladi va qayta tasnif AVTOMATIK boshlanadi (bitta oqim).
async function copoShowGroupBlocking(btn) {
  let d;
  try {
    d = await apiFetch("/co/admin/group-blocking");
  } catch (_) {
    showToast("❌ " + COT("copo_err_groups"));
    return;
  }

  const lines = (d.matches || []).slice(0, 15).map(m =>
    `${m.matchday}-tur · #${m.id} · ${m.p1 || "?"} vs ${m.p2 || "?"} — ${m.status}`
  );
  const more = d.blocking_count > lines.length
    ? `\n... va yana ${d.blocking_count - lines.length} ta`
    : "";

  const ok = confirm(
    `Guruh bosqichida ${d.blocking_count} ta o'yin tasdiqlanmagan.\n` +
    `Mavsum: ${d.season} · Joriy tur: ${d.current_matchday} / ${d.total_matchdays}\n\n` +
    lines.join("\n") + more +
    `\n\nShu o'yinlar HOZIR yopilsinmi?\n` +
    `• Hisob kiritilgan o'yinlar — kiritilgan natija bilan tasdiqlanadi\n` +
    `• Hech kim kiritmagan o'yinlar — 0:0 durang\n\n` +
    `Keyin qayta tasnif avtomatik boshlanadi. Bu amalni ortga qaytarib bo'lmaydi.`
  );
  if (!ok) return;

  try {
    const r = await apiFetch("/co/admin/group/force-close", { method: "POST" });
    showToast(`✅ ${r.awaiting_resolved + r.pending_resolved} o'yin yopildi (0:0: ${r.pending_resolved})`);
  } catch (e) {
    const msg = {
      group_not_over: "Guruh bosqichi hali tugamagan — majburiy yopib bo'lmaydi.",
      not_started: "KL turlari boshlanmagan.",
      not_drawn: "KL qur'asi o'tkazilmagan.",
      force_close_failed: "Yopishda xatolik.",
    }[e.message] || e.message;
    showToast("❌ " + msg);
    return;
  }

  // O'yinlar yopildi — endi qayta tasnifni qayta urinamiz
  try {
    const r = await apiFetch("/co/admin/playoff/start", { method: "POST" });
    showToast(`✅ Qayta tasnif boshlandi (${r.playin_pairs} juftlik)`);
    if (typeof coRenderAdminPage === "function") void coRenderAdminPage();
  } catch (e) {
    showToast("❌ " + (COPO_ERRORS[e.message] || e.message));
    if (btn) btn.disabled = false;
  }
}

// 2026-08: 2-BOSQICH — asosiy setkani ochish (qayta tasnif tugagach)
async function copoAdminStartBracket(btn) {
  if (!confirm("Asosiy setka (1/8 final) ochilsinmi?\n\nQayta tasnif g'oliblari top-8 bilan juftlanadi. Bu amalni ortga qaytarib bo'lmaydi.")) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/co/admin/playoff/start-bracket", { method: "POST" });
    showToast(`✅ Setka ochildi (${r.r16_pairs} juftlik)`);
    COPO.bracket = null;   // keshni tozalaymiz — yangi setka yuklansin
    if (typeof coRenderAdminPage === "function") void coRenderAdminPage();
  } catch (e) {
    showToast("❌ " + (COPO_ERRORS[e.message] || e.message));
    btn.disabled = false;
  }
}
