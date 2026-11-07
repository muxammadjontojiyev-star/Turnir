"""
match_shot_result.py — YIRIK HISOB: O'YIN YAKUNI EKRANI SKRINSHOTI (2026-11-07, egasi: «Yirik hisoblar uchun shunga
o'xshash skreen shotlar ham amal qilsin … adminga yirik hisob kiritilganligi haqida xabar kelmasin. Skreen ko'rsatilgach
bot uni tezda tasdiqlasin»).

eFootball o'yin tugagach ko'rsatadigan ikki ekran (Match History'dan tashqari):
  * «Итог матча / Match Result» — markazda katta «6–5», logotiplar ostida team nomlari;
  * statistika ekrani — tepada lenta: «Team A [6] (e) [5] Team B» (raqamlar sariq kataklarda).
read_result(raw) → {"kind": "result", "left", "right", "s_left", "s_right", "date": "", "time": ""} yoki None.

Bu ekranda sana va eFootball niknamei yo'q — tekshirish qoidalari: match_shot_side.py (faqat yirik hisob uchun).
"""

import io
import logging
import os
import re
import tempfile

logger = logging.getLogger(__name__)

RES_MIN_W = 1600                  # kichik skrinshot shu kenglikka kattalashtiriladi
TOP_PART = 0.45                   # hisob va nomlar rasmning yuqori qismida
CENTER_BAND = 0.14                # hisob markazdan ± shuncha (kenglikka nisbatan)
NAME_SIDE = 0.10                  # «Итог матча»: team nomi markazdan kamida shuncha chetda
BANNER_SIDE = 0.06                # lenta: nomlar raqam kataklariga yaqin
NAME_PAD_X, NAME_PAD_Y = 0.3, 0.25  # nom qirqimi chegarasi (yozuv balandligiga nisbatan)
BRIGHT_BOX = 150                  # sariq katak (yorqin fon) chegarasi
BOX_FILL_MIN = 0.55               # ustun/qatorda yorqin piksel ulushi shundan ko'p — sariq katak
BOX_INSET = 0.12
BOX_GLUE = 0.7                    # katak ustunlari orasidagi raqam kengligi (crop balandligiga nisbatan)
BOX_MIN_W = 0.4                   # katak kengligi crop balandligining kamida shuncha qismi
BANNER_DIGIT_H = 1.4               # lenta raqam katagi nom balandligidan kattaroq
BANNER_LOGO = 0.06                # nomlar orasining o'rtasi (eFootball belgisi) o'qilmaydi
NAME_CONF_MIN = 40
NAME_KEY_MIN = 3
LANDSCAPE_MIN = 1.3                # kenglik / balandlik
SCORE_MAX = 30
SCORE_TOKEN = re.compile(r"^(\d{1,2})[-–—:](\d{1,2})$")


def _tsv(path: str) -> list[dict]:
    from match_shot_ocr import _tess
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
        out.append({"x": x, "y": y, "w": w, "h": h, "cx": x + w / 2, "cy": y + h / 2, "t": p[11].strip(), "c": conf})
    return out


def _img_words(img) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f, "PNG")
        path = f.name
    try:
        return _tsv(path)
    finally:
        os.remove(path)


