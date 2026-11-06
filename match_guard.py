"""
match_guard.py — NATIJA FAQAT SKRINSHOT BILAN (2026-11-06, egasi: «natija kiritish faqat skrinshot orqali bo'lsin»).

  * Kalit — app_flags.shot_only. 2026-11-06 dan O'CHIQ (egasi: «qo'lda kiritishni ham qo'shing» — ikkalasi ham
    ishlaydi; migrate_flags bir marta o'chiradi). Bosh admin Admin → «📸 SKRINSHOT VA TEXNIK G'ALABA» da
    o'chira oladi (masalan, skrinshot o'qish xizmati ishlamay qolsa — favqulodda holat).
  * Yoqiq paytda barcha rejimlarning QO'LDA natija kiritish endpointlari (HTTP) rad etiladi: 400 «screenshot_only».
    Skrinshotli natija (match_shot.py) shu funksiyalarni Python ichidan chaqiradi — HTTP emas, shuning uchun o'tadi.
  * Istisno: pley-offda DURANG (penaltilar seriyasi) — qo'lda kiritiladi (skrinshotda penaltilar hozircha o'qilmaydi).
  * Tasdiqlash / rad etish, admin tuzatishlari, tezkor o'yin va jamoaviy bahs — o'zgarishsiz.
"""

import logging
import re

from models import get_connection

logger = logging.getLogger(__name__)

FLAG_SHOT_ONLY = "shot_only"
MANUAL_SUBMIT_PATHS = {
    "/match/submit-result", "/wc/match/submit-result", "/cl/match/submit-result", "/div/match/submit-result",
    "/el/match/submit-result", "/ac/match/submit-result", "/co/match/submit-result",
}
PLAYOFF_SUBMIT_PATHS = {
    "/wc/playoff/submit-result", "/cl/playoff/submit-result", "/el/playoff/submit-result",
    "/ac/playoff/submit-result", "/co/playoff/submit-result",
}
PT_RESULT_RE = re.compile(r"^/pt/match/\d+/result$")
ERR_SHOT_ONLY = "screenshot_only"


FLAG_RESET_MARK = "shot_only_reset_20261106"   # bir martalik: egasi «qo'lda kiritishni ham qo'shing» (2026-11-06)


def migrate_flags(cur) -> None:
    cur.execute("CREATE TABLE IF NOT EXISTS app_flags (key TEXT PRIMARY KEY, value TEXT)")
    # bir marta: qo'lda kiritish yana ochiladi (skrinshot ham qoladi). Keyin bosh admin xohlasa kalit bilan yopadi.
    if not cur.execute("SELECT 1 FROM app_flags WHERE key = ?", (FLAG_RESET_MARK,)).fetchone():
        cur.execute("INSERT INTO app_flags (key, value) VALUES (?, '0') ON CONFLICT(key) DO UPDATE SET value = '0'",
                    (FLAG_SHOT_ONLY,))
        cur.execute("INSERT INTO app_flags (key, value) VALUES (?, '1')", (FLAG_RESET_MARK,))


def shot_only() -> bool:
    conn = get_connection()
    try:
        r = conn.execute("SELECT value FROM app_flags WHERE key = ?", (FLAG_SHOT_ONLY,)).fetchone()
    except Exception:
        return True
    finally:
        conn.close()
    return r is None or r["value"] == "1"


def set_shot_only(on: bool) -> bool:
    conn = get_connection()
    try:
        conn.execute("INSERT INTO app_flags (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                     (FLAG_SHOT_ONLY, "1" if on else "0"))
        conn.commit()
    finally:
        conn.close()
    logger.info("NATIJA FAQAT SKRINSHOT: %s", "YOQILDI" if on else "O'CHIRILDI")
    return bool(on)


def blocks(method: str, path: str, query: dict) -> bool:
    """Shu so'rov rad etiladimi (qo'lda natija kiritish)?"""
    if method != "POST":
        return False
    path = path.rstrip("/")
    if path in PLAYOFF_SUBMIT_PATHS:
        if query.get("score1") is not None and query.get("score1") == query.get("score2"):
            return False                               # pley-off durang — penaltilar, qo'lda
    elif path not in MANUAL_SUBMIT_PATHS and not PT_RESULT_RE.match(path):
        return False
    return shot_only()


def install(app) -> None:
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def _shot_only_guard(request, call_next):
        if blocks(request.method, request.url.path, dict(request.query_params)):
            return JSONResponse(status_code=400, content={"detail": ERR_SHOT_ONLY})
        return await call_next(request)
