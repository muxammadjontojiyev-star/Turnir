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

// ChL kubogi ("katta quloqli" kubok) — WC png o'rniga inline SVG,
// .wc-bracket-trophy klassi bilan o'lchami WC'dagi bilan bir xil bo'ladi.
function clpoTrophySvg() {
  return `<svg class="wc-bracket-trophy" viewBox="0 0 64 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="ChL kubogi">
    <defs><linearGradient id="clpoSilver" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f4f7fb"/><stop offset=".5" stop-color="#b9c4d6"/><stop offset="1" stop-color="#8b98ad"/>
    </linearGradient></defs>
    <path d="M14 6h36l-2 26c-1.5 12-7 19-16 21-9-2-14.5-9-16-21L14 6Z" fill="url(#clpoSilver)"/>
    <path d="M14 6c-7 1-11 5-11 11 0 7 5 12 12 13l-1-8c-3-1-5-3-5-5 0-3 2-5 5-5V6ZM50 6c7 1 11 5 11 11 0 7-5 12-12 13l1-8c3-1 5-3 5-5 0-3-2-5-5-5V6Z" fill="url(#clpoSilver)"/>
    <rect x="29" y="52" width="6" height="10" fill="url(#clpoSilver)"/>
    <path d="M20 66h24l3 8H17l3-8Z" fill="url(#clpoSilver)"/>
    <path d="M18 10h28l-.6 8H18.6L18 10Z" fill="#dfe6f0" opacity=".55"/>
  </svg>`;
}

// ---- SETKA (Reyting sahifasi) ----

async function clpoLoadBracket() {
  const box = document.getElementById("cl-po-bracket-box");
  if (!box) return;
  try {
    CLPO.bracket = await apiFetch("/cl/playoff/bracket");
  } catch (_) { CLPO.bracket = null; }
  if (!CLPO.bracket || !CLPO.bracket.started) { box.innerHTML = ""; return; }
  box.innerHTML = clpoRenderBracket(CLPO.bracket);
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
  const scores = legTxt.map(v => v === null ? "–" : v).join("·");
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
    <div class="wc-bracket-card ${sideCls}">
      ${clpoTieSide(tie, "a", mirror)}
      ${clpoTieSide(tie, "b", mirror)}
    </div>`;
}

function clpoRenderBracket(data) {
  const rounds = data.rounds || {};
  const leftCols = [], rightCols = [];
  for (const rnd of CLPO_SIDE_ROUNDS) {
    const ties = rounds[rnd] || [];
    const half = Math.ceil(ties.length / 2);
    const left = ties.slice(0, half), right = ties.slice(half);
    leftCols.push(`<div class="wc-bracket-col">
      <div class="wc-bracket-round-label">${CLPO_ROUND_NAMES[rnd]}</div>
      ${left.map(t => clpoTieCard(t, "left")).join("")}</div>`);
    rightCols.unshift(`<div class="wc-bracket-col">
      <div class="wc-bracket-round-label">${CLPO_ROUND_NAMES[rnd]}</div>
      ${right.map(t => clpoTieCard(t, "right")).join("")}</div>`);
  }
  const finals = rounds["final"] || [];
  const champ = data.champion;
  const champHtml = champ ? `
    <div class="cl-po-champion">
      ${champ.club_name ? clClubBadge(champ.club_name, 30) : ""}
      <div class="cl-po-champion-name">🏆 ${escHtml(champ.username ? "@" + champ.username : (champ.nickname || ""))}</div>
      <div class="cl-po-champion-label">CHEMPION</div>
    </div>` : "";
  const centerCol = `<div class="wc-bracket-col wc-bracket-col--center">
    ${clpoTrophySvg()}
    ${finals.length ? `<div class="wc-bracket-round-label wc-bracket-final-label">Final</div>${finals.map(t => clpoTieCard(t, "left")).join("")}` : ""}
    ${champHtml}
  </div>`;
  return `
    <div class="section-label">PLAY-OFF SETKASI</div>
    <div class="wc-bracket-scroll">
      <div class="wc-bracket-inner">
        <div class="wc-bracket wc-bracket--two-sided">
          ${leftCols.join("")}
          ${centerCol}
          ${rightCols.join("")}
        </div>
      </div>
    </div>`;
}

// ---- PROFIL: PLAY-OFF O'YINLARIM ----

async function clpoLoadMyMatches() {
  const box = document.getElementById("cl-po-my-box");
  if (!box) return;
  try {
    CLPO.my = await apiFetch("/cl/playoff/my-matches");
  } catch (_) { CLPO.my = null; }
  if (!CLPO.my || !CLPO.my.started || !CLPO.my.matches.length) { box.innerHTML = ""; return; }
  box.innerHTML = `
    <div class="section-label">PLAY-OFF O'YINLARIM</div>
    ${CLPO.my.matches.map(clpoMyMatchItem).join("")}`;
  box.querySelectorAll("[data-clpo-open]").forEach(b =>
    b.addEventListener("click", () => clpoOpenModal(parseInt(b.dataset.clpoOpen))));
  box.querySelectorAll("[data-clpo-reject]").forEach(b =>
    b.addEventListener("click", () => void clpoReject(parseInt(b.dataset.clpoReject))));
}

function clpoLegLabel(m) {
  const r = CLPO_ROUND_NAMES[m.round] || m.round;
  return m.round === "final" ? r : `${r} · ${m.leg}-o'yin`;
}

