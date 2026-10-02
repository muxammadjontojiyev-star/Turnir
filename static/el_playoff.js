// ===== YeL PLAY-OFF (2026-07-20) =====
// Setka — Reyting sahifasida (WC bracket naqshi, wc-bracket-* CSS qayta ishlatiladi).
// Har juftlik UY+MEHMON (2 o'yin), final — 1 o'yin. Kubok — YeL kubogi (SVG).
// O'yinlar Profil sahifasida ("PLAY-OFF O'YINLARIM") kiritiladi/tasdiqlanadi.

const ELPO = {
  bracket: null,      // /el/playoff/bracket javobi
  my: null,           // /el/playoff/my-matches javobi
  activeMatch: null,  // modal ochilgan o'yin (obyekt)
  chatOpened: null,   // Set: chat ochilgan o'yinlar (💬 → "Natija", guruh oqimi kabi)
  _lastMyJson: null,  // 2026-07-21: pir-pirashga qarshi — o'zgarmagan bo'lsa DOM yozilmaydi
};

const ELPO_ROUND_NAMES = { playin: "Pley-in", r16: "1/8 final", r8: "1/4 final", r4: "1/2 final", final: ET("elpo_final") };
const ELPO_SIDE_ROUNDS = ["r16", "r8", "r4"];

// 2026-07-21: kubok — Sovrinlar sahifasidagi RASM (el-trophy.png, elRenderPrizes
// bilan bir xil fayl); .wc-bracket-trophy klassi o'lcham/animatsiya beradi.
function elpoTrophySvg() {
  return `<img src="el-trophy.png" alt="${ET("el_cup_title")}" class="wc-bracket-trophy" />`;
}

// ---- SETKA (Reyting sahifasi) ----

async function elpoLoadBracket() {
  const box = document.getElementById("el-po-bracket-box");
  if (!box) return;
  try {
    ELPO.bracket = await apiFetch("/el/playoff/bracket");
  } catch (_) { ELPO.bracket = null; }
  if (!ELPO.bracket || !ELPO.bracket.started) {
    box.innerHTML = `<div class="card">${ET("elpo_not_started")}</div>`;
    return;
  }
  box.innerHTML = elpoRenderBracket(ELPO.bracket);
  elpoBindBracketSides(box);
  // 2026-07-21: kataklarni bog'lovchi chiziqlar (WC wcDrawBracketLines naqshi).
  // Layout o'lchamlari tayyor bo'lishi uchun keyingi kadr + zaxira kechikish.
  requestAnimationFrame(elpoDrawBracketLines);
  setTimeout(elpoDrawBracketLines, 250);
}

// 2026-07-22 (talab 2): setkadagi ishtirokchi tomoniga bosilganda profil ochiladi
// (el_player.js elOpenPlayerFromBracket — reytingda topilsa to'liq, topilmasa minimal).
function elpoBindBracketSides(box) {
  box.querySelectorAll(".elpo-side--clickable").forEach(el => {
    el.addEventListener("click", () => {
      const uid = parseInt(el.dataset.elpoPlayer, 10);
      if (!uid || typeof elOpenPlayerFromBracket !== "function") return;
      elOpenPlayerFromBracket(uid, {
        nickname: el.dataset.elpoNick || "",
        username: el.dataset.elpoUser || "",
        club_name: el.dataset.elpoClub || "",
      });
    });
  });
}

