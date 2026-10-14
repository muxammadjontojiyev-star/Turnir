// =============================================================
//  pt_profile_prizes.js — profilda "SHAXSIY TURNIR SOVRINLARI" bo'limi (2026-10-14)
//  Admin qarori: shaxsiy turnirda yutilgan kuboklar rasmiy sovrinlardan ALOHIDA,
//  boshqa rangda va "Shaxsiy" belgisi bilan ko'rsatiladi; ★ bermaydi, reyting
//  jadvallarida belgi yo'q. Ma'lumot: GET /users/{id}/pt-prizes (pt_user_prizes.py).
//  api.js loadPrizesInto chaqiradi (o'z profilim va boshqa o'yinchi profili).
//  Global: APP, escHtml, LEAGUE_TROPHIES, PT_FORMAT_META, PTT.
// =============================================================

const PT_PRIZE_TEXTS = {
  uz: { title: "SHAXSIY TURNIR SOVRINLARI", badge: "Shaxsiy", champ: "Chempion", by: "tashkilotchi" },
  ru: { title: "НАГРАДЫ ЧАСТНЫХ ТУРНИРОВ", badge: "Частный", champ: "Чемпион", by: "организатор" },
  en: { title: "PRIVATE TOURNAMENT TROPHIES", badge: "Private", champ: "Champion", by: "organizer" },
};

function ptPrizeT(k) {
  return (PT_PRIZE_TEXTS[APP.lang] || PT_PRIZE_TEXTS.uz)[k];
}

function ptProfilePrizeImg(p) {
  if (p.league && typeof LEAGUE_TROPHIES !== "undefined" && LEAGUE_TROPHIES[p.league]) return LEAGUE_TROPHIES[p.league];
  const meta = typeof PT_FORMAT_META !== "undefined" ? PT_FORMAT_META[p.format] : null;
  return (meta && meta.trophy) || null;
}

function ptProfilePrizesSectionHtml(prizes) {
  const cards = prizes.map(p => {
    const img = ptProfilePrizeImg(p);
    const owner = p.owner_username ? "@" + p.owner_username : (p.owner_nickname || "");
    const sub = [p.league || "", owner ? `${ptPrizeT("by")} ${owner}` : ""].filter(Boolean).join(" · ");
    return `
      <div class="my-prize-card my-prize-card--pt" title="${escHtml(p.tournament_name)} · #${p.tournament_id}">
        <span class="my-prize-pt-badge">${escHtml(ptPrizeT("badge"))}</span>
        <div class="my-prize-icon">${img
          ? `<img src="${escHtml(img)}" alt="" class="my-prize-img" onerror="this.outerHTML='<span class=&quot;my-prize-emoji&quot;>🏆</span>'" />`
          : `<span class="my-prize-emoji">🏆</span>`}</div>
        <div class="my-prize-name">«${escHtml(p.tournament_name)}»</div>
        <div class="my-prize-season">${escHtml(ptPrizeT("champ"))} · ${escHtml(p.finished_at || "")}</div>
        ${sub ? `<div class="my-prize-pt-sub">${escHtml(sub)}</div>` : ""}
      </div>`;
  }).join("");
  return `
    <div class="section-label">${escHtml(ptPrizeT("title"))}</div>
    <div class="my-prizes-grid my-prizes-grid--pt">${cards}</div>`;
}
