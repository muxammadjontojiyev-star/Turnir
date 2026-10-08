// =============================================================
//  admin_stats.js — Admin paneli: "📊 Statistika" (2026-10-08, faqat bosh admin)
//  GET /admin/stats (stats.py): foydalanuvchilar, faollik, rejimlar, shaxsiy turnirlar,
//  tillar, 14 kunlik yangi foydalanuvchilar ustunlari (bitta seriya — bitta rang,
//  bosilganda/hoverda aniq son). Botda xuddi shu ma'lumot — /stats buyrug'i.
//  Global: apiFetch, escHtml, APP.
// =============================================================

const ADMIN_STATS_T = {
  uz: { title: "📊 STATISTIKA", refresh: "↻ Yangilash", total: "Jami foydalanuvchi", online: "Hozir onlayn",
        today: "Bugun yangi", act_today: "Bugun kirgan", d7: "7 kunda yangi", act7: "7 kunda faol",
        d30: "30 kunda yangi", act30: "30 kunda faol", growth: "Yangi foydalanuvchilar — so'nggi 14 kun",
        modes: "RASMIY TURNIRLAR", league: "Ligalar", wc: "Jahon ch.", cl: "ChL", el: "YeL", div: "Divizion (bugun)",
        pt: "SHAXSIY TURNIRLAR", pt_total: "Turnirlar", pt_live: "Yig'ilmoqda / davom", pt_players: "Ishtirokchilar",
        pt_org: "Tashkilotchilar", pt_subs: "Faol obunalar", pt_paid: "Tushum, so'm", langs: "TIL", at: "Holat",
        hint: "Faol — shu davrda ilovani ochgan. Botda ham: /stats", err: "Statistikani yuklab bo'lmadi" },
  ru: { title: "📊 СТАТИСТИКА", refresh: "↻ Обновить", total: "Всего пользователей", online: "Сейчас онлайн",
        today: "Новых сегодня", act_today: "Заходили сегодня", d7: "Новых за 7 дней", act7: "Активных за 7 дней",
        d30: "Новых за 30 дней", act30: "Активных за 30 дней", growth: "Новые пользователи — последние 14 дней",
        modes: "ОФИЦИАЛЬНЫЕ ТУРНИРЫ", league: "Лиги", wc: "ЧМ", cl: "ЛЧ", el: "ЛЕ", div: "Дивизион (сегодня)",
        pt: "ЧАСТНЫЕ ТУРНИРЫ", pt_total: "Турниры", pt_live: "Набор / идут", pt_players: "Участники",
        pt_org: "Организаторы", pt_subs: "Активные подписки", pt_paid: "Выручка, сум", langs: "ЯЗЫК", at: "Данные на",
        hint: "Активные — открывали приложение за период. В боте: /stats", err: "Не удалось загрузить статистику" },
  en: { title: "📊 STATISTICS", refresh: "↻ Refresh", total: "Total users", online: "Online now",
        today: "New today", act_today: "Opened today", d7: "New in 7 days", act7: "Active in 7 days",
        d30: "New in 30 days", act30: "Active in 30 days", growth: "New users — last 14 days",
        modes: "OFFICIAL TOURNAMENTS", league: "Leagues", wc: "World Cup", cl: "UCL", el: "UEL", div: "Division (today)",
        pt: "PRIVATE TOURNAMENTS", pt_total: "Tournaments", pt_live: "Gathering / running", pt_players: "Players",
        pt_org: "Organizers", pt_subs: "Active subscriptions", pt_paid: "Revenue, UZS", langs: "LANGUAGE", at: "As of",
        hint: "Active — opened the app in the period. In the bot: /stats", err: "Could not load statistics" },
};

function adminStatsT(k) {
  const lang = (typeof APP !== "undefined" && APP.lang) || "uz";
  return (ADMIN_STATS_T[lang] || ADMIN_STATS_T.uz)[k] || ADMIN_STATS_T.uz[k] || k;
}

function adminStatsNum(n) { return Number(n || 0).toLocaleString("ru-RU").replace(/,/g, " "); }

function adminStatsCell(v, key, accent) {
  return `<div class="stat-card${accent ? " stat-card--primary" : ""}"><span class="stat-card-value${accent ? " neon-cyan" : ""}">${adminStatsNum(v)}</span>
    <span class="stat-card-label">${escHtml(adminStatsT(key))}</span></div>`;
}