// Juftlikning bir tomoni (klub + @user + IKKI O'YIN natijasi alohida ustunlarda)
// 2026-07-22: agregat o'rniga 1-o'yin va 2-o'yin natijalari YONMA-YON alohida
// ko'rsatiladi (masalan: Tojiyev  2  6 / Xusanov  1  4). Final — bitta o'yin.
function elpoTieSide(tie, side, mirror) {
  const p = side === "a" ? tie.a : tie.b;
  const won = tie.winner_id && p.user_id === tie.winner_id;
  const name = p.username ? "@" + p.username : (p.nickname || "—");
  const badge = p.club_name ? elClubBadge(p.club_name, 18) : "";
  // Hisoblar: sideA — leg1'da mehmon (score2), leg2'da uyda (score1)
  const l1 = tie.leg1, l2 = tie.leg2;
  const s = (m, key) => (m && m.status === "confirmed") ? m[key] : null;
  const legVals = (tie.round === "final")
    ? [s(l1, side === "a" ? "score1" : "score2")]
    : [s(l1, side === "a" ? "score2" : "score1"), s(l2, side === "a" ? "score1" : "score2")];
  // Har o'yin uchun alohida katak (bo'sh/o'ynalmagan bo'lsa "–")
  const legCells = p.user_id
    ? legVals.map(v => `<span class="elpo-leg-score">${v === null ? "–" : v}</span>`).join("")
    : "";
  const scoresText = p.user_id ? legVals.map(v => v === null ? "–" : v).join("·") : "";
  const scoreBlock = `<span class="wc-bracket-score elpo-leg-scores">${legCells}</span>`;
  const inner = mirror
    ? `${scoreBlock}<span class="wc-bracket-name">${escHtml(name)}</span><span class="wc-bracket-flag">${badge}</span>`
    : `<span class="wc-bracket-flag">${badge}</span><span class="wc-bracket-name">${escHtml(name)}</span>${scoreBlock}`;
  // 2026-07-22 (talab 2): ishtirokchi aniq bo'lsa — bosilganda profili ochiladi.
  // Bo'sh tomon (hali aniqlanmagan) bosilmaydi; ma'lumot data-atributlarda.
  const cls = "wc-bracket-side" + (won ? " winner" : "")
    + (p.user_id ? " elpo-side--clickable" : "");
  const dataAttrs = p.user_id
    ? ` data-elpo-player="${p.user_id}"`
      + ` data-elpo-nick="${escHtml(p.nickname || "")}"`
      + ` data-elpo-user="${escHtml(p.username || "")}"`
      + ` data-elpo-club="${escHtml(p.club_name || "")}"`
    : "";
  return `<div class="${cls}"${dataAttrs} title="O'yinlar: ${scoresText}">${inner}</div>`;
}

function elpoTieCard(tie, side) {
  const mirror = side === "right";
  const sideCls = mirror ? "wc-bracket-card--right" : "wc-bracket-card--left";
  return `
    <div class="wc-bracket-card ${sideCls}"
         data-br-round="${escHtml(tie.round)}" data-br-pos="${tie.position}" data-br-side="${side}">
      ${elpoTieSide(tie, "a", mirror)}
      ${elpoTieSide(tie, "b", mirror)}
    </div>`;
}

// Har bosqichdagi juftliklar soni (bo'sh bosqichlar ham SKELET sifatida chiziladi —
// 2026-07-21: kubokkacha boradigan barcha kataklar oldindan ko'rinadi, chiziqlar ulanadi)
const ELPO_TIE_COUNTS = { r16: 8, r8: 4, r4: 2, final: 1 };

function elpoGetTie(rounds, rnd, pos) {
  const found = (rounds[rnd] || []).find(t => t.position === pos);
  return found || { round: rnd, position: pos, a: {}, b: {}, leg1: null, leg2: null,
                    agg_a: null, agg_b: null, winner_id: null };
}

