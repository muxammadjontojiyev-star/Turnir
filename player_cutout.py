"""
player_cutout.py — SHAXSIY KARTA uchun ishtirokchi rasmidan FAQAT ODAMNI qirqish (2026-11-04, egasi so'rovi).

Endpoint (player_card_api.py): GET /players/{user_id}/cutout — shaffof fonli WEBP; odam topilmasa / rasm
yo'q / xato — 404 (frontend butun rasmni xira chetli qilib ko'rsatadi).
  * Telegram'dan profil rasmining ENG KATTA o'lchami olinadi (avatar uchun kichigi yetarli edi, karta uchun emas).
  * Natija bazada keshlanadi (player_cutouts): rasm o'zgarmaguncha qayta hisoblanmaydi (file_unique_id);
    Telegram'ga har CUTOUT_RECHECK_S da bir marta murojaat qilinadi.
  * Hisoblash — alohida jarayonda (player_cutout_worker.py), bir vaqtda bittadan (CPU/xotira); navbat
    CUTOUT_WAIT_S dan uzun bo'lsa — 503, frontend keyingi ochilishda yana so'raydi.
  * Model (u2net_human_seg, 168 MB) birinchi marta GitHub'dan yuklab olinadi va baza papkasida saqlanadi.
Kalitlar — .env: BOT_TOKEN (mavjud). Sozlamalar — quyidagi nomlangan konstantalar.
"""

import asyncio
import hashlib
import logging
import os
import sys
import time

import httpx

from config import BOT_TOKEN, DB_PATH
from models import get_connection

logger = logging.getLogger(__name__)

CUTOUT_ENABLED = os.getenv("PCARD_CUTOUT", "1") != "0"   # .env: PCARD_CUTOUT=0 — o'chirish (xotira kam bo'lsa)
CUTOUT_RECHECK_S = 6 * 3600          # rasm o'zgarganini tekshirish oralig'i
CUTOUT_FAIL_RETRY_S = 3600           # xato bo'lsa — qayta urinish oralig'i
CUTOUT_WAIT_S = 25                   # navbatda kutish chegarasi
CUTOUT_JOB_TIMEOUT_S = 90            # bitta qirqish (model yuklash bilan)
TG_TIMEOUT_S = 10
MODEL_NAME = "u2net_human_seg.onnx"
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx"
MODEL_MD5 = "c09ddc2e0104f800e3e1bb4652583d1f"
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "models")
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_NAME)
WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_cutout_worker.py")
EXIT_NO_PERSON = 3
ST_OK, ST_NONE, ST_ERR = "ok", "none", "err"

_job_lock = asyncio.Lock()
_model_lock = asyncio.Lock()


def migrate_cutouts(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS player_cutouts (user_id INTEGER PRIMARY KEY, photo_uid TEXT, "
                "status TEXT, img BLOB, checked_at REAL)")


def _row(user_id: int):
    conn = get_connection()
    try:
        return conn.execute("SELECT photo_uid, status, img, checked_at FROM player_cutouts WHERE user_id = ?",
                            (user_id,)).fetchone()
    finally:
        conn.close()


def _save(user_id: int, photo_uid: str | None, status: str, img: bytes | None) -> None:
    conn = get_connection()
    try:
        conn.execute("INSERT INTO player_cutouts (user_id, photo_uid, status, img, checked_at) VALUES (?,?,?,?,?) "
                     "ON CONFLICT(user_id) DO UPDATE SET photo_uid = excluded.photo_uid, status = excluded.status, "
                     "img = excluded.img, checked_at = excluded.checked_at",
                     (user_id, photo_uid, status, img, time.time()))
        conn.commit()
    finally:
        conn.close()


def _touch(user_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE player_cutouts SET checked_at = ? WHERE user_id = ?", (time.time(), user_id))
        conn.commit()
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


async def _tg_photo(telegram_id: int) -> tuple[str, bytes] | None:
    """(file_unique_id, baytlar) — eng katta o'lcham; rasm yo'q bo'lsa None."""
    base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    async with httpx.AsyncClient(timeout=TG_TIMEOUT_S) as cl:
        r1 = (await cl.get(f"{base}/getUserProfilePhotos", params={"user_id": telegram_id, "limit": 1})).json()
        photos = r1.get("result", {}).get("photos") or []
        if not photos or not photos[0]:
            return None
        big = photos[0][-1]
        fp = (await cl.get(f"{base}/getFile", params={"file_id": big["file_id"]})).json().get("result", {}).get("file_path")
        if not fp:
            return None
        r3 = await cl.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}")
        r3.raise_for_status()
        return big["file_unique_id"], r3.content


async def _run_worker(raw: bytes) -> tuple[str, bytes | None]:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, WORKER, MODEL_PATH,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(raw), CUTOUT_JOB_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return ST_ERR, None
    if proc.returncode == 0 and out:
        return ST_OK, out
    if proc.returncode == EXIT_NO_PERSON:
        return ST_NONE, None
    logger.warning("KARTA: qirqish xatosi (kod %s): %s", proc.returncode, (err or b"")[-300:].decode("utf-8", "ignore"))
    return ST_ERR, None


async def get_cutout(user_id: int, telegram_id: int) -> bytes | None:
    """Tayyor bo'lsa WEBP baytlari; aks holda None. Navbat band bo'lsa — TimeoutError."""
    if not CUTOUT_ENABLED:
        return None
    row = _row(user_id)
    if row:
        age = time.time() - (row["checked_at"] or 0)
        if age < (CUTOUT_FAIL_RETRY_S if row["status"] == ST_ERR else CUTOUT_RECHECK_S):
            return row["img"] if row["status"] == ST_OK else None
    try:
        ph = await _tg_photo(telegram_id)
    except Exception:
        logger.warning("KARTA: Telegram rasmi olinmadi (user %s)", user_id)
        return row["img"] if row and row["status"] == ST_OK else None
    if ph is None:
        _save(user_id, None, ST_NONE, None)
        return None
    uid, raw = ph
    if row and row["photo_uid"] == uid and row["status"] != ST_ERR:
        _touch(user_id)
        return row["img"] if row["status"] == ST_OK else None
    if not await _ensure_model():
        _save(user_id, uid, ST_ERR, None)
        return None
    await asyncio.wait_for(_job_lock.acquire(), CUTOUT_WAIT_S)   # TimeoutError — chaqiruvchi 503 qaytaradi
    try:
        again = _row(user_id)                                      # navbatda turganda boshqasi qilib qo'ygan bo'lsa
        if again and again["photo_uid"] == uid and again["status"] != ST_ERR:
            return again["img"] if again["status"] == ST_OK else None
        status, img = await _run_worker(raw)
    finally:
        _job_lock.release()
    _save(user_id, uid, status, img)
    logger.info("KARTA: user %s rasmi qirqildi — %s", user_id, status)
    return img