// 14 kunlik ustunlar: bitta seriya, bitta rang; eng katta qiymat va bugungi kun yozuv bilan
function adminStatsGrowthHtml(growth) {
  const max = Math.max(1, ...growth.map(g => g.count));
  const bars = growth.map((g, i) => {
    const h = Math.max(2, Math.round((g.count / max) * 78));
    const label = `${g.day.slice(8, 10)}.${g.day.slice(5, 7)}: ${g.count}`;
    const showVal = g.count === max || i === growth.length - 1;
    return `<div class="ast-col" title="${escHtml(label)}" data-ast-tip="${escHtml(label)}">
        ${showVal ? `<span class="ast-val">${g.count}</span>` : ""}<div class="ast-bar" style="height:${h}%"></div>
        <span class="ast-day">${escHtml(g.day.slice(8, 10))}</span></div>`;
  }).join("");
  return `<div class="ast-chart-title">${escHtml(adminStatsT("growth"))}</div><div class="ast-chart">${bars}</div>
    <div class="ast-tip" id="ast-tip"></div>`;
}

function adminStatsHtml(s) {
  const u = s.users, m = s.modes, p = s.private;
  const langs = Object.entries(s.languages || {}).sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<span class="ast-chip">${escHtml(k.toUpperCase())} · ${adminStatsNum(v)}</span>`).join("");
  const leagues = (s.leagues || []).map(l => `<span class="ast-chip">${escHtml(l.name)} · ${adminStatsNum(l.players)}/${l.max}</span>`).join("");
  return `
    <div class="stats-grid ast-grid">
      ${adminStatsCell(u.total, "total", true)}${adminStatsCell(u.online, "online", true)}
      ${adminStatsCell(u.new_today, "today")}${adminStatsCell(u.active_today, "act_today")}
      ${adminStatsCell(u.new_7d, "d7")}${adminStatsCell(u.active_7d, "act7")}
      ${adminStatsCell(u.new_30d, "d30")}${adminStatsCell(u.active_30d, "act30")}
    </div>
    <div class="card ast-card">${adminStatsGrowthHtml(s.growth || [])}</div>
    <div class="ast-sub">${escHtml(adminStatsT("modes"))}</div>
    <div class="stats-grid ast-grid ast-grid--5">
      ${adminStatsCell(m.league, "league")}${adminStatsCell(m.wc, "wc")}${adminStatsCell(m.cl, "cl")}
      ${adminStatsCell(m.el, "el")}${adminStatsCell(m.division_today, "div")}
    </div>
    ${leagues ? `<div class="ast-chips">${leagues}</div>` : ""}
    <div class="ast-sub">${escHtml(adminStatsT("pt"))}</div>
    <div class="stats-grid ast-grid">
      ${adminStatsCell(p.total, "pt_total")}<div class="stat-card"><span class="stat-card-value">${adminStatsNum(p.recruiting)} / ${adminStatsNum(p.running)}</span>
        <span class="stat-card-label">${escHtml(adminStatsT("pt_live"))}</span></div>
      ${adminStatsCell(p.players, "pt_players")}${adminStatsCell(p.organizers, "pt_org")}
      ${adminStatsCell(p.subs_active, "pt_subs")}${adminStatsCell(p.paid_uzs, "pt_paid")}
    </div>
    <div class="ast-sub">${escHtml(adminStatsT("langs"))}</div><div class="ast-chips">${langs}</div>
    <div class="ast-foot">${escHtml(adminStatsT("hint"))} · 🕒 ${escHtml(adminStatsT("at"))}: ${escHtml(s.generated_at || "")}</div>`;
}

async function adminLoadStats() {
  const box = document.getElementById("admin-stats-box");
  if (!box) return;
  box.innerHTML = `<div class="ast-head"><button class="tab-btn" id="ast-refresh">${escHtml(adminStatsT("refresh"))}</button></div>
    <div id="ast-body"><div class="empty-state">…</div></div>`;
  document.getElementById("ast-refresh").addEventListener("click", () => void adminLoadStats());
  const title = document.getElementById("admin-stats-title");
  if (title) title.textContent = adminStatsT("title");
  try {
    const s = await apiFetch("/admin/stats");
    document.getElementById("ast-body").innerHTML = adminStatsHtml(s);
    adminBindStatsTips(box);
  } catch (e) {
    document.getElementById("ast-body").innerHTML = `<div class="empty-state">${escHtml(adminStatsT("err"))}</div>`;
  }
}

// Ustunga bosilganda (telefon) / hoverda — aniq sana va son
function adminBindStatsTips(box) {
  const tip = box.querySelector("#ast-tip");
  box.querySelectorAll("[data-ast-tip]").forEach(col => {
    const show = () => { if (tip) { tip.textContent = col.dataset.astTip; tip.classList.add("on"); } };
    col.addEventListener("mouseenter", show);
    col.addEventListener("click", show);
  });
  box.querySelector(".ast-chart")?.addEventListener("mouseleave", () => tip && tip.classList.remove("on"));
}
