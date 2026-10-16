// =============================================================
//  tb_logo.js — "TEAMLAR JANGI": team va liga logolari (galereyadan rasm, 2026-10-16)
//  tbLogo(kind, id, ver, emoji, cls)  — logo <img> (yo'q bo'lsa — emoji); barcha ekranlar ishlatadi
//  tbLogoPickerHtml(kind, id, ver, emoji) — "Logoni o'zgartirish" bloki (sardor / liga admini)
//  Rasm brauzerda 256x256 kvadratga (markazdan) kesilib siqiladi -> POST:
//    team:   /tb/team/logo          {image_base64}            (sardor)
//    league: /tb/admin/league/logo  {league_id, image_base64} (liga admini / bosh admin)
//  Backend: tb_logos.py, tb_api_league.py. Global: API_BASE, apiFetch, escHtml, tbToast, tbConfirm, tbErr, TB.
// =============================================================

const TB_LOGO_SIDE = 256;          // px — saqlanadigan kvadrat
const TB_LOGO_QUALITY = 0.86;
const TB_LOGO_FALLBACK = { team: "⚔️", league: "🏆" };

function tbLogo(kind, id, ver, emoji, cls) {
  const c = `tb-logo${cls ? " " + cls : ""}`;
  if (id && ver) {
    return `<img class="${c}" src="${API_BASE}/tb/logo/${kind}/${+id}?v=${+ver}" alt="" loading="lazy" decoding="async">`;
  }
  return `<span class="${c} tb-logo--emoji">${escHtml(emoji || TB_LOGO_FALLBACK[kind] || "⚔️")}</span>`;
}

function tbLogoPickerHtml(kind, id, ver, emoji) {
  return `<div class="tb-logo-pick">
      ${tbLogo(kind, id, ver, emoji, "tb-logo--lg")}
      <div class="tb-logo-pick-acts">
        <label class="btn btn--ghost tb-logo-btn">🖼 Galereyadan logo
          <input type="file" accept="image/*" hidden data-tb-logo-file="${kind}" data-id="${id}"></label>
        ${ver ? `<button class="tb-mini tb-mini--danger" data-tb-logo-del="${kind}" data-id="${id}">Logoni olib tashlash</button>` : ""}
        <div class="tb-hint">Kvadrat rasm yaxshi chiqadi — markazi kesib olinadi.</div>
      </div>
    </div>`;
}

// Markazdan kvadrat kesib, TB_LOGO_SIDE ga kichraytiradi. Shaffoflik saqlansin — WEBP (iOS da PNG).
function tbLogoCompress(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const s = Math.min(img.width, img.height);
      const side = Math.min(TB_LOGO_SIDE, s);
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = side;
      canvas.getContext("2d").drawImage(img, (img.width - s) / 2, (img.height - s) / 2, s, s, 0, 0, side, side);
      URL.revokeObjectURL(url);
      let data = canvas.toDataURL("image/webp", TB_LOGO_QUALITY);
      if (!data.startsWith("data:image/webp")) data = canvas.toDataURL("image/png");
      resolve(data);
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("bad_image")); };
    img.src = url;
  });
}

async function tbLogoSave(kind, id, image) {
  const path = kind === "league" ? "/tb/admin/league/logo" : "/tb/team/logo";
  const body = kind === "league" ? { league_id: id, image_base64: image } : { image_base64: image };
  await apiFetch(path, { method: "POST", body: JSON.stringify(body) });
  try { TB.me = await apiFetch("/tb/me"); } catch (_) { /* ekran baribir yangilanadi */ }
  if (TB.tab === "admin" && typeof tbAdminLoad === "function") await tbAdminLoad();
  else if (typeof tbRenderTab === "function") tbRenderTab();
}

document.addEventListener("change", async (e) => {
  const inp = e.target.closest ? e.target.closest("#tb-root [data-tb-logo-file]") : null;
  if (!inp || !inp.files || !inp.files[0]) return;
  const kind = inp.dataset.tbLogoFile, id = +inp.dataset.id;
  const label = inp.closest("label");
  if (label) label.classList.add("is-busy");
  try {
    const image = await tbLogoCompress(inp.files[0]);
    await tbLogoSave(kind, id, image);
    tbToast("✅ Logo yangilandi");
  } catch (err) {
    tbToast("❌ " + tbErr(err));
    if (label) label.classList.remove("is-busy");
  }
  inp.value = "";
});

document.addEventListener("click", async (e) => {
  const b = e.target.closest ? e.target.closest("#tb-root [data-tb-logo-del]") : null;
  if (!b || !tbConfirm("Logo olib tashlansinmi?")) return;
  b.disabled = true;
  try {
    await tbLogoSave(b.dataset.tbLogoDel, +b.dataset.id, null);
    tbToast("Logo olib tashlandi");
  } catch (err) {
    tbToast("❌ " + tbErr(err));
    b.disabled = false;
  }
});
