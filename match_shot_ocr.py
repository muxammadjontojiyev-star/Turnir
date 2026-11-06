"""
match_shot_ocr.py — eFootball «Match History» skrinshotini O'QISH (2026-11-06, match_shot.py uchun).

Tesseract (bepul, serverda: railpack.json → deploy.aptPackages "tesseract-ocr") bilan:
  1) butun rasm — so'zlar va joylashuvi (TSV);
  2) har bir o'yin qatori «dd/mm/yyyy hh:mm» sanasidan topiladi;
  3) sana ostidagi markaziy qism (hisob) alohida, faqat raqamlar bilan qayta o'qiladi (0 → «Q» xatosi bo'lmasin);
  4) hisob ostidagi chap va o'ng kulrang yozuv — ikkala o'yinchining eFootball niknamei.
Natija: [{"date": "05/11/2026", "time": "16:26", "left": nick, "right": nick, "s_left": 5, "s_right": 2}, ...]
"""

import io
import logging
import os
import re
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)

TESS_BIN = shutil.which("tesseract") or "tesseract"
TESS_TIMEOUT_S = 25
MIN_WIDTH = 1200                 # kichik skrinshot — kattalashtiriladi (o'qish aniqroq)
DATE_RE = re.compile(r"^(\d{2})[/.\-](\d{2})[/.\-](\d{4})$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")
ROW_MAX_H = 5.2                  # qator balandligi — sana balandligining shuncha barobari (keyingi sana bo'lmasa)
NICK_MIN_DY = 1.9                # nikname qatori sanadan kamida shuncha (sana balandligi) pastda
SCORE_HALF_W = 0.11              # hisob qirqimi kengligi: markazdan ± (rasm kengligiga nisbatan)
SCORE_UPSCALE = 2


def available() -> bool:
    return shutil.which("tesseract") is not None


def _tess(path: str, *args: str) -> str:
    r = subprocess.run([TESS_BIN, path, "-", *args], capture_output=True, text=True, timeout=TESS_TIMEOUT_S)
    return r.stdout


def _words(path: str) -> list[dict]:
    out = []
    for ln in _tess(path, "--psm", "11", "tsv").splitlines()[1:]:
        p = ln.split("\t")
        if len(p) != 12 or not p[11].strip():
            continue
        try:
            conf = float(p[10])
        except ValueError:
            continue
        if conf < 0:
            continue
        x, y, w, h = (int(v) for v in p[6:10])
        out.append({"x": x, "y": y, "w": w, "h": h, "cx": x + w / 2, "cy": y + h / 2, "t": p[11].strip()})
    return out


def _lines(words: list[dict], tol: float) -> list[list[dict]]:
    """So'zlarni gorizontal qatorlarga yig'adi (markaz y yaqinligi bo'yicha)."""
    rows: list[list[dict]] = []
    for w in sorted(words, key=lambda w: w["cy"]):
        if rows and abs(rows[-1][0]["cy"] - w["cy"]) <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w["x"]) for r in rows]


DIGIT_PSMS = ("10", "8", "7", "13", "6")     # bitta raqam turli rejimlarda o'qiladi — ko'pchilik ovozi
BRIGHT = 170                     # hisob raqamlari — oq, qalin (kulrang niknamedan yorqinroq)
TALL_K, DASH_K = 0.6, 0.35       # baland belgi (raqam) / past-keng belgi (chiziqcha) — eng baland belgiga nisbatan
GLUE_K = 0.6                     # bir son raqamlari orasidagi bo'shliq (balandlikka nisbatan)
PAD = 20
WHOLE_PSMS = ("7", "13", "6")
WHOLE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*-+\s*(\d{1,2})(?!\d)")