function elpoRenderBracket(data) {
  const rounds = data.rounds || {};
  const leftCols = [], rightCols = [];
  for (const rnd of ELPO_SIDE_ROUNDS) {
    const total = ELPO_TIE_COUNTS[rnd];
    const ties = [];
    for (let pos = 0; pos < total; pos++) ties.push(elpoGetTie(rounds, rnd, pos));
    const half = Math.ceil(ties.length / 2);
    const left = ties.slice(0, half), right = ties.slice(half);
    leftCols.push(`<div class="wc-bracket-col">
      <div class="wc-bracket-round-label">${ELPO_ROUND_NAMES[rnd]}</div>
      ${left.map(t => elpoTieCard(t, "left")).join("")}</div>`);
    rightCols.unshift(`<div class="wc-bracket-col">
      <div class="wc-bracket-round-label">${ELPO_ROUND_NAMES[rnd]}</div>
      ${right.map(t => elpoTieCard(t, "right")).join("")}</div>`);
  }
  const finals = [elpoGetTie(rounds, "final", 0)];
  const champ = data.champion;
  const champHtml = champ ? `
    <div class="el-po-champion">
      ${champ.club_name ? elClubBadge(champ.club_name, 30) : ""}
      <div class="el-po-champion-name">🏆 ${escHtml(champ.username ? "@" + champ.username : (champ.nickname || ""))}</div>
      <div class="el-po-champion-label">CHEMPION</div>
    </div>` : "";
  const centerCol = `<div class="wc-bracket-col wc-bracket-col--center">
    ${elpoTrophySvg()}
    <div class="wc-bracket-round-label wc-bracket-final-label">Final</div>
    ${finals.map(t => elpoTieCard(t, "center")).join("")}
    ${champHtml}
  </div>`;
  // Pley-in bloki (yangi format): 9-24 o'rin juftliklari setka ustida alohida
  // ro'yxat. Faqat playin bosqichi mavjud bo'lsa ko'rsatiladi (elpoTieCard — DRY).
  const playinTies = rounds.playin || [];
  const playinHtml = playinTies.length ? `
    <div class="section-label">${ET("elpo_playin_label")}</div>
    <div class="el-po-playin-list">
      ${playinTies
        .slice()
        .sort((a, b) => a.position - b.position)
        .map(t => elpoTieCard({ ...t, round: "playin" }, "left"))
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
// Ma'lumot manbai setka bilan bir xil (/el/playoff/bracket) — qoida #26 DRY.
async function elpoLoadPlayin() {
  const box = document.getElementById("el-po-playin-box");
  if (!box) return;
  if (!ELPO.bracket) {
    try { ELPO.bracket = await apiFetch("/el/playoff/bracket"); }
    catch (_) { ELPO.bracket = null; }
  }
  const br = ELPO.bracket;
  if (!br || !br.started) {
    box.innerHTML = `<div class="card">${ET("elpo_not_started")}</div>`;
    return;
  }
  const ties = (br.rounds && br.rounds.playin) || [];
  if (!ties.length) {
    box.innerHTML = `<div class="card">Qayta tasnif juftliklari hali yaratilmagan.</div>`;
    return;
  }
  box.innerHTML = `
    <div class="section-label">${ET("elpo_playin_label")}</div>
    <div class="elpo-playin-list">
      ${ties.slice().sort((x, y) => x.position - y.position).map(elpoPlayinRow).join("")}
    </div>`;
  if (typeof elpoBindBracketSides === "function") elpoBindBracketSides(box);
}

// Bitta pley-in juftligi qatori (ikki o'yin hisobi bilan)
function elpoPlayinRow(tie) {
  const l1 = tie.leg1, l2 = tie.leg2;
  // sideA = yuqori o'rin: leg1'da MEHMON (score2), leg2'da UYDA (score1)
  const a1 = (l1 && l1.score1 != null) ? l1.score2 : null;
  const b1 = (l1 && l1.score1 != null) ? l1.score1 : null;
  const a2 = (l2 && l2.score1 != null) ? l2.score1 : null;
  const b2 = (l2 && l2.score1 != null) ? l2.score2 : null;
  const line = (x, y) => (x == null || y == null)
    ? `<div class="elpo-pi-score elpo-pi-score--pending">—<span class="elpo-pi-dash">:</span>—</div>`
    : `<div class="elpo-pi-score">${x}<span class="elpo-pi-dash">:</span>${y}</div>`;

  const sideHtml = (p, won, align) => {
    if (!p || !p.user_id) {
      return `<div class="elpo-pi-side elpo-pi-side--${align}"><span class="elpo-pi-name">—</span></div>`;
    }
    const nm = escHtml(p.username ? "@" + p.username : (p.nickname || ""));
    return `
      <div class="elpo-pi-side elpo-pi-side--${align}${won ? " winner" : ""} elpo-side--clickable"
           data-elpo-player="${p.user_id}"
           data-elpo-nick="${escHtml(p.nickname || "")}"
           data-elpo-user="${escHtml(p.username || "")}"
           data-elpo-club="${escHtml(p.club_name || "")}">
        ${elClubBadge(p.club_name, 26)}
        <span class="elpo-pi-name">${nm}</span>
      </div>`;
  };

  const aWon = tie.winner_id && tie.a && tie.a.user_id === tie.winner_id;
  const bWon = tie.winner_id && tie.b && tie.b.user_id === tie.winner_id;

  return `
    <div class="elpo-pi-row">
      ${sideHtml(tie.a, aWon, "left")}
      <div class="elpo-pi-scores">${line(a1, b1)}${line(a2, b2)}</div>
      ${sideHtml(tie.b, bWon, "right")}
    </div>`;
}

// ---- PROFIL: PLAY-OFF O'YINLARIM ----
// 2026-07-21: dizayn va natija oqimi guruh o'yinlari ("MENING O'YINLARIM",
// elRenderMatchItem) bilan BIR XIL: .el-match-wrap karta, umumiy #modal-result
// modali (klub logolari + input-score1/2), tasdiqlash — bir bosishda, rad — alohida qator.

async function elpoLoadMyMatches(force = false) {
  const box = document.getElementById("el-po-my-box");
  if (!box) return;
  try {
    ELPO.my = await apiFetch("/el/playoff/my-matches");
  } catch (_) { ELPO.my = null; }
  // 2026-07-21: PIR-PIRASH TUZATISH — har profil renderida qayta yozish o'rniga
  // ma'lumot O'ZGARMAGAN bo'lsa DOM tegilmaydi (JSON solishtiruv).
  const json = JSON.stringify(ELPO.my && ELPO.my.matches);
  if (!force && json === ELPO._lastMyJson && box.innerHTML !== "") return;
  ELPO._lastMyJson = json;
  elpoRenderMyBox();
}

// Faqat renderlash (fetch'siz) — chat ochilganda 💬 → "Natija" almashinuvi uchun
function elpoRenderMyBox() {
  const box = document.getElementById("el-po-my-box");
  if (!box) return;
  if (!ELPO.my || !ELPO.my.started || !ELPO.my.matches.length) { box.innerHTML = ""; return; }
  box.innerHTML = `
    <div class="section-label">PLAY-OFF O'YINLARIM</div>
    <div class="matches-list">${ELPO.my.matches.map(elpoMyMatchItem).join("")}</div>`;
  if (typeof applyIcons === "function") applyIcons(box);
  box.querySelectorAll("[data-elpo-result]").forEach(b =>
    b.addEventListener("click", () => elpoOpenResultModal(parseInt(b.dataset.elpoResult))));
  box.querySelectorAll("[data-elpo-chat]").forEach(b =>
    b.addEventListener("click", () => elpoChatThenResult(parseInt(b.dataset.elpoChat))));
  box.querySelectorAll("[data-elpo-open-match]").forEach(b =>
    b.addEventListener("click", () => elpoChatThenResult(parseInt(b.dataset.elpoOpenMatch))));
  box.querySelectorAll("[data-elpo-confirm]").forEach(b =>
    b.addEventListener("click", () => void elpoConfirm(parseInt(b.dataset.elpoConfirm), true)));
  box.querySelectorAll("[data-elpo-reject]").forEach(b =>
    b.addEventListener("click", () => void elpoConfirm(parseInt(b.dataset.elpoReject), false)));
}

// 💬 yoki logolar bosilganda: VS-oyna (ikkita chat) + "Natija" tugmasi ochiladi
// (guruh elOpenChatThenResult oqimi). Faqat LOKAL box qayta chiziladi —
// to'liq renderEuropaLeague chaqirilmaydi (pir-pirash bo'lmasin).
function elpoChatThenResult(matchId) {
  if (!ELPO.chatOpened) ELPO.chatOpened = new Set();
  ELPO.chatOpened.add(matchId);
  elpoOpenOpponentModal(matchId);
  elpoRenderMyBox();
}

function elpoLegLabel(m) {
  const r = ELPO_ROUND_NAMES[m.round] || m.round;
  return m.round === "final" ? r : `${r} · ${m.leg}-o'yin`;
}