def _runs(mask, glue: int = 0) -> list[tuple[int, int]]:
    """True qismlar [(boshi, oxiri)]; glue — shundan kichik oraliq bilan ajralganlari birlashtiriladi (katak ichidagi raqam)."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if out and i - out[-1][1] < glue:
                out[-1] = (out[-1][0], j)
            else:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def _digit_cell(gray) -> str:
    """Bitta son — lentadagi sariq katak ichida (qora raqam). Katak topilmasa — "" (bu yakun ekrani emas)."""
    import numpy as np
    from PIL import Image, ImageOps
    from match_shot_ocr import PAD, _ocr_digits
    a = np.asarray(gray, dtype=np.uint8) > BRIGHT_BOX
    cols = _runs(a.mean(axis=0) >= BOX_FILL_MIN, int(gray.height * BOX_GLUE))
    if not cols:
        return ""
    x0, x1 = max(cols, key=lambda r: r[1] - r[0])
    rows = _runs(a[:, x0:x1].mean(axis=1) >= BOX_FILL_MIN)
    if not rows or x1 - x0 < gray.height * BOX_MIN_W:
        return ""
    y0, y1 = max(rows, key=lambda r: r[1] - r[0])
    dx, dy = int((x1 - x0) * BOX_INSET), int((y1 - y0) * BOX_INSET)
    if y1 - y0 <= 2 * dy + 4:
        return ""
    im = ImageOps.expand(gray.crop((x0 + dx, y0 + dy, x1 - dx, y1 - dy)), PAD, 255)
    return _ocr_digits(im.resize((im.width * 2, im.height * 2), Image.LANCZOS))


def _reread(gray, ws: list[dict]) -> str:
    """Team nomini o'z qirqimida qayta o'qish (eFootball qalin shrifti butun rasmda yomon o'qiladi)."""
    from PIL import Image, ImageOps
    from match_shot_ocr import PAD, _tess
    h = max(w["h"] for w in ws)
    box = (max(0, min(w["x"] for w in ws) - int(h * NAME_PAD_X)), max(0, min(w["y"] for w in ws) - int(h * NAME_PAD_Y)),
           min(gray.width, max(w["x"] + w["w"] for w in ws) + int(h * NAME_PAD_X)),
           min(gray.height, max(w["y"] + w["h"] for w in ws) + int(h * NAME_PAD_Y)))
    im = ImageOps.expand(ImageOps.invert(gray.crop(box)), PAD, 255)
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        im.save(f, "PNG")
        path = f.name
    try:
        t = _tess(path, "--psm", "7").strip()
    finally:
        os.remove(path)
    t = re.sub(r"^[^\w]+|[^\w]+$", "", t)
    return t if len(t) >= 2 else " ".join(w["t"] for w in ws)


def _names(words: list[dict], gray, y_lo: float, y_hi: float, off: float) -> tuple[str, str, list, list]:
    """(y_lo..y_hi) oralig'idagi eng ishonchli qator: markazdan chap va o'ngdagi team nomlari."""
    W, cx = gray.width, gray.width / 2
    lettered = [w for w in words if y_lo <= w["cy"] <= y_hi and len(w["t"]) >= 2 and re.search(r"[^\W\d_]", w["t"])]
    best, best_k = ("", "", [], []), 0.0
    for w0 in (w for w in lettered if w["c"] >= NAME_CONF_MIN):
        line = sorted((w for w in lettered if abs(w["cy"] - w0["cy"]) <= w0["h"] * 0.6), key=lambda w: w["x"])
        lw = [w for w in line if w["cx"] < cx - W * off]
        rw = [w for w in line if w["cx"] > cx + W * off]
        if not (lw and rw):
            continue
        k = sum(w["c"] * len(w["t"]) for w in line)
        if k > best_k:
            best, best_k = ("", "", lw, rw), k
    lw, rw = best[2], best[3]
    if not (lw and rw):
        return "", "", [], []
    return _reread(gray, lw), _reread(gray, rw), lw, rw


def _ok(row: dict | None) -> dict | None:
    """Nomlar o'qilgan va hisob real bo'lsa."""
    from match_shot import _key
    if not row or min(len(_key(row["left"])), len(_key(row["right"]))) < NAME_KEY_MIN:
        return None
    return row if max(row["s_left"], row["s_right"]) <= SCORE_MAX else None


def read_result(raw: bytes) -> dict | None:
    from PIL import Image
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if img.width < RES_MIN_W:
        k = RES_MIN_W / img.width
        img = img.resize((RES_MIN_W, int(img.height * k)), Image.LANCZOS)
    W, H = img.size
    if W < H * LANDSCAPE_MIN:                                               # eFootball — faqat yotiq ekran
        return None
    gray = img.convert("L")
    top = [w for w in _img_words(img) if w["cy"] < H * TOP_PART]
    cx = W / 2
    # 1) «6-5» — bitta so'z (Итог матча ekrani), nomlar — hisobdan pastda
    sc = [w for w in top if SCORE_TOKEN.match(w["t"]) and abs(w["cx"] - cx) < W * CENTER_BAND]
    if sc:
        s = max(sc, key=lambda w: w["h"])
        m = SCORE_TOKEN.match(s["t"])
        left, right, _, _ = _names(top, gray, s["y"], H * TOP_PART, NAME_SIDE)
        if left and right:
            return _ok({"kind": "result", "left": left, "right": right, "s_left": int(m.group(1)),
                        "s_right": int(m.group(2)), "date": "", "time": ""})
    # 2) lenta: «Team A [6] (e) [5] Team B» — nomlar orasidagi markaz qismi ikkiga bo'linib o'qiladi
    left, right, lw, rw = _names(top, gray, 0, H * TOP_PART, BANNER_SIDE)
    if not (left and right):
        return None
    line = lw + rw
    h = max(w["h"] for w in line)
    ymid = sum(w["cy"] for w in line) / len(line)
    x0, x1 = max(w["x"] + w["w"] for w in lw), min(w["x"] for w in rw)
    y0, y1 = int(ymid - h * BANNER_DIGIT_H), int(ymid + h * BANNER_DIGIT_H)
    gap = (x1 - x0) * BANNER_LOGO                                          # o'rtadagi eFootball belgisi
    sl = _digit_cell(gray.crop((int(x0), y0, int(cx - gap), y1)))
    sr = _digit_cell(gray.crop((int(cx + gap), y0, int(x1), y1)))
    if not (sl and sr):
        logger.info("MATCH SHOT RESULT: hisob o'qilmadi (%r | %r)", left, right)
        return None
    return _ok({"kind": "result", "left": left, "right": right, "s_left": int(sl), "s_right": int(sr), "date": "", "time": ""})
