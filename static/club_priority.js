// =============================================================
//  club_priority.js — liga klubini tanlashda NAVBAT (bosh sahifa banneri, 2026-10-18)
//  Yangi mavsum ochilgach: o'tgan mavsumni oxirigacha o'ynaganlar darhol, yangilar keyinroq,
//  tashlab ketganlar eng oxirida klub tanlaydi. Backend: club_priority.py, GET /club-priority/me;
//  /register navbat kelmagan bo'lsa "priority_wait" qaytaradi.
//  api.js loadHome() -> clubPriorityLoad(); registerToLeague xatosi -> clubPriorityWaitText().
//  Global: APP, apiFetch, escHtml.
// =============================================================

const CLUB_PRIO_TXT = {
  uz: {
    finished: "✅ Siz o'tgan mavsumni oxirigacha o'ynadingiz — klubni birinchilardan bo'lib tanlaysiz!",
    wait_new: "⏳ Hozir o'tgan mavsumni oxirigacha o'ynaganlar klub tanlayapti. Sizning navbatingiz: {t}",
    wait_abandoned: "⏳ O'tgan mavsumda turnirni tashlab ketganingiz sababli klub tanlash navbatingiz oxirida: {t}",
    open_after: "Navbat: oxirigacha o'ynaganlar birinchi, keyin yangilar, oxirida tashlab ketganlar. Mavsumni oxirigacha o'ynang — keyingi mavsumda birinchi tanlaysiz.",
    toast: "Klub tanlash navbatingiz hali kelmadi: {t}",
  },
  ru: {
    finished: "✅ Вы доиграли прошлый сезон до конца — выбираете клуб одним из первых!",
    wait_new: "⏳ Сейчас клубы выбирают те, кто доиграл прошлый сезон. Ваша очередь: {t}",
    wait_abandoned: "⏳ Вы бросили турнир в прошлом сезоне, поэтому выбираете клуб последним: {t}",
    open_after: "Очередь: сначала доигравшие до конца, затем новые, в конце — бросившие. Доиграйте сезон — в следующем выберете первым.",
    toast: "Ваша очередь выбора клуба ещё не наступила: {t}",
  },
  en: {
    finished: "✅ You finished last season — you pick your club among the first!",
    wait_new: "⏳ Players who finished last season are picking clubs now. Your turn: {t}",
    wait_abandoned: "⏳ You left the tournament last season, so you pick your club last: {t}",
    open_after: "Order: those who finished first, then new players, then those who left. Finish the season to pick first next time.",
    toast: "Your turn to pick a club hasn't come yet: {t}",
  },
};

function clubPrioT(key, t) {
  const d = CLUB_PRIO_TXT[APP.lang] || CLUB_PRIO_TXT.uz;
  return (d[key] || CLUB_PRIO_TXT.uz[key] || "").replace("{t}", t || "");
}

// ISO (UTC) -> "19.10 18:00" Toshkent vaqtida
function clubPrioTime(iso) {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat("ru-RU", { timeZone: "Asia/Tashkent", day: "2-digit", month: "2-digit",
      hour: "2-digit", minute: "2-digit" }).format(new Date(iso)).replace(",", "");
  } catch (_) { return iso.slice(0, 16).replace("T", " "); }
}

function clubPriorityWaitText() {
  return clubPrioT("toast", clubPrioTime(APP.clubPriority && APP.clubPriority.opens_at));
}

function clubPriorityRender() {
  const box = document.getElementById("club-priority-note");
  if (!box) return;
  const p = APP.clubPriority;
  // Navbat faol emas yoki foydalanuvchi allaqachon ro'yxatdan o'tgan — banner kerak emas
  if (!p || !p.active || (APP.profileData && APP.profileData.league_id)) { box.classList.add("hidden"); return; }
  let main, cls;
  if (p.tier === "finished") { main = clubPrioT("finished"); cls = "is-ok"; }
  else if (!p.open) { main = clubPrioT(p.tier === "abandoned" ? "wait_abandoned" : "wait_new", clubPrioTime(p.opens_at)); cls = "is-wait"; }
  else { box.classList.add("hidden"); return; }
  box.className = `club-priority-note ${cls}`;
  box.innerHTML = `<div>${escHtml(main)}</div><small>${escHtml(clubPrioT("open_after"))}</small>`;
}

async function clubPriorityLoad() {
  try { APP.clubPriority = await apiFetch("/club-priority/me"); }
  catch (_) { APP.clubPriority = null; }      // xato bo'lsa banner ko'rinmaydi, /register baribir tekshiradi
  clubPriorityRender();
}
