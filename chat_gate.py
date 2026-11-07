"""
chat_gate.py — QO'LDA NATIJA KIRITISH CHAT SHARTI (2026-11-07, chat_rules.manual_check).

Barcha rejimlarning qo'lda natija endpointlari (HTTP) tekshiriladi — rejim fayllariga tegilmaydi:
  * o'yinga kelishilgan vaqt hali kelmagan bo'lsa — rad («crule_err_agree_locked»);
  * ikkala ishtirokchi shu o'yin chatida kamida 1 marta yozmagan bo'lsa — rad (raqib jim — faqat tex win 3:0).
Xato matni foydalanuvchi tilida qaytadi (rejimlarning xato toast'i noma'lum kodni o'zicha ko'rsatadi).
Tasdiqlash / rad etish, admin tuzatishlari, skrinshotli natija va tex win (Python ichidan chaqiriladi) — tegilmaydi.
Ichki xato bo'lsa — so'rov o'tkaziladi (rejimning o'z tekshiruvlari ishlaydi) va logga yoziladi.
"""

import asyncio
import logging
import re

logger = logging.getLogger(__name__)

PATH_MODES = {
    "/match/submit-result": "league", "/wc/match/submit-result": "wc", "/wc/playoff/submit-result": "wc_po",
    "/cl/match/submit-result": "cl", "/cl/playoff/submit-result": "cl_po", "/div/match/submit-result": "div",
    "/el/match/submit-result": "el", "/el/playoff/submit-result": "el_po",
    "/ac/match/submit-result": "ac", "/ac/playoff/submit-result": "ac_po",
    "/co/match/submit-result": "co", "/co/playoff/submit-result": "co_po",
}
PT_RESULT_RE = re.compile(r"^/pt/match/(\d+)/result$")
ERR_KEY = "crule_err_{}"


def target(method: str, path: str, query: dict) -> tuple[str | None, int | None]:
    if method != "POST":
        return None, None
    path = path.rstrip("/")
    m = PT_RESULT_RE.match(path)
    if m:
        return "pt", int(m.group(1))
    mode = PATH_MODES.get(path)
    if not mode:
        return None, None
    try:
        return mode, int(query.get("match_id"))
    except (TypeError, ValueError):
        return None, None


def check(mode: str, match_id: int, init_data: str) -> str | None:
    """Rad etish matni (foydalanuvchi tilida) yoki None — o'tkazish."""
    from fastapi import HTTPException
    from api import verify_telegram_init_data
    from chat_rules import manual_check
    from match_modes import get_match
    from queries_users import get_user_by_telegram_id
    from texts import t
    try:
        tg = verify_telegram_init_data(init_data or "")
    except HTTPException:
        return None                                      # autentifikatsiya xatosini endpointning o'zi qaytaradi
    user = get_user_by_telegram_id(tg["id"])
    match = get_match(mode, match_id)
    if not user or not match:
        return None
    ok, why, info = manual_check(mode, match, user["id"])
    if ok:
        return None
    logger.info("CHAT SHARTI: %s #%s — user %s qo'lda natija rad: %s", mode, match_id, user["id"], why)
    text = t(ERR_KEY.format(why), user.get("language") or "uz")
    try:
        return text.format(**info)
    except (KeyError, IndexError):
        return text


def install(app) -> None:
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def _chat_gate(request, call_next):
        mode, mid = target(request.method, request.url.path, dict(request.query_params))
        if mode:
            try:
                err = await asyncio.to_thread(check, mode, mid, request.headers.get("x-telegram-init-data", ""))
            except Exception:
                logger.exception("CHAT SHARTI: tekshiruv xatosi (%s #%s) — o'tkazildi", mode, mid)
                err = None
            if err:
                return JSONResponse(status_code=400, content={"detail": err})
        return await call_next(request)
