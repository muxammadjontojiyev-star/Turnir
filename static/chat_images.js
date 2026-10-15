// =============================================================
//  chat_images.js — bot chatida (WebApp chati) rasm yuborish (2026-10-11)
//  Barcha rejimlar: liga, ChL (+pley-off), YeL (+pley-off), Divizion, JCh (+pley-off),
//  shaxsiy turnir. Backend: POST /chat/image, GET /chat/image/{token} (chat_images_api.py).
//  Chatda rasm xabari matni: "📷 [img:<32 hex>]" — renderer'lar uni rasmga aylantiradi.
//  Rasm ochiq <img src> havolasi emas: auth sarlavhasi bilan blob olinadi (qoida #34).
//  Global: APP, WC_CHAT, API_BASE, apiFetch, escHtml, showToast, loadWebChatMessages,
//          wcLoadWebChatMessages.
// =============================================================

const CHAT_IMG_MAX_SIDE = 1600;          // px — katta tomon (backend chegarasi 2.5 MB)
const CHAT_IMG_QUALITY = 0.82;           // JPEG sifati
const CHAT_IMG_RE = /^📷 \[img:([0-9a-f]{32})\]$/;

// Chat URL prefiksi → backend rejim nomi (chat_report.MODES kalitlari)
const CHAT_IMG_MODES = {
  "/matches": "league", "/cl/matches": "cl", "/cl/playoff/matches": "cl_po",
  "/el/matches": "el", "/el/playoff/matches": "el_po", "/div/matches": "div",
  "/ac/matches": "ac", "/ac/playoff/matches": "ac_po",   // 2026-10-15
  "/tb/matches": "tb",                                   // 2026-10-16: Teamlar jangi
  "/pt/matches": "pt",
};

const CHAT_IMG = { cache: {}, loading: {}, busy: false, ctx: null };

function chatImageToken(text) {
  const m = CHAT_IMG_RE.exec(String(text || "").trim());
  return m ? m[1] : null;
}

// Xabar tanasi: rasm bo'lsa — rasm (yoki yuklanayotgan joy), aks holda matn
function chatMessageBodyHtml(msg, textHtml) {
  const tok = chatImageToken(msg.text);
  if (!tok) return `<span class="webchat-text">${textHtml}</span>`;
  const src = CHAT_IMG.cache[tok];
  return src
    ? `<img class="webchat-img" src="${src}" alt="" data-chat-img-open="${tok}">`
    : `<span class="webchat-img webchat-img--loading" data-chat-img="${tok}">📷</span>`;
}

// Chizilgan ro'yxatdagi hali yuklanmagan rasmlarni olib keladi (har token bir marta)
function chatLoadImages(box) {
  if (!box) return;
  box.querySelectorAll("[data-chat-img]").forEach(el => {
    const tok = el.dataset.chatImg;
    if (CHAT_IMG.cache[tok] || CHAT_IMG.loading[tok]) return;
    CHAT_IMG.loading[tok] = true;
    fetch(`${API_BASE}/chat/image/${tok}`, {
      headers: { "X-Telegram-Init-Data": window.Telegram?.WebApp?.initData || "" },
    }).then(r => { if (!r.ok) throw new Error(String(r.status)); return r.blob(); })
      .then(blob => {
        CHAT_IMG.cache[tok] = URL.createObjectURL(blob);
        const nearBottom = (box.scrollHeight - box.scrollTop - box.clientHeight) < 80;
        box.querySelectorAll(`[data-chat-img="${tok}"]`).forEach(x => {
          x.outerHTML = `<img class="webchat-img" src="${CHAT_IMG.cache[tok]}" alt="" data-chat-img-open="${tok}">`;
        });
        if (nearBottom) box.querySelectorAll("img.webchat-img").forEach(i =>
          i.addEventListener("load", () => { box.scrollTop = box.scrollHeight; }, { once: true }));
      })
      .catch(() => {
        box.querySelectorAll(`[data-chat-img="${tok}"]`).forEach(x => { x.textContent = "📷 ✕"; });
      })
      .finally(() => { delete CHAT_IMG.loading[tok]; });
  });
}