// Guruh o'yinlari kartasi (elRenderMatchItem) bilan bir xil tuzilma
function elpoMyMatchItem(m) {
  const meId = ELPO.my.me_id;
  const isHome = m.player1_id === meId;                 // player1 = uy egasi
  const mine = m.submitted_by === meId;
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";

  // 2026-07-21: o'qilmagan chat rozetka — RAQIB logosi ustida (guruh kartasi kabi,
  // play-off kalitlari "p{id}" — /el/matches/unread endi ularni ham qaytaradi)
  const unreadCount = (typeof EL !== "undefined" && EL.unread && EL.unread.by_match
    && EL.unread.by_match["p" + m.id]) || 0;
  const unreadBadge = unreadCount > 0
    ? `<span class="chat-badge">${unreadCount > 9 ? "9+" : unreadCount}</span>`
    : "";
  const center = `
    <span class="el-mc-logo match-badge-wrap">${elClubBadge(m.p1_club, 26)}${isHome ? "" : unreadBadge}</span>
    <span class="match-score">${score}</span>
    <span class="el-mc-logo match-badge-wrap">${elClubBadge(m.p2_club, 26)}${isHome ? unreadBadge : ""}</span>`;

  let statusCls = "status--pending", statusText = "KUTILMOQDA";
  if (m.status === "awaiting_confirmation") { statusCls = "status--awaiting"; statusText = "TASDIQ"; }
  if (m.status === "confirmed")             { statusCls = "status--confirmed"; statusText = "TASDIQLANDI"; }

  let action = "";
  if (m.status === "pending") {
    // 2026-07-21: guruh oqimi bilan bir xil — avval 💬 chat, chat ochilgach "Natija"
    action = (ELPO.chatOpened && ELPO.chatOpened.has(m.id))
      ? `<button class="match-action-btn" data-elpo-result="${m.id}">${ET("el_result")}</button>`
      : `<button class="match-action-btn match-chat-btn" data-elpo-chat="${m.id}" title="Avval raqib bilan kelishing">${ICON.get("chat", 18)}</button>`;
  } else if (m.status === "awaiting_confirmation") {
    action = mine
      ? `<span class="match-waiting">${ET("el_pending")}</span>`
      : `<button class="match-action-btn" data-elpo-confirm="${m.id}">${ICON.get("check", 16)}</button>`;
  }
  const reject = (m.status === "awaiting_confirmation" && !mine)
    ? `<div class="el-score-row"><button class="btn" data-elpo-reject="${m.id}">${ICON.get("cross", 15)} ${ET("el_reject")}</button></div>` : "";

  const venue = isHome
    ? `<span class="el-venue el-venue--home">UY</span>`
    : `<span class="el-venue el-venue--away">MEHMON</span>`;

  // 2-o'yinda 1-o'yin hisobi (agregat konteksti)
  const ctx = (m.leg === 2 && m.other_leg_score1 !== null && m.other_leg_score1 !== undefined)
    ? `<div class="el-po-ctx">1-o'yin: ${m.other_leg_score1} : ${m.other_leg_score2}</div>` : "";

  return `
    <div class="el-match-wrap">
      <div class="el-match-head">
        <span class="el-match-round">${escHtml(elpoLegLabel(m))}</span><span class="el-match-id">#${m.id}</span>
        ${venue}
        <span class="match-status ${statusCls}">${statusText}</span>
      </div>
      <div class="el-match-body">
        <div class="match-center match-center--clickable" data-elpo-open-match="${m.id}">${center}</div>
        ${action}
      </div>
      ${ctx}
      ${reject}
    </div>`;
}