function clpoMyMatchItem(m) {
  const meId = CLPO.my.me_id;
  const iAmP1 = m.player1_id === meId;
  const oppNick = iAmP1 ? (m.p2_user ? "@" + m.p2_user : m.p2_nick) : (m.p1_user ? "@" + m.p1_user : m.p1_nick);
  const oppClub = iAmP1 ? m.p2_club : m.p1_club;
  const homeTxt = iAmP1 ? "🏠 Uyda" : "🚌 Mehmonda";
  const hasScore = m.score1 !== null && m.score1 !== undefined;
  const score = hasScore ? `${m.score1} : ${m.score2}` : "— : —";

  // 2-o'yin uchun 1-o'yin natijasi (agregat konteksti)
  let ctx = "";
  if (m.leg === 2 && m.other_leg_score1 !== null && m.other_leg_score1 !== undefined) {
    ctx = `<div class="cl-po-ctx">1-o'yin: ${m.other_leg_score1} : ${m.other_leg_score2}</div>`;
  }

  let action = "";
  if (m.status === "pending") {
    action = `<button class="btn btn--primary btn--sm" data-clpo-open="${m.id}">Natija kiritish</button>`;
  } else if (m.status === "awaiting_confirmation") {
    action = (m.submitted_by === meId)
      ? `<span class="cl-po-wait">⏳ Raqib tasdig'i kutilmoqda</span>`
      : `<button class="btn btn--primary btn--sm" data-clpo-open="${m.id}">✅ Tasdiqlash</button>
         <button class="btn btn--ghost btn--sm" data-clpo-reject="${m.id}">❌</button>`;
  }

  return `
    <div class="card cl-po-match" data-clpo-id="${m.id}">
      <div class="cl-po-match-top">
        <span class="cl-po-round">${escHtml(clpoLegLabel(m))}</span>
        <span class="cl-po-home">${homeTxt}</span>
      </div>
      <div class="cl-po-match-mid">
        ${oppClub ? clClubBadge(oppClub, 22) : ""}
        <span class="cl-po-opp">${escHtml(oppNick || "—")}</span>
        <span class="match-score">${score}</span>
      </div>
      ${ctx}
      <div class="cl-po-actions">${action}</div>
    </div>`;
}

// ---- Natija modali (Divizion naqshi: .modal + .score-input) ----

function clpoOpenModal(matchId) {
  const m = (CLPO.my?.matches || []).find(x => x.id === matchId);
  if (!m) return;
  CLPO.activeMatch = m;
  const isConfirm = m.status === "awaiting_confirmation";
  const p1 = m.p1_user ? "@" + m.p1_user : (m.p1_nick || "—");
  const p2 = m.p2_user ? "@" + m.p2_user : (m.p2_nick || "—");

  let modal = document.getElementById("cl-po-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "cl-po-modal";
    modal.className = "modal hidden";
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div class="modal-box">
      <div class="modal-title">${escHtml(clpoLegLabel(m))} — ${isConfirm ? "tasdiqlash" : "natija kiritish"}</div>
      <div class="score-input-row">
        <div class="score-input-group">
          <div style="font-size:11px;text-align:center;margin-bottom:4px">🏠 ${escHtml(p1)}</div>
          <input id="cl-po-score1" class="score-input" type="number" min="0" max="99"
                 value="${isConfirm ? m.score1 : 0}" ${isConfirm ? "disabled" : ""} />
        </div>
        <span class="score-separator">:</span>
        <div class="score-input-group">
          <div style="font-size:11px;text-align:center;margin-bottom:4px">${escHtml(p2)}</div>
          <input id="cl-po-score2" class="score-input" type="number" min="0" max="99"
                 value="${isConfirm ? m.score2 : 0}" ${isConfirm ? "disabled" : ""} />
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn--ghost" id="cl-po-cancel">Bekor</button>
        <button class="btn btn--primary" id="cl-po-submit">${isConfirm ? "✅ Tasdiqlash" : "Yuborish"}</button>
      </div>
    </div>`;
  modal.classList.remove("hidden");
  document.getElementById("cl-po-cancel").addEventListener("click", () => modal.classList.add("hidden"));
  document.getElementById("cl-po-submit").addEventListener("click", (e) => void clpoSubmitFromModal(e.target, isConfirm));
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

async function clpoSubmitFromModal(btn, isConfirm) {
  const m = CLPO.activeMatch;
  if (!m) return;
  btn.disabled = true;
  try {
    if (isConfirm) {
      await apiFetch(`/cl/playoff/confirm-result?match_id=${m.id}&accept=true`, { method: "POST" });
      showToast("✅ Tasdiqlandi");
    } else {
      const s1 = parseInt(document.getElementById("cl-po-score1").value);
      const s2 = parseInt(document.getElementById("cl-po-score2").value);
      if (isNaN(s1) || isNaN(s2)) { showToast("❌ Hisobni kiriting"); btn.disabled = false; return; }
      await apiFetch(`/cl/playoff/submit-result?match_id=${m.id}&score1=${s1}&score2=${s2}`, { method: "POST" });
      showToast("✅ Natija yuborildi");
    }
    document.getElementById("cl-po-modal").classList.add("hidden");
    void clpoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (CLPO_ERRORS[e.message] || e.message));
    btn.disabled = false;
  }
}

async function clpoReject(matchId) {
  try {
    await apiFetch(`/cl/playoff/confirm-result?match_id=${matchId}&accept=false`, { method: "POST" });
    showToast("Rad etildi — natija qayta kiritilsin");
    void clpoLoadMyMatches();
  } catch (e) {
    showToast("❌ " + (CLPO_ERRORS[e.message] || e.message));
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