// Kiritish qatoridagi 📎 tugmasi. ctx: "app" (api.js chati) | "wc" (JCh chati)
function chatAttachBtnHtml(ctx) {
  const t = APP.t || {};
  return `<button class="webchat-attach" type="button" data-chat-attach="${ctx}" title="${escHtml(t.chat_img_send || "Rasm yuborish")}">📎</button>`;
}

function chatImgContext(ctx) {
  if (ctx === "wc") {
    return { matchId: WC_CHAT.matchId, mode: WC_CHAT.isPlayoff ? "wc_po" : "wc",
             reload: () => wcLoadWebChatMessages() };
  }
  return { matchId: APP.chatMatchId, mode: CHAT_IMG_MODES[APP.chatUrlPrefix || "/matches"] || "league",
           reload: () => loadWebChatMessages() };
}

function chatCompressImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, CHAT_IMG_MAX_SIDE / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL("image/jpeg", CHAT_IMG_QUALITY));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("bad_image")); };
    img.src = url;
  });
}

async function chatSendImage(file, btn) {
  const t = APP.t || {};
  const ctx = CHAT_IMG.ctx;
  if (CHAT_IMG.busy || !ctx || !ctx.matchId) return;    // ikki marta yuborish (qoida #38)
  CHAT_IMG.busy = true;
  if (btn) { btn.disabled = true; btn.textContent = "⏳"; }
  try {
    const image_base64 = await chatCompressImage(file);
    await apiFetch("/chat/image", {
      method: "POST",
      body: JSON.stringify({ match_id: Number(ctx.matchId), mode: ctx.mode, image_base64 }),
    });
    showToast("✅ " + (t.chat_img_sent || "Rasm yuborildi"));
    ctx.reload();
  } catch (e) {
    const msg = {
      image_too_large: t.chat_img_too_large || "Rasm juda katta",
      bad_image: t.chat_img_bad || "Rasm formati noto'g'ri (JPG/PNG)",
      too_many_images: t.chat_img_too_many || "Bu o'yinda rasm chegarasiga yetdingiz",
      chat_no_access: t.room_code_no_access || "Bu o'yinda xabar yuborib bo'lmaydi.",
    }[e.message] || (t.chat_img_failed || "Rasm yuborilmadi");
    showToast("❌ " + msg);
  } finally {
    CHAT_IMG.busy = false;
    if (btn) { btn.disabled = false; btn.textContent = "📎"; }
  }
}

// To'liq ekranda ko'rish (bosilsa yopiladi)
function chatImgLightbox(src) {
  let box = document.getElementById("chat-img-lightbox");
  if (!box) {
    box = document.createElement("div");
    box.id = "chat-img-lightbox";
    box.className = "chat-img-lightbox hidden";
    box.addEventListener("click", () => box.classList.add("hidden"));
    document.body.appendChild(box);
  }
  box.innerHTML = `<img src="${src}" alt="">`;
  box.classList.remove("hidden");
}

// Global delegatsiya: chat oynalari har poll'da qayta chiziladi (qoida #26)
if (!window._chatImgBound) {
  window._chatImgBound = true;
  const picker = document.createElement("input");
  picker.type = "file";
  picker.accept = "image/*";
  picker.style.display = "none";
  document.addEventListener("DOMContentLoaded", () => document.body.appendChild(picker));
  let pickerBtn = null;
  picker.addEventListener("change", () => {
    const file = picker.files && picker.files[0];
    picker.value = "";                       // o'sha faylni qayta tanlash mumkin bo'lsin
    if (file) void chatSendImage(file, pickerBtn);
  });
  document.addEventListener("click", (e) => {
    const att = e.target.closest ? e.target.closest("[data-chat-attach]") : null;
    if (att) {
      CHAT_IMG.ctx = chatImgContext(att.dataset.chatAttach);
      pickerBtn = att;
      if (!picker.isConnected) document.body.appendChild(picker);
      picker.click();
      return;
    }
    const img = e.target.closest ? e.target.closest("[data-chat-img-open]") : null;
    if (img) chatImgLightbox(img.getAttribute("src"));
  });
}
