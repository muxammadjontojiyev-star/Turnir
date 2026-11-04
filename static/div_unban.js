// =============================================================
//  div_unban.js — DIVIZION: BANNI OLIB TASHLASH (2026-11-04, egasi so'rovi)
//  Admin → «KUNLIK BAN BERISH» formasi ostida: hozir ban ostidagilar ro'yxati (har birida «Banni olib
//  tashlash») va Telegram ID / @username bo'yicha olib tashlash. Faqat bosh admin (ban berish kabi).
//  API: GET /div/admin/bans, POST /div/admin/unban {query} (division_bans_api.py). Ishtirokchiga
//  bot xabari boradi; bugundan boshlab yana ro'yxatdan o'ta oladi, o'tgan ban kunlari tarixda qoladi.
//  division.js dagi divAdminBanForm qayta tayinlash orqali o'raladi — index.html da division.js dan KEYIN.
//  Global: APP, DIV, apiFetch, escHtml, showToast.
// =============================================================

const DIV_UNBAN_TXT = {
  uz: { title: "BANNI OLIB TASHLASH", none: "Hozir ban ostida hech kim yo'q ✅", until: "{d} gacha",
        btn: "Banni olib tashlash", ph: "Telegram ID yoki @username", pick: "Telegram ID yoki @username kiriting",
        ask: "{who} ning Divizion bani olib tashlansinmi?\n\nU bugundan boshlab yana ro'yxatdan o'ta oladi va telegramiga xabar boradi.",
        done: "✅ Ban olib tashlandi: {who}", loading: "Yuklanmoqda…",
        hint: "Ban bugundan tugaydi; o'tgan ban kunlari kalendarda tarix sifatida qoladi.",
        errors: { not_banned: "bu ishtirokchida amaldagi ban yo'q", user_not_found: "ishtirokchi topilmadi" } },
  ru: { title: "СНЯТЬ БАН", none: "Сейчас никто не забанен ✅", until: "до {d}",
        btn: "Снять бан", ph: "Telegram ID или @username", pick: "Введите Telegram ID или @username",
        ask: "Снять бан дивизиона у {who}?\n\nС сегодняшнего дня он снова сможет регистрироваться, в telegram придёт уведомление.",
        done: "✅ Бан снят: {who}", loading: "Загрузка…",
        hint: "Бан заканчивается сегодня; прошлые дни бана остаются в календаре как история.",
        errors: { not_banned: "у участника нет действующего бана", user_not_found: "участник не найден" } },
  en: { title: "LIFT A BAN", none: "Nobody is banned right now ✅", until: "until {d}",
        btn: "Lift ban", ph: "Telegram ID or @username", pick: "Enter a Telegram ID or @username",
        ask: "Lift {who}'s Division ban?\n\nStarting today they can register again; a telegram notice is sent.",
        done: "✅ Ban lifted: {who}", loading: "Loading…",
        hint: "The ban ends today; past ban days stay in the calendar as history.",
        errors: { not_banned: "this player has no active ban", user_not_found: "player not found" } },
};

function divUnbanT(k) { return (DIV_UNBAN_TXT[APP.lang] || DIV_UNBAN_TXT.uz)[k] || DIV_UNBAN_TXT.uz[k]; }

function divUnbanWho(b) {
  return b.username ? "@" + b.username : (b.nickname || "ID " + b.telegram_id);
}

function divUnbanListHtml(bans) {
  if (!bans.length) return `<div style="font-size:12.5px;opacity:.75;margin:4px 2px">${escHtml(divUnbanT("none"))}</div>`;
  return bans.map(b => `<div style="display:flex;align-items:center;gap:8px;padding:7px 2px;border-bottom:1px solid rgba(255,255,255,.06)">
      <span style="flex:1;min-width:0">${escHtml(divUnbanWho(b))} <small style="opacity:.6">· ID ${escHtml(b.telegram_id)}</small><br>
        <small style="opacity:.75">🚫 ${escHtml(divUnbanT("until").replace("{d}", b.until_day))}</small></span>
      <button class="btn btn--primary" style="flex:none;width:auto;padding:7px 12px;font-size:12px;letter-spacing:0" data-div-unban="${Number(b.telegram_id)}"
        data-div-unban-who="${escHtml(divUnbanWho(b))}">${escHtml(divUnbanT("btn"))}</button>
    </div>`).join("");
}

async function divUnbanLoad() {
  const box = document.getElementById("div-unban-list");
  if (!box) return;
  try {
    const d = await apiFetch("/div/admin/bans");
    box.innerHTML = divUnbanListHtml((d && d.bans) || []);
  } catch (e) {
    box.innerHTML = `<div style="font-size:12px;opacity:.7">${escHtml(e.message || "")}</div>`;
  }
}

function divUnbanFormHtml() {
  if (!DIV.status?.is_super) return "";
  setTimeout(divUnbanLoad, 0);                       // forma DOM'ga tushgach ro'yxat yuklanadi
  return `
    <div class="section-label">${escHtml(divUnbanT("title"))}</div>
    <div class="admin-fix-form" style="margin-bottom:12px">
      <div id="div-unban-list" style="margin-bottom:8px;font-size:12.5px;opacity:.75">${escHtml(divUnbanT("loading"))}</div>
      <input id="div-unban-query" class="modal-input" type="text" autocomplete="off"
             placeholder="${escHtml(divUnbanT("ph"))}" style="margin-bottom:8px" />
      <button class="btn btn--primary" id="div-btn-unban">${escHtml(divUnbanT("btn"))}</button>
      <div style="font-size:11.5px;opacity:.65">${escHtml(divUnbanT("hint"))}</div>
    </div>`;
}

async function divUnbanSubmit(btn, query, who) {
  if (!query) { showToast(divUnbanT("pick")); return; }
  if (!window.confirm(divUnbanT("ask").replace("{who}", who))) return;
  btn.disabled = true;                                // ikki marta bosish (qoida #38)
  try {
    await apiFetch("/div/admin/unban", { method: "POST", body: JSON.stringify({ query }) });
    showToast(divUnbanT("done").replace("{who}", who));
    const inp = document.getElementById("div-unban-query");
    if (inp) inp.value = "";
    await divUnbanLoad();
  } catch (e) {
    const err = divUnbanT("errors");
    showToast("❌ " + (err[e.message] || e.message));
  } finally {
    btn.disabled = false;
  }
}

document.addEventListener("click", (e) => {
  const rowBtn = e.target.closest("[data-div-unban]");
  if (rowBtn) { void divUnbanSubmit(rowBtn, rowBtn.dataset.divUnban, rowBtn.dataset.divUnbanWho); return; }
  const formBtn = e.target.closest("#div-btn-unban");
  if (formBtn) {
    const q = (document.getElementById("div-unban-query")?.value || "").trim();
    const who = /^\d+$/.test(q) ? `ID ${q}` : "@" + q.replace(/^@/, "");
    void divUnbanSubmit(formBtn, q, who);
  }
});

if (typeof divAdminBanForm === "function") {
  const _divUnbanPrevForm = divAdminBanForm;
  divAdminBanForm = function () { return _divUnbanPrevForm() + divUnbanFormHtml(); };
}

// Yangi ban berilgach — ro'yxat ham yangilansin (division.js tugmasi global nom orqali chaqiradi)
if (typeof divAdminBanSubmit === "function") {
  const _divUnbanPrevBan = divAdminBanSubmit;
  divAdminBanSubmit = async function (btn) { await _divUnbanPrevBan(btn); void divUnbanLoad(); };
}