def _ocr_digits(im) -> str:
    """Bitta son (1–2 raqam): bir nechta rejimda o'qib, eng ko'p chiqqanini oladi."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        im.save(f, "PNG")
        path = f.name
    try:
        votes: dict[str, int] = {}
        for psm in DIGIT_PSMS:
            t = re.sub(r"\D", "", _tess(path, "--psm", psm, "-c", "tessedit_char_whitelist=0123456789"))
            if t and len(t) <= 2:
                votes[t] = votes.get(t, 0) + 1
    finally:
        os.remove(path)
    return max(votes, key=votes.get) if votes else ""


def _score(img, cx: float, y0: int, y1: int) -> tuple[int, int] | None:
    """Hisob qismini ustunlarga bo'ladi: [chap son] [–] [o'ng son] va har sonni alohida o'qiydi."""
    import numpy as np
    from PIL import Image, ImageOps
    half = img.width * SCORE_HALF_W
    crop = img.convert("L").crop((int(cx - half), max(0, y0), int(cx + half), min(img.height, y1)))
    a = np.asarray(crop, dtype=np.uint8) > BRIGHT
    cols = a.any(axis=0)
    comps, x, n = [], 0, len(cols)
    while x < n:
        if not cols[x]:
            x += 1
            continue
        s0 = x
        while x < n and cols[x]:
            x += 1
        rows = np.where(a[:, s0:x].any(axis=1))[0]
        comps.append((s0, x, int(rows.min()), int(rows.max()) + 1))
    if not comps:
        return None
    hmax = max(c[3] - c[2] for c in comps)
    tall = [c for c in comps if c[3] - c[2] >= TALL_K * hmax]
    dashes = [c for c in comps if c[3] - c[2] < DASH_K * hmax and c[1] - c[0] > c[3] - c[2]]
    if not dashes:
        return None
    mid = crop.width / 2
    d = min(dashes, key=lambda c: abs((c[0] + c[1]) / 2 - mid))

    def side(cs, left: bool):
        cs = sorted(cs, key=lambda c: c[0], reverse=left)
        out, edge = [], d[0] if left else d[1]
        for c in cs:
            gap = (edge - c[1]) if left else (c[0] - edge)
            if gap > hmax * (1.5 if not out else GLUE_K):
                break
            out.append(c)
            edge = c[0] if left else c[1]
        return out

    def read(cs) -> str:
        x0, x1 = min(c[0] for c in cs), max(c[1] for c in cs)
        ya, yb = min(c[2] for c in cs), max(c[3] for c in cs)
        im = ImageOps.invert(crop.crop((x0, ya, x1, yb)))
        im = ImageOps.expand(im, PAD, 255)
        return _ocr_digits(im.resize((im.width * SCORE_UPSCALE, im.height * SCORE_UPSCALE), Image.LANCZOS))

    L = side([c for c in tall if c[1] <= d[0]], True)
    R = side([c for c in tall if c[0] >= d[1]], False)
    if L and R:
        sl, sr = read(L), read(R)
        if sl and sr:
            return int(sl), int(sr)
    return _score_whole(crop)


