// =============================================================
//  chat_dates.js — BOT CHATIDA SANA AJRATGICHLARI (2026-11-07, egasi: «huddi telegramdagidek … xabarlar qaysi sanada
//  yozilganligi ham ko'rinishi kerak»). Kun almashganda — «Bugun» / «Kecha» / «5-noyabr» (boshqa yil — yil bilan).
//  Barcha rejimlar: api.js renderWebChatMessages (liga, Divizion, ChL, YeL, OChL, KL, xususiy turnir) va
//  worldcup_chat.js wcRenderWebChatMessages (JCh). Vaqt — xabar vaqti kabi qurilma vaqtida (formatChatTime bilan bir xil).
// =============================================================

const CHAT_MONTHS = {
  uz: ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"],
  ru: ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"],
  en: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
};
const CHAT_DAY_WORDS = { uz: ["Bugun", "Kecha"], ru: ["Сегодня", "Вчера"], en: ["Today", "Yesterday"] };
const CHAT_DAY_MS = 24 * 60 * 60 * 1000;

function chatMsgDate(raw) {                          // SQLite «YYYY-MM-DD HH:MM:SS» (UTC) → Date
  if (!raw) return null;
  const s = String(raw);
  const d = new Date(s.replace(" ", "T") + (s.includes("Z") || /[+-]\d\d:?\d\d$/.test(s) ? "" : "Z"));
  return isNaN(d.getTime()) ? null : d;
}

function chatDayKey(d) { return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; }

function chatDayLabel(d) {
  const lang = (typeof APP !== "undefined" && CHAT_MONTHS[APP.lang]) ? APP.lang : "uz";
  const now = new Date();
  if (chatDayKey(d) === chatDayKey(now)) return CHAT_DAY_WORDS[lang][0];
  if (chatDayKey(d) === chatDayKey(new Date(now.getTime() - CHAT_DAY_MS))) return CHAT_DAY_WORDS[lang][1];
  const day = d.getDate(), mon = CHAT_MONTHS[lang][d.getMonth()];
  const year = d.getFullYear() !== now.getFullYear() ? ` ${d.getFullYear()}` : "";
  if (lang === "uz") return `${day}-${mon}${year}`;
  if (lang === "en") return `${mon} ${day}${year ? "," + year : ""}`;
  return `${day} ${mon}${year}`;
}

// i-xabardan oldin ajratgich kerak bo'lsa — uning HTML i (birinchi xabar yoki kun almashgan)
function chatDaySepHtml(messages, i) {
  const d = chatMsgDate(messages[i] && messages[i].created_at);
  if (!d) return "";
  const prev = i > 0 ? chatMsgDate(messages[i - 1] && messages[i - 1].created_at) : null;
  if (prev && chatDayKey(prev) === chatDayKey(d)) return "";
  return `<div class="webchat-day"><span>${escHtml(chatDayLabel(d))}</span></div>`;
}
