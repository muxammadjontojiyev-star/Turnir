// ============================================================
//  2026-09-22: DIVIZION "BARABAN" (toq qolgan ishtirokchi achkosi)
//  Ro'yxatdan o'tganlar soni toq bo'lsa, raqib yetmagan ishtirokchi
//  avtomatik +15 O'RNIGA barabanni aylantiradi: 6 qism (bitta 15,
//  ikkita 10, uchta 5).
//  Natija SERVERDA aniqlanadi (POST /div/bye/spin) — bu yerda faqat
//  animatsiya. Aks holda natijani klientdan tanlab olish mumkin bo'lardi.
// ============================================================

const DIV_BYE = {
  state: null,      // GET /div/bye javobi
  spinning: false,
};

// Baraban SVG'si. Qismlar teng burchakli (360/6 = 60°).
function divByeWheelSvg(segments) {
  const n = segments.length;
  const step = 360 / n;
  const R = 78, CX = 90, CY = 90;
  // Achkoga qarab rang: 15 — oltin, 10 — ko'k, 5 — kulrang
  const fill = (p) => p >= 15 ? "#f2c94c" : (p >= 10 ? "#4ea8ff" : "#4a5468");

  const parts = segments.map((p, i) => {
    const a0 = (i * step - 90) * Math.PI / 180;
    const a1 = ((i + 1) * step - 90) * Math.PI / 180;
    const x0 = CX + R * Math.cos(a0), y0 = CY + R * Math.sin(a0);
    const x1 = CX + R * Math.cos(a1), y1 = CY + R * Math.sin(a1);
    // Matn qism markazida
    const am = ((i + 0.5) * step - 90) * Math.PI / 180;
    const tx = CX + R * 0.62 * Math.cos(am), ty = CY + R * 0.62 * Math.sin(am);
    return `
      <path d="M ${CX} ${CY} L ${x0.toFixed(2)} ${y0.toFixed(2)} A ${R} ${R} 0 0 1 ${x1.toFixed(2)} ${y1.toFixed(2)} Z"
            fill="${fill(p)}" stroke="rgba(0,0,0,.35)" stroke-width="1"/>
      <text x="${tx.toFixed(2)}" y="${ty.toFixed(2)}" text-anchor="middle" dominant-baseline="central"
            font-size="20" font-weight="800" fill="#0d1017">${p}</text>`;
  }).join("");

  return `
    <svg viewBox="0 0 180 180" class="div-wheel-svg" id="div-wheel-svg">
      <circle cx="${CX}" cy="${CY}" r="${R + 4}" fill="rgba(255,255,255,.06)"/>
      ${parts}
      <circle cx="${CX}" cy="${CY}" r="12" fill="#11151f" stroke="rgba(255,255,255,.25)" stroke-width="2"/>
    </svg>`;
}

// Bosh sahifadagi baraban kartasi. Bye bo'lmasa — bo'sh satr (hech narsa
// ko'rsatilmaydi, qoida #40: ishlamaydigan element turmasin).
function divByeCard() {
  const st = DIV_BYE.state;
  if (!st || !st.has_bye) return "";

  const segs = st.segments || [15, 10, 5, 10, 5, 5];
  let body;

  if (st.spun) {
    body = `
      <div class="div-wheel-result">${st.points} ${escHtml(DT("div_bye_points") || "achko")}</div>
      <div class="div-wheel-hint">${escHtml(DT("div_bye_done") || "Baraban aylantirildi. Achko reytingga qo'shildi.")}</div>`;
  } else if (st.expired) {
    body = `
      <div class="div-wheel-result">${st.min_points} ${escHtml(DT("div_bye_points") || "achko")}</div>
      <div class="div-wheel-hint">${escHtml(DT("div_bye_expired") || "Muddat o'tdi — kafolatlangan minimum berildi.")}</div>`;
  } else {
    body = `
      <button class="btn btn--primary btn--glow" id="div-bye-spin" style="width:100%;margin-top:10px">
        ${escHtml(DT("div_bye_spin") || "Barabanni aylantirish")}
      </button>
      <div class="div-wheel-hint">${escHtml(DT("div_bye_hint") || "Bugun sizga raqib yetmadi. Barabanni aylantiring — achkongiz omadga bog'liq.")}</div>`;
  }

  return `
    <div class="card div-wheel-card">
      <b>${escHtml(DT("div_bye_title") || "RAQIB YETMADI")}</b>
      <div class="div-wheel-wrap" id="div-wheel-wrap">${divByeWheelSvg(segs)}
        <div class="div-wheel-pointer"></div>
      </div>
      ${body}
    </div>`;
}

// Holatni yuklaydi (bosh sahifa chizilishidan oldin)
async function divLoadByeState() {
  try {
    DIV_BYE.state = await apiFetch("/div/bye");
  } catch (_) {
    DIV_BYE.state = null;   // xato bo'lsa baraban ko'rsatilmaydi
  }
}

// Aylantirish: server natijani qaytaradi, animatsiya shu qismda to'xtaydi
async function divByeSpin(btn) {
  if (DIV_BYE.spinning) return;
  DIV_BYE.spinning = true;
  if (btn) btn.disabled = true;

  let r;
  try {
    r = await apiFetch("/div/bye/spin", { method: "POST" });
  } catch (e) {
    const msg = {
      no_bye: DT("div_bye_none") || "Sizda baraban yo'q.",
      already_spun: DT("div_bye_already") || "Baraban allaqachon aylantirilgan.",
      expired: DT("div_bye_expired") || "Muddat o'tdi.",
    }[e.message] || (DT("div_bye_failed") || "Aylantirishda xatolik.");
    showToast("❌ " + msg);
    DIV_BYE.spinning = false;
    if (btn) btn.disabled = false;
    void divRefreshBye();
    return;
  }

  const svg = document.getElementById("div-wheel-svg");
  const n = (r.segments || []).length || 6;
  const step = 360 / n;
  // Ko'rsatkich tepada. r.index qismining markazi tepaga kelishi uchun
  // shuncha burchakka teskari buramiz + 5 to'liq aylanish (animatsiya uchun).
  const target = 360 * 5 - (r.index * step + step / 2);
  if (svg) {
    svg.style.transition = "transform 3.2s cubic-bezier(.17,.67,.21,1)";
    svg.style.transform = `rotate(${target}deg)`;
  }

  // Animatsiya tugagach natijani ko'rsatamiz
  setTimeout(() => {
    DIV_BYE.spinning = false;
    showToast(`🎉 ${r.points} ${DT("div_bye_points") || "achko"}`);
    void divRefreshBye();
  }, 3400);
}

// Holatni qayta yuklab, sahifani yangilaydi (reyting ham o'zgargan bo'ladi)
async function divRefreshBye() {
  await divLoadByeState();
  if (typeof renderDivision === "function") renderDivision();
}