// ---- VS-oyna: IKKITA chat (bot chati + Telegram) — el_chat.js elOpenOpponentModal naqshi ----
// 2026-07-21: logolar juftligi yoki 💬 bosilganda ochiladi. WebApp chati
// /el/playoff/matches prefiksi bilan ishlaydi (guruh chatidan alohida jadval).

function elpoOpenOpponentModal(matchId) {
  const m = (ELPO.my?.matches || []).find(x => x.id === matchId);
  if (!m) return;
  const t = APP.t || {};
  const meId = ELPO.my.me_id;
  const iAmP1 = m.player1_id === meId;

  const me  = { nick: iAmP1 ? m.p1_nick : m.p2_nick,
                club: iAmP1 ? m.p1_club : m.p2_club,
                username: iAmP1 ? m.p1_user : m.p2_user };
  const opp = { nick: iAmP1 ? m.p2_nick : m.p1_nick,
                club: iAmP1 ? m.p2_club : m.p1_club,
                username: iAmP1 ? m.p2_user : m.p1_user };

  let modal = document.getElementById("modal-elpo-opponent");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "modal-elpo-opponent";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }

  const side = (p) => `
    <div class="opp-side">
      <div class="el-vs-logo">${elClubBadge(p.club, 72)}</div>
      <div class="opp-club">${escHtml(p.club || p.nick || "—")}</div>
      <div class="opp-user">${p.username ? "@" + escHtml(p.username) : "—"}</div>
    </div>`;

  const tgBtn = opp.username
    ? `<button class="opp-chat-btn" id="elpo-opp-tg">${ICON.get("chat", 18)} ${escHtml(t.opp_write_button || "Raqib chatiga yozish")}</button>`
    : `<div class="opp-no-contact">${escHtml(t.opp_no_contact || "Raqib bilan bog'lanib bo'lmaydi")}</div>`;

  modal.innerHTML = `
    <div class="modal-box opp-modal-box">
      <button class="modal-close" id="elpo-opp-close">${ICON.get("close", 18)}</button>
      <div class="opp-vs">
        ${side(me)}
        <div class="opp-vs-sep">VS</div>
        ${side(opp)}
      </div>
      ${typeof roomCodeBtnHtml === "function" ? roomCodeBtnHtml(matchId, "el_po") : ""}
      <button class="opp-chat-btn opp-webchat-btn" id="elpo-opp-webchat">
        ${ICON.get("chat", 18)} ${escHtml(t.webchat_open || "Chatni ochish")}
      </button>
      ${tgBtn}
    </div>`;
  modal.classList.remove("hidden");
  if (typeof applyIcons === "function") applyIcons(modal);

  const close = () => modal.classList.add("hidden");
  document.getElementById("elpo-opp-close").addEventListener("click", close);
  modal.addEventListener("click", (e) => { if (e.target === modal) close(); });

  document.getElementById("elpo-opp-webchat").addEventListener("click", () => {
    close();
    openWebChat(m.id, opp.nick || "Raqib", "/el/playoff/matches");   // api.js webchat (DRY)
  });
  document.getElementById("elpo-opp-tg")?.addEventListener("click", () => {
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

// ---- Natija modali: guruh o'yinlaridagi UMUMIY #modal-result (elOpenResultModal naqshi) ----

function elpoOpenResultModal(matchId) {
  const m = (ELPO.my?.matches || []).find(x => x.id === matchId);
  if (!m) { showToast(ET("el_match_404")); return; }
  const modal = document.getElementById("modal-result");
  if (!modal) { showToast(ET("el_modal_404")); return; }

  ELPO._resultMatchId = matchId;   // submitMatchResult() shu flag orqali play-off'ga yo'naltiradi
  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  const setLogo = (id, club) => {
    const el = document.getElementById(id);
    if (!el) return;
    const logo = (typeof elClubLogo === "function") ? elClubLogo(club) : null;
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

const ELPO_ERRORS = {
  draw_not_allowed: ET("elpo_err_draw"),
  aggregate_draw_not_allowed: ET("elpo_err_agg_draw"),
  wrong_status: ET("elpo_err_status"),
  not_participant: ET("elpo_err_not_part"),
  cannot_confirm_own: ET("elpo_err_own"),
  already_started: ET("elpo_err_started"),
  groups_not_finished: ET("elpo_err_groups"),
  not_drawn: ET("elpo_err_not_drawn"),
  // 2026-08: setka bosqichi (2-bosqich) xatolari
  playin_not_started: "Avval qayta tasnifni boshlang.",
  playin_not_finished: "Qayta tasnif hali tugamagan — barcha 16 o'yin tasdiqlanishi kerak.",
  bracket_already_started: "Setka allaqachon ochilgan.",
  not_enough_players: "Reytingda yetarli ishtirokchi yo'q (24 ta kerak).",
  bracket_failed: "Setkani ochishda xatolik.",
};

// Umumiy modaldagi "Yuborish" shu funksiyaga yo'naltiriladi (api.js submitMatchResult)
async function elpoSubmitResultFromModal() {
  const id = ELPO._resultMatchId;
  const s1 = Number(document.getElementById("input-score1").value || 0);
  const s2 = Number(document.getElementById("input-score2").value || 0);
  try {
    await apiFetch(`/el/playoff/submit-result?match_id=${id}&score1=${s1}&score2=${s2}`, { method: "POST" });
    ELPO._resultMatchId = null;
    closeResultModal();
    showToast(ET("el_toast_result_sent"));
    void elpoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (ELPO_ERRORS[e.message] || e.message));
  }
}

async function elpoConfirm(matchId, accept) {
  try {
    await apiFetch(`/el/playoff/confirm-result?match_id=${matchId}&accept=${accept}`, { method: "POST" });
    showToast(accept ? ET("elpo_confirmed") : ET("elpo_rejected"));
    void elpoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (ELPO_ERRORS[e.message] || e.message));
  }
}

// ---- Kataklarni bog'lovchi chiziqlar (2026-07-21, WC wcDrawBracketLines naqshi) ----
// YeL bosqichlari: r16 → r8 → r4 → final. Keyingi juftlik pos = floor(pos/2).
// Final markazda (side="center") — chap 1/2 final unga o'ngdan, o'ng 1/2 final chapdan ulanadi.
function elpoDrawBracketLines() {
  const box = document.getElementById("el-po-bracket-box");
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

async function elpoAdminStart(btn) {
  if (!confirm(ET("elpo_start_ask"))) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/el/admin/playoff/start", { method: "POST" });
    showToast(`✅ Qayta tasnif boshlandi (${r.playin_pairs} juftlik)`);
    if (typeof elRenderAdminPage === "function") void elRenderAdminPage();
  } catch (e) {
    // 2026-08-28: "Guruh o'yinlari hali tugamagan" xabari qaysi o'yin
    // bloklayotganini aytmaydi — diagnostikani so'rab, adminga ro'yxatni
    // ko'rsatamiz (faqat o'qish, hech narsa o'zgarmaydi).
    if (e.message === "groups_not_finished") {
      await elpoShowGroupBlocking(btn);
      return;   // btn holati elpoShowGroupBlocking ichida boshqariladi
    } else {
      showToast("❌ " + (ELPO_ERRORS[e.message] || e.message));
    }
    btn.disabled = false;
  }
}

// Bloklayotgan o'yinlarni ko'rsatadi va majburiy yopishni taklif qiladi.
// 2026-08-28: admin 23:30 deadline'ni kutmasin — ro'yxatni ko'rib, tasdiqlasa
// o'yinlar darhol yopiladi va qayta tasnif AVTOMATIK boshlanadi (bitta oqim).
async function elpoShowGroupBlocking(btn) {
  let d;
  try {
    d = await apiFetch("/el/admin/group-blocking");
  } catch (_) {
    showToast("❌ " + ET("elpo_err_groups"));
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
    const r = await apiFetch("/el/admin/group/force-close", { method: "POST" });
    showToast(`✅ ${r.awaiting_resolved + r.pending_resolved} o'yin yopildi (0:0: ${r.pending_resolved})`);
  } catch (e) {
    const msg = {
      group_not_over: "Guruh bosqichi hali tugamagan — majburiy yopib bo'lmaydi.",
      not_started: "YeL turlari boshlanmagan.",
      not_drawn: "YeL qur'asi o'tkazilmagan.",
      force_close_failed: "Yopishda xatolik.",
    }[e.message] || e.message;
    showToast("❌ " + msg);
    return;
  }

  // O'yinlar yopildi — endi qayta tasnifni qayta urinamiz
  try {
    const r = await apiFetch("/el/admin/playoff/start", { method: "POST" });
    showToast(`✅ Qayta tasnif boshlandi (${r.playin_pairs} juftlik)`);
    if (typeof elRenderAdminPage === "function") void elRenderAdminPage();
  } catch (e) {
    showToast("❌ " + (ELPO_ERRORS[e.message] || e.message));
    if (btn) btn.disabled = false;
  }
}

// 2026-08: 2-BOSQICH — asosiy setkani ochish (qayta tasnif tugagach)
async function elpoAdminStartBracket(btn) {
  if (!confirm("Asosiy setka (1/8 final) ochilsinmi?\n\nQayta tasnif g'oliblari top-8 bilan juftlanadi. Bu amalni ortga qaytarib bo'lmaydi.")) return;
  btn.disabled = true;
  try {
    const r = await apiFetch("/el/admin/playoff/start-bracket", { method: "POST" });
    showToast(`✅ Setka ochildi (${r.r16_pairs} juftlik)`);
    ELPO.bracket = null;   // keshni tozalaymiz — yangi setka yuklansin
    if (typeof elRenderAdminPage === "function") void elRenderAdminPage();
  } catch (e) {
    showToast("❌ " + (ELPO_ERRORS[e.message] || e.message));
    btn.disabled = false;
  }
}
