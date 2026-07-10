// ============================================================
//  CELEBRATION — Mavsum yakuni tabrik oynasi (bir martalik)
//  Backend: GET /season/celebration, POST /season/celebration/seen
//  app.js dan keyin yuklanadi (apiFetch ishlatadi).
// ============================================================

// XSS himoyasi (qoida #35): foydalanuvchi nicknamelari HTML sifatida chiqmasin
function escCel(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// Sovrin turi → rasm va nom (mavjud static rasmlar; liga kubogi uchun wc-trophy.png)
const CEL_PRIZE_META = {
  golden_ball: { img: "golden-ball.png", label: "Oltin to'p" },
  golden_boot: { img: "golden-boot.png", label: "Oltin butsa" },
  league_cup:  { img: "wc-trophy.png",  label: "Liga kubogi" },
};

function celPrizeLabel(w) {
  const meta = CEL_PRIZE_META[w.prize_type] || { img: "wc-trophy.png", label: w.prize_type };
  const league = w.prize_type === "league_cup" && w.league_name
    ? ` — ${escCel(w.league_name)}` : "";
  return { img: meta.img, text: meta.label + league };
}

// Salyut: 60 ta konfetti bo'lagi (CSS animatsiya .cel-piece)
function celFireworksHtml() {
  let html = '<div class="cel-fireworks" aria-hidden="true">';
  const colors = ["#f5c542", "#7c5cff", "#31d0aa", "#ff5c8a", "#4cc3ff"];
  for (let i = 0; i < 60; i++) {
    const left = Math.random() * 100;
    const delay = (Math.random() * 2.5).toFixed(2);
    const dur = (2.6 + Math.random() * 2).toFixed(2);
    const color = colors[i % colors.length];
    html += `<span class="cel-piece" style="left:${left}%;background:${color};` +
            `animation-delay:${delay}s;animation-duration:${dur}s"></span>`;
  }
  return html + "</div>";
}

function celWinnersListHtml(winners) {
  return winners.map((w) => {
    const p = celPrizeLabel(w);
    return `
      <div class="cel-winner-row">
        <img class="cel-prize-img" src="${p.img}" alt="">
        <div class="cel-winner-info">
          <div class="cel-winner-name">${escCel(w.nickname)}</div>
          <div class="cel-winner-prize">${p.text}</div>
        </div>
      </div>`;
  }).join("");
}

function showCelebrationModal(data) {
  const overlay = document.createElement("div");
  overlay.className = "cel-overlay";

  let inner;
  if (data.is_winner) {
    inner = `
      ${celFireworksHtml()}
      <div class="cel-box cel-box--winner">
        <div class="cel-emoji">🎆🏆🎆</div>
        <div class="cel-title">Tabriklaymiz!</div>
        <div class="cel-sub">${data.season}-mavsum sovrindorisiz!</div>
        <div class="cel-list">${celWinnersListHtml(data.my_prizes)}</div>
        <button class="btn btn-primary cel-close">Rahmat! 🎉</button>
      </div>`;
  } else {
    inner = `
      <div class="cel-box">
        <div class="cel-emoji">🏆</div>
        <div class="cel-title">${data.season}-mavsum yakunlandi</div>
        <div class="cel-sub">Mavsum sovrindorlari:</div>
        <div class="cel-list">${celWinnersListHtml(data.winners)}</div>
        <button class="btn btn-primary cel-close">Yopish</button>
      </div>`;
  }
  overlay.innerHTML = inner;
  document.body.appendChild(overlay);

  overlay.querySelector(".cel-close").addEventListener("click", async () => {
    overlay.remove();
    try {
      await apiFetch("/season/celebration/seen", { method: "POST" });
    } catch (e) {
      // Belgilash muvaffaqiyatsiz bo'lsa — keyingi kirishda yana ko'rinadi, xavfsiz
      console.warn("celebration seen xatosi:", e);
    }
  });
}

// init oxirida chaqiriladi (app.js). Xato bo'lsa ilova ishlashiga ta'sir qilmaydi.
async function checkSeasonCelebration() {
  try {
    const data = await apiFetch("/season/celebration");
    if (data && data.show) showCelebrationModal(data);
  } catch (e) {
    console.warn("celebration tekshiruvi xatosi:", e);
  }
}
