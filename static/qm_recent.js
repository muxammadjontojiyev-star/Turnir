/* qm_recent.js — TEZKOR O'YIN: «So'nggi o'yinlarim» eFootball Divizion uslubida (2026-10-22).
   Bitta gorizontal qator: raqib rasmi + ostida rangli hisob (yashil=g'alaba, kulrang=durang, qizil=mag'lubiyat).
   Ishlatadi: qm.js dagi qmAvatar, qmWho, qmT, escHtml. Chaqiriladi: qm.js qmRatingHtml. */

function qmRecentResult(m) {
  return m.my_score > m.opp_score ? "win" : m.my_score < m.opp_score ? "loss" : "draw";
}

function qmRecentTileHtml(m) {
  const res = qmRecentResult(m);
  const who = qmWho(m.opponent);
  const d = m.my_delta || 0;
  const pts = m.rated ? `${d > 0 ? "+" : ""}${d}` : "—";
  return `<div class="qm-rc is-${res}" title="${escHtml(who)}">
      ${qmAvatar(m.opponent && m.opponent.id, who, "qm-ava--md")}
      <span class="qm-rc-score">${m.my_score}-${m.opp_score}</span>
      <small class="qm-rc-pts">${escHtml(pts)}</small>
    </div>`;
}

function qmRecentStripHtml(list) {
  const items = (list || []).filter(m => m.status !== "cancelled").map(qmRecentTileHtml).join("");
  return items ? `<div class="card qm-rc-strip">${items}</div>` : "";
}
