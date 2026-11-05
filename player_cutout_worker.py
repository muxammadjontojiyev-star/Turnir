"""
player_cutout_worker.py — yuklangan rasmdan INSONNI BUTUN TANASI bilan qirqib olish (2026-11-04/05, player_cutout.py).

ALOHIDA JARAYONDA ishga tushiriladi (python player_cutout_worker.py <model_yo'li>): model ~600 MB xotira
oladi, ish tugashi bilan jarayon yopilib xotira to'liq qaytadi (bot jarayoni og'irlashmaydi).
  stdin  — rasm baytlari (JPEG/PNG)
  stdout — shaffof fonli WEBP (odam atrofida qirqilgan)
  exit 0 — tayyor, 3 — rasmda odam topilmadi, 2 — xato.
Model — u2net_human_seg (rembg loyihasi, MIT), birinchi marta GitHub'dan yuklab olinadi (player_cutout.py).
"""

import io
import sys

SEG_SIZE = 320                       # model kirish o'lchami
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
ALPHA_LO, ALPHA_HI = 0.15, 0.85      # niqob chetini aniqlashtirish (shundan pasti — fon, yuqorisi — odam)
MIN_COVER = 0.04                     # odam rasmning shundan kam qismi bo'lsa — «odam yo'q»
PAD_SIDE, PAD_TOP, PAD_BOTTOM = 0.04, 0.03, 0.01   # qirqishda odam atrofida qoldiriladigan joy (butun tana saqlanadi)
OUT_MAX = 1000                       # natija rasmining eng katta tomoni
WEBP_Q = 85
EXIT_NO_PERSON, EXIT_ERR = 3, 2


def cutout(raw: bytes, model_path: str) -> bytes | None:
    import numpy as np
    import onnxruntime as ort
    from PIL import Image

    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((OUT_MAX, OUT_MAX), Image.LANCZOS)
    x = np.asarray(im.resize((SEG_SIZE, SEG_SIZE), Image.LANCZOS), dtype=np.float32)
    x = x / max(float(x.max()), 1e-6)
    x = ((x - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)

    so = ort.SessionOptions()
    so.intra_op_num_threads = 1
    so.enable_cpu_mem_arena = False
    sess = ort.InferenceSession(model_path, so, providers=["CPUExecutionProvider"])
    pred = sess.run(None, {sess.get_inputs()[0].name: x})[0][0, 0]
    pred = (pred - pred.min()) / max(float(pred.max() - pred.min()), 1e-6)

    mask = Image.fromarray((pred * 255).astype(np.uint8)).resize(im.size, Image.BILINEAR)
    a = np.asarray(mask, dtype=np.float32) / 255
    a = np.clip((a - ALPHA_LO) / (ALPHA_HI - ALPHA_LO), 0, 1)
    solid = a > 0.5
    if solid.mean() < MIN_COVER:
        return None
    ys, xs = np.where(solid)
    w, h = im.size
    x0 = max(0, int(xs.min() - w * PAD_SIDE)); x1 = min(w, int(xs.max() + w * PAD_SIDE) + 1)
    y0 = max(0, int(ys.min() - h * PAD_TOP));  y1 = min(h, int(ys.max() + h * PAD_BOTTOM) + 1)
    rgba = im.copy()
    rgba.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    out = io.BytesIO()
    rgba.crop((x0, y0, x1, y1)).save(out, "WEBP", quality=WEBP_Q, method=4)
    return out.getvalue()


def main() -> int:
    try:
        res = cutout(sys.stdin.buffer.read(), sys.argv[1])
    except Exception as exc:                   # noqa: BLE001 — sabab ota jarayon logiga
        print(f"cutout xato: {exc}", file=sys.stderr)
        return EXIT_ERR
    if res is None:
        return EXIT_NO_PERSON
    sys.stdout.buffer.write(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
