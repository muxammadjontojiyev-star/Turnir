// =============================================================
//  player_card_photo.js — KARTA RASMINI O'ZI TANLASH (2026-11-05, egasi so'rovi)
//  «⚙️ Kartani sozlash» oynasining tepasida: hozirgi rasm namunasi, «📷 Rasm yuklash», «Olib tashlash».
//  Rasm telefonda kichraytiriladi (PCP_MAX_SIDE, JPEG) va POST /pcard/me/photo ga yuboriladi; server fonini
//  olib tashlab, odamni BUTUN TANASI bilan qirqadi (player_cutout.py); qirqib bo'lmasa — saqlanmaydi, sababi
//  ko'rsatiladi. DELETE /pcard/me/photo — Telegram rasmiga qaytish. Bosh adminga — xizmat holati (cutout-status).
//  Global: PCE, pceHtml (player_card_edit.js), pcardHtml, pcT, pcRemember, pcRefreshMine (player_card.js),
//  apiFetch, escHtml, showToast. Ulanish: player_card_edit.js dan KEYIN.
// =============================================================

const PCP_MAX_SIDE = 1280;
const PCP_JPEG_Q = 0.9;
const PCP = { busy: false, status: null };
const PCP_ERRORS = ["too_big", "bad_image", "too_small", "daily_limit", "no_person", "cutout_off", "cutout_failed", "busy"];

function pcpSectionHtml() {
  const c = PCE.card;
  if (!c) return "";
  const has = !!c.photo;
  return `<div class="pcp-row">
      <div class="pcp-prev">${pcardHtml(c, { size: "sm" })}</div>
      <div class="pcp-side">
        <div class="pce-label" style="margin-top:0">${escHtml(pcT("pc_photo"))}</div>
        <div class="pcp-hint">${escHtml(pcT(PCP.busy ? "pc_photo_busy" : "pc_photo_hint"))}</div>
        <label class="btn btn--primary pcp-btn${PCP.busy ? " pcp-btn--busy" : ""}">
          ${escHtml(pcT(PCP.busy ? "pc_photo_wait" : "pc_photo_pick"))}
          <input type="file" accept="image/*" id="pcp-file" hidden ${PCP.busy ? "disabled" : ""}>
        </label>
        ${has && !PCP.busy ? `<button class="btn btn--ghost pcp-btn" data-pcp="del">${escHtml(pcT("pc_photo_del"))}</button>` : ""}
      </div>
    </div>${pcpStatusHtml()}`;
}

// Bosh admin — fon xizmati holati (nima uchun ishlamayotganini ko'rish uchun)
function pcpStatusHtml() {
  const st = PCP.status;
  if (!st) return "";
  const ok = (v) => (v ? "✅" : "❌");
  return `<div class="pcp-status"><b>${escHtml(pcT("pc_cut_status"))}:</b>
      ${ok(st.enabled)} PCARD_CUTOUT · ${ok(st.onnxruntime)} onnxruntime · ${ok(st.model)} model
      ${st.last_error ? `<div class="pcp-status-err">${escHtml(st.last_error)}</div>` : ""}</div>`;
}

async function pcpLoadStatus() {
  try { PCP.status = await apiFetch("/pcard/admin/cutout-status"); } catch (_) { PCP.status = null; return; }
  pcpRerender();
}

function pcpRerender() {
  const m = document.getElementById("pce-modal");
  if (!m) return;
  PCE.cc = document.getElementById("pce-country")?.value || PCE.cc;   // tanlangan davlat yo'qolmasin
  m.innerHTML = pceHtml();
}

// Telefon rasmi (8–12 MP) → PCP_MAX_SIDE gacha JPEG dataURL (orientatsiyani brauzer to'g'rilaydi)
function pcpShrink(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, PCP_MAX_SIDE / Math.max(img.naturalWidth, img.naturalHeight));
      const cv = document.createElement("canvas");
      cv.width = Math.round(img.naturalWidth * k); cv.height = Math.round(img.naturalHeight * k);
      cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
      URL.revokeObjectURL(url);
      resolve(cv.toDataURL("image/jpeg", PCP_JPEG_Q));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("bad_image")); };
    img.src = url;
  });
}

function pcpApply(card) {
  PCE.card = pcRemember(card);
  pcRefreshMine();
}

async function pcpUpload(file) {
  if (PCP.busy || !file) return;
  if (!/^image\//.test(file.type || "")) { showToast(pcT("pc_photo_err_bad_image")); return; }
  PCP.busy = true; pcpRerender();
  try {
    const image = await pcpShrink(file);
    const card = await apiFetch("/pcard/me/photo", { method: "POST", body: JSON.stringify({ image }) });
    pcpApply(card);
    showToast(pcT(card.photo && card.photo.cut ? "pc_photo_ok" : "pc_photo_ok_plain"));
  } catch (e) {
    const code = String((e && e.message) || "");
    const key = PCP_ERRORS.find(k => code.includes(k));
    showToast(pcT(key ? `pc_photo_err_${key}` : "pc_err"));
  } finally {
    PCP.busy = false; pcpRerender();
    if (PCP.status) void pcpLoadStatus();
  }
}

async function pcpDelete() {
  if (PCP.busy) return;
  PCP.busy = true;
  try {
    pcpApply(await apiFetch("/pcard/me/photo", { method: "DELETE" }));
  } catch (_) { showToast(pcT("pc_err")); }
  finally { PCP.busy = false; pcpRerender(); }
}

document.addEventListener("change", (e) => {
  if (e.target && e.target.id === "pcp-file") void pcpUpload(e.target.files && e.target.files[0]);
});
document.addEventListener("click", (e) => {
  const t = e.target.closest ? e.target.closest('[data-pcp="del"]') : null;
  if (t && document.getElementById("pce-modal")?.contains(t)) { e.stopPropagation(); void pcpDelete(); }
}, true);

// «Kartani sozlash» ochilganda — bosh admin bo'lsa holatni ko'rsatamiz (oddiy foydalanuvchiga 403 — jim)
document.addEventListener("click", (e) => {
  if (e.target.closest && e.target.closest("[data-pcard-edit]")) { PCP.status = null; setTimeout(pcpLoadStatus, 400); }
});
