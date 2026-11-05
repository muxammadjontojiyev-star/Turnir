"""
player_cutout.py — SHAXSIY KARTA RASMI: ishtirokchi O'ZI yuklagan rasm (2026-11-05, egasi so'rovi).

Avval Telegram profil rasmi avtomatik olinardi — egasi: «profil rasmini emas, ishtirokchi o'zi xohlagan rasmini
qo'ya olsin, butun tanasi bilan ko'rinsin». Endi:
  * Ishtirokchi Profil → «⚙️ Kartani sozlash» → «📷 Rasm yuklash» (POST /pcard/me/photo).
  * Server rasmni tekshiradi va qayta kodlaydi (EXIF/zararli ma'lumot tozalanadi), fonini olib tashlab ODAMNI
    BUTUN TANASI bilan qirqadi (player_cutout_worker.py, alohida jarayon, bir vaqtda bittadan).
    Odam topilmasa yoki qirqish o'chiq bo'lsa — rasm o'zicha (fonli) saqlanadi.
  * Kunlik limit — PHOTO_DAILY_LIMIT (CPU'ni suiiste'mol qilmaslik uchun).
  * Rasm yuklanmagan bo'lsa — kartada avvalgidek Telegram profil rasmi (qirqilmagan, chetlari xira).
  * Bosh admin nomaqbul rasmni o'chira oladi (DELETE /pcard/admin/{user_id}/photo).
Jadval — player_card_photos (migratsiya, qoida #31). Model — u2net_human_seg, birinchi marta GitHub'dan.
"""

import asyncio
import hashlib
import io
import logging
import os
import sys
from datetime import date

import httpx

from config import DB_PATH
from models import get_connection

logger = logging.getLogger(__name__)

CUTOUT_ENABLED = os.getenv("PCARD_CUTOUT", "1") != "0"   # .env: PCARD_CUTOUT=0 — fonni olib tashlash o'chadi
PHOTO_DAILY_LIMIT = 5                # bir kunda shuncha marta yuklash mumkin
PHOTO_MAX_BYTES = 8 * 1024 * 1024    # qabul qilinadigan fayl
PHOTO_MAX_SIDE = 1280                # saqlashdan oldin kichraytiriladi
PHOTO_MIN_SIDE = 120                 # juda kichik rasm — rad
PHOTO_JPEG_Q = 88
CUTOUT_WAIT_S = 60                   # navbatda kutish chegarasi
CUTOUT_JOB_TIMEOUT_S = 90
MODEL_NAME = "u2net_human_seg.onnx"
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx"
MODEL_MD5 = "c09ddc2e0104f800e3e1bb4652583d1f"
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "models")
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)
WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_cutout_worker.py")
EXIT_NO_PERSON = 3
KIND_CUT, KIND_PLAIN = "cut", "plain"

_job_lock = asyncio.Lock()
_model_lock = asyncio.Lock()


