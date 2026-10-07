// =============================================================
//  pt_delete.js — SHAXSIY turnirni o'chirish (2026-10-07)
//  Faqat tashkilotchi (server ham tekshiradi: POST /pt/{id}/delete -> not_owner).
//  Ikki joyda: ro'yxatdagi kartada 🗑 tugmasi va Admin sahifasi oxirida "Turnirni o'chirish".
//  Tasdiqlash: holatga qarab ogohlantirish (to'langan summa qaytarilmaydi / natijalar o'chadi).
//  Global: PT, PTT, escHtml, apiFetch, showToast, ptLoadList.
// =============================================================

function ptDeleteHtml(t) {
  if (!t.is_owner) return "";
  return `<div class="card pt-pay pt-danger">
      <div class="pt-hint">${escHtml(PTT("pt_del_hint"))}</div>
      <button class="btn pt-btn-danger" data-pt-del="${t.id}" data-pt-name="${escHtml(t.name)}"
              data-pt-status="${escHtml(t.status)}" data-pt-paid="${escHtml(t.paid_via || "")}">🗑 ${escHtml(PTT("pt_del_btn"))}</button>
    </div>`;
}

// Ogohlantirish matni: to'langan (bir martalik) — pul qaytmaydi; boshlangan — o'yinlar va natijalar o'chadi
function ptDeleteQuestion(name, status, paid) {
  const lines = [PTT("pt_del_ask", { name })];
  if (paid === "one_time" && ["payment_review", "recruiting", "running", "finished"].includes(status)) lines.push(PTT("pt_del_ask_paid"));
  if (["running", "finished"].includes(status)) lines.push(PTT("pt_del_ask_running"));
  return lines.join("\n\n");
}

function ptBindDelete() {
  document.querySelectorAll("#pt-root [data-pt-del]").forEach(b => b.addEventListener("click", ev => {
    ev.stopPropagation();
    void ptDeleteTournament(b.dataset.ptDel, b.dataset.ptName || "", b.dataset.ptStatus || "", b.dataset.ptPaid || "");
  }));
}

async function ptDeleteTournament(tid, name, status, paid) {
  if (PT.busy || !window.confirm(ptDeleteQuestion(name, status, paid))) return;
  PT.busy = true;
  try {
    await apiFetch(`/pt/${encodeURIComponent(tid)}/delete`, { method: "POST" });
    showToast(PTT("pt_deleted"));
    if (String(PT.detailId) === String(tid)) { PT.detailId = null; PT.detail = null; PT.play = null; }
    PT.view = "list";
  } catch (e) {
    showToast(PTT(e && e.message === "not_owner" ? "pt_err_not_owner" : "pt_err_generic"));
    PT.busy = false;
    return;
  } finally {
    PT.busy = false;
  }
  await ptLoadList();
}
