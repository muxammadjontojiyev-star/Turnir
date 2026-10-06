// =============================================================
//  pt_payment.js — SHAXSIY turnir to'lovi (2026-10-02, 2-bosqich)
//  1) Tashkilotchi: chek rasmini yuklash (telefonda 1600px JPEG ga siqiladi).
//  2) Bosh admin: tekshiruvdagi to'lovlar, chek rasmi, tasdiqlash/rad etish.
//  pt.js dan KEYIN ulanadi. Global: PT, PTT, apiFetch, API_BASE, escHtml,
//  showToast, ptRender, ptOpenDetail, ptFormatPrice, ptLoadList.
// =============================================================

const PT_RECEIPT_MAX_SIDE = 1600;    // px — chek o'qilishi uchun yetarli, hajmi kichik
const PT_RECEIPT_QUALITY = 0.82;

// Tashkilotchi to'lov blokining pastki qismi (pt.js ptRenderDetail chaqiradi)
function ptPaymentActionsHtml(t) {
  if (t.status === "payment_review") {
    return `<div class="pt-note">${escHtml(PTT("pt_review_note"))}</div>`;
  }
  const rejected = t.status === "rejected"
    ? `<div class="pt-warn">${escHtml(PTT("pt_rejected_note", { reason: t.reject_reason || "—" }))}</div>` : "";
  return `${rejected}
    <input type="file" id="pt-receipt-input" accept="image/*" hidden>
    <button class="btn btn--primary" id="pt-receipt-btn">${escHtml(PTT("pt_receipt_btn"))}</button>`;
}

function ptBindPaymentActions(t) {
  const btn = document.getElementById("pt-receipt-btn");
  const input = document.getElementById("pt-receipt-input");
  if (!btn || !input) return;
  btn.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (file) void ptUploadReceipt(t.id, file, btn);
    input.value = "";                       // o'sha faylni qayta tanlash mumkin bo'lsin
  });
}

// Rasmni canvas orqali kichraytirib JPEG base64 ga aylantiradi
function ptCompressImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, PT_RECEIPT_MAX_SIDE / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", PT_RECEIPT_QUALITY));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("bad_image")); };
    img.src = url;
  });
}

async function ptUploadReceipt(tournamentId, file, btn) {
  if (PT.busy) return;                       // ikki marta yuborish (qoida #38)
  PT.busy = true;
  btn.disabled = true;
  btn.textContent = PTT("pt_receipt_sending");
  try {
    const dataUrl = await ptCompressImage(file);
    await apiFetch(`/pt/${encodeURIComponent(tournamentId)}/receipt`, {
      method: "POST", body: JSON.stringify({ image_base64: dataUrl }),
    });
    showToast(PTT("pt_receipt_sent"));
    PT.busy = false;
    await ptOpenDetail(tournamentId);
  } catch (e) {
    const map = { bad_image: "pt_err_image", empty_image: "pt_err_image",
                  image_too_large: "pt_err_image_large", wrong_status: "pt_err_wrong_status" };
    showToast(PTT(map[e && e.message] || "pt_err_generic"));
    btn.disabled = false;
    btn.textContent = PTT("pt_receipt_btn");
  } finally {
    PT.busy = false;
  }
}

// ---------------- Bosh admin: to'lovlar ----------------

async function ptOpenPayments() {
  PT.view = "payments";
  ptRender(`<div class="empty-state">${escHtml(PTT("pt_loading"))}</div>`);
  try {
    const d = await apiFetch("/pt/admin/payments");
    PT.payments = d.payments || [];
    ptRenderPayments();
  } catch (e) {
    ptRender(`<div class="empty-state">${escHtml(PTT("pt_load_err"))}</div>`);
  }
}

function ptRenderPayments() {
  const items = (PT.payments || []).map(p => `
    <div class="card pt-pay-item" data-pt-pay="${p.id}">
      <div class="pt-card-top">
        <span class="pt-card-name">${escHtml(p.name)}</span>
        <span class="pt-muted">#${p.id}</span>
      </div>
      <div class="pt-card-meta">
        <span>${escHtml(p.owner_username ? "@" + p.owner_username : (p.owner_nickname || ""))}</span>
        <b>${escHtml(ptFormatPrice(p.price_uzs))} so'm</b>
      </div>
      <div class="pt-receipt-box" id="pt-receipt-${p.id}">${escHtml(PTT("pt_loading"))}</div>
      <input class="modal-input" id="pt-reason-${p.id}" maxlength="200"
             placeholder="${escHtml(PTT("pt_reject_ph"))}">
      <div class="pt-pay-actions">
        <button class="btn btn--ghost" data-pt-reject="${p.id}">${escHtml(PTT("pt_reject"))}</button>
        <button class="btn btn--primary" data-pt-approve="${p.id}">${escHtml(PTT("pt_approve"))}</button>
      </div>
    </div>`).join("");
  ptRender(`
    <div class="section-label pt-label">${escHtml(PTT("pt_payments_title"))}</div>
    ${items || `<div class="empty-state">${escHtml(PTT("pt_payments_empty"))}</div>`}`);

  document.querySelectorAll("#pt-root [data-pt-approve]").forEach(b =>
    b.addEventListener("click", () => void ptReview(b.dataset.ptApprove, "approve", b)));
  document.querySelectorAll("#pt-root [data-pt-reject]").forEach(b =>
    b.addEventListener("click", () => void ptReview(b.dataset.ptReject, "reject", b)));
  (PT.payments || []).forEach(p => void ptLoadReceiptImage(p.id));
}

// Chek rasmi auth bilan olinadi (ochiq <img src> emas — bank ma'lumoti, qoida #34)
async function ptLoadReceiptImage(id) {
  const box = document.getElementById(`pt-receipt-${id}`);
  if (!box) return;
  try {
    const res = await fetch(`${API_BASE}/pt/admin/${encodeURIComponent(id)}/receipt`, {
      headers: { "X-Telegram-Init-Data": window.Telegram?.WebApp?.initData || "" },
    });
    if (!res.ok) throw new Error(String(res.status));
    const url = URL.createObjectURL(await res.blob());
    box.innerHTML = `<img class="pt-receipt-img" src="${url}" alt="">`;
    box.querySelector("img").addEventListener("click", () => window.open(url, "_blank"));
  } catch (e) {
    box.textContent = PTT("pt_load_err");
  }
}

async function ptReview(id, action, btn) {
  if (PT.busy) return;
  if (action === "approve" && !window.confirm(PTT("pt_approve_ask"))) return;
  PT.busy = true;
  btn.disabled = true;
  try {
    const opts = { method: "POST" };
    if (action === "reject") {
      const reason = (document.getElementById(`pt-reason-${id}`)?.value || "").trim();
      opts.body = JSON.stringify({ reason });
    }
    await apiFetch(`/pt/admin/${encodeURIComponent(id)}/${action}`, opts);
    showToast(PTT(action === "approve" ? "pt_approved_toast" : "pt_rejected_toast"));
  } catch (e) {
    showToast(PTT(e && e.message === "wrong_status" ? "pt_err_wrong_status" : "pt_err_generic"));
  } finally {
    PT.busy = false;
  }
  await ptOpenPayments();                    // navbat yangilanadi
}