def migrate_cutouts(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS player_card_photos (user_id INTEGER PRIMARY KEY, ver INTEGER DEFAULT 0, "
                "kind TEXT, img BLOB, day TEXT, day_count INTEGER DEFAULT 0)")


def photo_meta(user_ids) -> dict[int, dict]:
    """{user_id: {"v": versiya, "cut": bool}} — faqat rasm yuklaganlar."""
    ids = [int(u) for u in user_ids if u]
    if not ids:
        return {}
    conn = get_connection()
    try:
        q = ",".join("?" * len(ids))
        rows = conn.execute(f"SELECT user_id, ver, kind FROM player_card_photos WHERE user_id IN ({q}) AND img IS NOT NULL", ids)
        return {r["user_id"]: {"v": r["ver"], "cut": r["kind"] == KIND_CUT} for r in rows}
    except Exception:            # migratsiyadan oldin
        return {}
    finally:
        conn.close()


def get_photo(user_id: int) -> tuple[bytes, str] | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT kind, img FROM player_card_photos WHERE user_id = ?", (user_id,)).fetchone()
    finally:
        conn.close()
    if not r or not r["img"]:
        return None
    return r["img"], ("image/webp" if r["kind"] == KIND_CUT else "image/jpeg")


def delete_photo(user_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE player_card_photos SET img = NULL, kind = NULL, ver = ver + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


def _normalize(raw: bytes) -> bytes:
    """Rasmni tekshirib qayta kodlaydi (JPEG). Noto'g'ri fayl — ValueError."""
    from PIL import Image, ImageOps
    try:
        im = Image.open(io.BytesIO(raw))
        im = ImageOps.exif_transpose(im).convert("RGB")
    except Exception as exc:
        raise ValueError("bad_image") from exc
    if min(im.size) < PHOTO_MIN_SIDE:
        raise ValueError("too_small")
    im.thumbnail((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "JPEG", quality=PHOTO_JPEG_Q, optimize=True)
    return out.getvalue()


def _take_quota(user_id: int) -> bool:
    today = date.today().isoformat()
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        r = conn.execute("SELECT day, day_count FROM player_card_photos WHERE user_id = ?", (user_id,)).fetchone()
        used = r["day_count"] if r and r["day"] == today else 0
        if used >= PHOTO_DAILY_LIMIT:
            conn.rollback()
            return False
        conn.execute("INSERT INTO player_card_photos (user_id, day, day_count) VALUES (?, ?, 1) "
                     "ON CONFLICT(user_id) DO UPDATE SET day = excluded.day, day_count = ?", (user_id, today, used + 1))
        conn.commit()
        return True
    finally:
        conn.close()


def _store(user_id: int, kind: str, img: bytes) -> int:
    conn = get_connection()
    try:
        conn.execute("UPDATE player_card_photos SET kind = ?, img = ?, ver = ver + 1 WHERE user_id = ?", (kind, img, user_id))
        conn.commit()
        return conn.execute("SELECT ver FROM player_card_photos WHERE user_id = ?", (user_id,)).fetchone()["ver"]
    finally:
        conn.close()


async def _ensure_model() -> bool:
    if os.path.exists(MODEL_PATH):
        return True
    async with _model_lock:
        if os.path.exists(MODEL_PATH):
            return True
        os.makedirs(MODEL_DIR, exist_ok=True)
        tmp = MODEL_PATH + ".part"
        md5 = hashlib.md5()
        try:
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as cl:
                async with cl.stream("GET", MODEL_URL) as r:
                    r.raise_for_status()
                    with open(tmp, "wb") as f:
                        async for chunk in r.aiter_bytes():
                            f.write(chunk)
                            md5.update(chunk)
            if md5.hexdigest() != MODEL_MD5:
                raise ValueError("model md5 mos emas")
            os.replace(tmp, MODEL_PATH)
            logger.info("KARTA: odam qirqish modeli yuklab olindi (%s)", MODEL_PATH)
            return True
        except Exception:
            logger.exception("KARTA: model yuklab olinmadi")
            if os.path.exists(tmp):
                os.remove(tmp)
            return False


async def _run_worker(raw: bytes) -> bytes | None:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, WORKER, MODEL_PATH,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(raw), CUTOUT_JOB_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return None
    if proc.returncode == 0 and out:
        return out
    if proc.returncode != EXIT_NO_PERSON:
        logger.warning("KARTA: qirqish xatosi (kod %s): %s", proc.returncode, (err or b"")[-300:].decode("utf-8", "ignore"))
    return None


async def save_upload(user_id: int, raw: bytes) -> tuple[bool, str | dict]:
    """Yuklangan rasm → (True, {"v", "cut"}) yoki (False, xato kodi)."""
    if not raw or len(raw) > PHOTO_MAX_BYTES:
        return False, "too_big"
    try:
        jpeg = await asyncio.to_thread(_normalize, raw)
    except ValueError as exc:
        return False, str(exc)
    if not _take_quota(user_id):
        return False, "daily_limit"
    cut = None
    if CUTOUT_ENABLED and await _ensure_model():
        try:
            await asyncio.wait_for(_job_lock.acquire(), CUTOUT_WAIT_S)
        except (TimeoutError, asyncio.TimeoutError):
            logger.warning("KARTA: qirqish navbati band — rasm fonli saqlanadi (user %s)", user_id)
        else:
            try:
                cut = await _run_worker(jpeg)
            finally:
                _job_lock.release()
    kind = KIND_CUT if cut else KIND_PLAIN
    ver = _store(user_id, kind, cut or jpeg)
    logger.info("KARTA: user %s rasm yukladi — %s", user_id, kind)
    return True, {"v": ver, "cut": kind == KIND_CUT}
