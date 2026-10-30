// =============================================================
//  receipt_image.js — to'lov CHEKI rasmini yuborishga tayyorlash (2026-10-30)
//  Muammo: ba'zi cheklar "Rasm yaroqsiz" chiqardi. Sabablar:
//    - telefon WebView'i faylni <img> orqali ocholmaydi (HEIC, ba'zi galereya/fayl tanlagichlari) -> onerror;
//    - xotira yetmasa canvas.toDataURL bo'sh "data:," qaytaradi -> server empty_image;
//    - uzun skrinshot (1080×6000) eng uzun tomon bo'yicha 1600px ga tushirilib, o'qib bo'lmas darajada torayardi.
//  Yechim (receiptPrepare):
//    1) createImageBitmap (EXIF burilishi bilan), bo'lmasa <img>; o'lcham — kenglik RECEIPT_MAX_W, balandlik
//       RECEIPT_MAX_H va jami RECEIPT_MAX_PIXELS dan oshmaydi (uzun skrinshot ham o'qiladi);
//    2) natija tekshiriladi (haqiqiy JPEG data URL);
//    3) siqib bo'lmasa, lekin fayl o'zi JPEG/PNG/WEBP (imzo bo'yicha) va RECEIPT_RAW_MAX_BYTES dan kichik —
//       ASL fayl yuboriladi (server imzoni baribir tekshiradi);
//    4) aks holda Error("unsupported_format") — chaqiruvchi tushunarli matn va "chekni Telegram'da yuborish" yo'lini ko'rsatadi.
//  Global: yo'q. pt_payment.js (ptCompressImage) va shop.js shu funksiyadan foydalanadi.
// =============================================================

const RECEIPT_MAX_W = 1600;
const RECEIPT_MAX_H = 6000;
const RECEIPT_MAX_PIXELS = 4000000;
const RECEIPT_QUALITIES = [0.85, 0.7, 0.55];   // server chegarasidan oshsa — pastroq sifat bilan qayta
const RECEIPT_RAW_MAX_BYTES = 2400000;        // server chegarasi 2.5 MB (pt_payment.RECEIPT_MAX_BYTES)
const RECEIPT_MIN_DATAURL = 200;              // bundan qisqa natija — bo'sh / buzilgan

async function receiptSniff(file) {
  try {
    const b = new Uint8Array(await file.slice(0, 12).arrayBuffer());
    if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return "image/jpeg";
    if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return "image/png";
    if (b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return "image/webp";
  } catch (_) { /* o'qib bo'lmadi */ }
  return null;
}

function receiptLoadImg(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => resolve({ src: img, w: img.naturalWidth || img.width, h: img.naturalHeight || img.height,
                                 done: () => URL.revokeObjectURL(url) });
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("decode")); };
    img.src = url;
  });
}

async function receiptDecode(file) {
  if (typeof createImageBitmap === "function") {
    try {
      const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
      return { src: bmp, w: bmp.width, h: bmp.height, done: () => bmp.close && bmp.close() };
    } catch (_) { /* eski WebView — <img> bilan urinamiz */ }
  }
  return receiptLoadImg(file);
}

function receiptCanvas(d) {
  const scale = Math.min(1, RECEIPT_MAX_W / d.w, RECEIPT_MAX_H / d.h, Math.sqrt(RECEIPT_MAX_PIXELS / (d.w * d.h)));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(d.w * scale));
  canvas.height = Math.max(1, Math.round(d.h * scale));
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff";                                  // shaffof PNG qora fon bo'lib qolmasin
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(d.src, 0, 0, canvas.width, canvas.height);
  let url = "";
  for (const q of RECEIPT_QUALITIES) {
    url = canvas.toDataURL("image/jpeg", q);
    if (url.length * 3 / 4 <= RECEIPT_RAW_MAX_BYTES) break;   // base64 -> bayt (taxminan)
  }
  return url;
}

function receiptReadRaw(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result || ""));
    r.onerror = () => reject(new Error("unsupported_format"));
    r.readAsDataURL(file);
  });
}

async function receiptPrepare(file) {
  if (!file || !file.size) throw new Error("empty_image");
  try {
    const d = await receiptDecode(file);
    try {
      if (d.w > 0 && d.h > 0) {
        const url = receiptCanvas(d);
        if (url.startsWith("data:image/jpeg;base64,") && url.length > RECEIPT_MIN_DATAURL
            && url.length * 3 / 4 <= RECEIPT_RAW_MAX_BYTES) return url;
      }
    } finally {
      d.done();
    }
  } catch (_) { /* ochib/siqib bo'lmadi — pastda asl fayl */ }
  const mime = await receiptSniff(file);
  if (!mime) throw new Error("unsupported_format");
  if (file.size > RECEIPT_RAW_MAX_BYTES) throw new Error("image_too_large");
  const raw = await receiptReadRaw(file);
  const comma = raw.indexOf(",");
  if (comma < 0) throw new Error("unsupported_format");
  return `data:${mime};base64,${raw.slice(comma + 1)}`;      // FileReader noto'g'ri mime yozsa ham — imzo bo'yicha
}