def _score_whole(crop) -> tuple[int, int] | None:
    """Zaxira: butun hisob qismini «X-Y» sifatida o'qish (belgi chizig'i raqamlarga tegib ketgan bo'lsa)."""
    from PIL import Image, ImageOps
    im = ImageOps.expand(ImageOps.invert(crop), PAD, 255)
    im = im.resize((im.width * SCORE_UPSCALE, im.height * SCORE_UPSCALE), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        im.save(f, "PNG")
        path = f.name
    try:
        votes: dict[tuple[int, int], int] = {}
        for psm in WHOLE_PSMS:
            t = _tess(path, "--psm", psm, "-c", "tessedit_char_whitelist=0123456789-")
            mm = WHOLE_RE.search(t)
            if mm:
                k = (int(mm.group(1)), int(mm.group(2)))
                votes[k] = votes.get(k, 0) + 1
    finally:
        os.remove(path)
    return max(votes, key=votes.get) if votes else None


TIME_ZONE_W = 0.95              # vaqt sana o'ngida, taxminan sana kengligicha joyda


def _time_near(img, d: dict) -> str | None:
    from PIL import Image, ImageOps
    x0 = int(d["x"] + d["w"]); x1 = int(min(img.width, x0 + d["w"] * TIME_ZONE_W))
    crop = img.convert("L").crop((x0, int(d["y"] - d["h"] * 0.25), x1, int(d["y"] + d["h"] * 1.25)))
    im = ImageOps.expand(ImageOps.invert(crop), PAD, 255)
    im = im.resize((im.width * SCORE_UPSCALE, im.height * SCORE_UPSCALE), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        im.save(f, "PNG")
        path = f.name
    try:
        t = _tess(path, "--psm", "7", "-c", "tessedit_char_whitelist=0123456789:")
    finally:
        os.remove(path)
    mm = re.search(r"(\d{1,2}):(\d{2})", t)
    return f"{mm.group(1)}:{mm.group(2)}" if mm else None


def read_rows(raw: bytes) -> list[dict]:
    """Skrinshotdagi barcha o'yin qatorlari. Tesseract yo'q bo'lsa — RuntimeError("ocr_unavailable")."""
    if not available():
        raise RuntimeError("ocr_unavailable")
    from PIL import Image
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if img.width < MIN_WIDTH:
        k = MIN_WIDTH / img.width
        img = img.resize((MIN_WIDTH, int(img.height * k)), Image.LANCZOS)
    orig = img
    img = _erase_marks(img)                    # rangli chiziqlar matn ustidan o'tgan bo'lsa ham o'qilsin
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f, "PNG")
        path = f.name
    try:
        words = _words(path)
    finally:
        os.remove(path)

    dates = [w for w in words if DATE_RE.match(w["t"])]
    dates.sort(key=lambda w: w["y"])
    rows = []
    for i, d in enumerate(dates):
        h = d["h"]
        y_end = dates[i + 1]["y"] - h * 0.3 if i + 1 < len(dates) else d["y"] + h * ROW_MAX_H
        tm = next((w["t"] for w in words if TIME_RE.match(w["t"]) and abs(w["cy"] - d["cy"]) < h * 0.6
                   and 0 < w["x"] - d["x"] < d["w"] * 3), None)
        if tm is None:                                            # belgi chizig'i vaqt ustidan o'tgan bo'lsa
            tm = _time_near(img, d)
        # sana+vaqt guruhining markazi — kartochka markazi (hisob shu yerda)
        tw = next((w for w in words if w["t"] == tm and abs(w["cy"] - d["cy"]) < h * 0.6), None)
        cx = ((d["x"] + (tw["x"] + tw["w"] if tw else d["x"] + d["w"])) / 2)
        below = [w for w in words if d["y"] + h * NICK_MIN_DY < w["cy"] < y_end]
        nick_lines = _lines(below, tol=h * 0.6)
        nick_line = nick_lines[-1] if nick_lines else []           # eng pastki (kulrang) qator — niknamelar
        left = " ".join(w["t"] for w in nick_line if w["cx"] < cx).strip()
        right = " ".join(w["t"] for w in nick_line if w["cx"] > cx).strip()
        nick_top = min((w["y"] for w in nick_line), default=int(d["y"] + h * 3.2))
        sc = _score(img, cx, int(d["y"] + h * 1.15), int(nick_top - h * 0.1))
        if not (left and right and sc):
            logger.info("MATCH SHOT: qator o'qilmadi (%s %s): %r | %r | %r", d["t"], tm, left, right, sc)
            continue
        nick_bot = max((w["y"] + w["h"] for w in nick_line), default=int(d["y"] + h * 4))
        rows.append({"date": d["t"], "time": tm, "left": left, "right": right, "s_left": sc[0], "s_right": sc[1],
                     "_box": (cx, d["y"] - h * MARK_PAD_H, nick_bot + h * MARK_PAD_H)})
    _marks(orig, rows)
    for r in rows:
        r.pop("_box", None)
    return rows


# ---- ishtirokchi rangli chiziq bilan belgilagan qator (2026-11-06) ----
# O'yin qatorining matn qismi (logotiplar orasi) odatda faqat oq/kulrang/qora — u yerdagi YORQIN RANGLI
# piksellar — ishtirokchi chizgan belgi (aylana, ostiga chiziq, galochka). Eng ko'p bo'lgan qator — belgilangan.
MARK_PAD_H = 0.6                 # qator chegarasi sana/nikname dan shuncha (sana balandligi) tashqariga
MARK_HALF_W = 0.30               # tekshiriladigan kenglik: markazdan ± (rasm kengligiga nisbatan; logotiplar tashqarida)
MARK_SAT, MARK_VAL = 0.45, 0.35  # «rangli» piksel: to'yinganlik va yorqinlik chegarasi
MARK_MIN_RATIO = 0.004           # qatordagi rangli piksellar ulushi shundan kam bo'lsa — belgi yo'q
MARK_LEAD = 2.0                  # eng ko'p belgilangan qator keyingisidan kamida shuncha barobar ko'p bo'lsin


MARK_BG = (30, 31, 36)           # o'chirilgan belgi o'rniga — Match History qator foni
MARK_GROW = 2                    # belgi chetini shuncha piksel kengaytirib o'chirish


def _colored_mask(img):
    import numpy as np
    hsv = np.asarray(img.convert("HSV"), dtype=np.float32) / 255.0
    return (hsv[..., 1] > MARK_SAT) & (hsv[..., 2] > MARK_VAL)


def _erase_marks(img):
    """Yorqin rangli piksellarni (belgi, logotip, nuqtalar) fon rangiga bo'yaydi — matn (oq/kulrang) qoladi."""
    import numpy as np
    from PIL import Image, ImageFilter
    m = Image.fromarray((_colored_mask(img) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(MARK_GROW * 2 + 1))
    out = img.copy()
    out.paste(Image.new("RGB", img.size, MARK_BG), mask=m)
    return out


def _marks(img, rows: list[dict]) -> None:
    import numpy as np
    if not rows:
        return
    colored = _colored_mask(img)
    H, W = colored.shape
    ratios = []
    for r in rows:
        cx, y0, y1 = r["_box"]
        x0, x1 = int(max(0, cx - W * MARK_HALF_W)), int(min(W, cx + W * MARK_HALF_W))
        y0, y1 = int(max(0, y0)), int(min(H, y1))
        band = colored[y0:y1, x0:x1]
        ratios.append(float(band.mean()) if band.size else 0.0)
    best = max(range(len(rows)), key=lambda i: ratios[i])
    others = sorted(ratios, reverse=True)[1:2]
    lead_ok = not others or ratios[best] >= MARK_LEAD * max(others[0], MARK_MIN_RATIO / MARK_LEAD)
    for i, r in enumerate(rows):
        r["marked"] = bool(i == best and ratios[best] >= MARK_MIN_RATIO and lead_ok)
