// =============================================================
//  pt_fix.js — SHAXSIY turnir: tashkilotchi/admin natijani tuzatadi (Match ID bo'yicha)
//  2026-10-07: pt_play.js'dan ajratildi (qoida #21). Global: PTT, escHtml, apiFetch, showToast,
//  ptStageLabel, ptPlayAction, ptPlayErr.
// =============================================================


async function ptFixLoad(tid) {
  const id = Number(document.getElementById("pt-fix-id")?.value || 0);
  const box = document.getElementById("pt-fix-box");
  if (!id || !box) return;
  try {
    const m = await apiFetch(`/pt/owner/match/${encodeURIComponent(id)}`);
    box.innerHTML = `
      <div class="match-item pt-match">
        <div class="pt-match-head"><span>${escHtml(ptStageLabel(m))}</span><span class="pt-muted">#${m.id}</span></div>
        <div class="pt-match-row"><b>${escHtml(m.player1 || "—")}</b><span class="pt-score">${m.score1 != null ? `${m.score1} : ${m.score2}` : "— : —"}</span><b>${escHtml(m.player2 || "—")}</b></div>
        <div class="pt-res-form">
          <input class="modal-input pt-num" type="number" min="0" max="99" inputmode="numeric" id="pt-fix-s1" value="${m.score1 ?? ""}">
          <span>:</span>
          <input class="modal-input pt-num" type="number" min="0" max="99" inputmode="numeric" id="pt-fix-s2" value="${m.score2 ?? ""}">
          <button class="pt-mini pt-mini--ok" id="pt-fix-save">${escHtml(PTT("pt_fix_save"))}</button>
        </div>
        ${m.can_cancel && m.status !== "pending" ? `<button class="pt-mini pt-mini--no" id="pt-fix-cancel">${escHtml(PTT("pt_fix_cancel"))}</button>` : ""}
      </div>`;
    document.getElementById("pt-fix-save").addEventListener("click", () => {
      const s1 = document.getElementById("pt-fix-s1").value, s2 = document.getElementById("pt-fix-s2").value;
      if (s1 === "" || s2 === "") return;
      void ptPlayAction(tid, `/pt/owner/match/${id}/set`, { score1: Number(s1), score2: Number(s2) }, "pt_fix_saved");
    });
    document.getElementById("pt-fix-cancel")?.addEventListener("click", () =>
      void ptPlayAction(tid, `/pt/owner/match/${id}/cancel`, null, "pt_fix_cancelled"));
  } catch (e) {
    box.innerHTML = "";
    showToast(ptPlayErr(e));
  }
}

