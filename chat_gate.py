"""
chat_gate.py — QO'LDA NATIJA KIRITISH CHAT SHARTI (2026-11-07, chat_rules.manual_check).

Barcha rejimlarning qo'lda natija endpointlari (HTTP) tekshiriladi — rejim fayllariga tegilmaydi:
  * o'yinga kelishilgan vaqt hali kelmagan bo'lsa — rad («crule_err_agree_locked»);
  * bot chatida xona ID almashilmagan bo'lsa (bir tomon yuborib, ikkinchisi chatdan nusxalamagan) — rad (chat_room.py).
Xato matni foydalanuvchi tilida qaytadi (rejimlarning xato toast'i noma'lum kodni o'zicha ko'rsatadi).
Tasdiqlash / rad etish, admin tuzatishlari, skrinshotli natija va tex win (Python ichidan chaqiriladi) — tegilmaydi.
YIRIK HISOB (2026-11-07, egasi): biror tomon MAX_NORMAL_SCORE dan ko'p gol — qo'lda qabul qilinmaydi, «big_needs_shot|…»
  kodi qaytadi → ilova skrinshot oynasini ochadi; skrinshotdagi hisob kiritilgan bilan bir xil bo'lsa — darhol tasdiq
  (match_shot.apply_shot expect). Xususiy turnir — o'z tartibida (pt_bigscore).
«WIN SIZGA» (chat_concede.py): raqib taslim iborasini yozgan (rad etmagan) bo'lsa — xona ID siz FAQAT o'z foydangizga 3:0.
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


BIG_CODE = "big_needs_shot"      # frontend (crule.js) ushlaydi → skrinshot oynasi; matn emas, kod qaytadi
BIG_SKIP_MODES = {"pt"}         # xususiy turnir: natija JSON tanada — yirik hisob kodi endpointning o'zida (pt_api_play)


def big_score(query: dict) -> tuple[int, int] | None:
    """Qo'lda kiritilgan hisob YIRIK bo'lsa (rejimlardagi MAX_NORMAL_SCORE qoidasi) — (score1, score2)."""
    from config import MAX_NORMAL_SCORE
    try:
        s1, s2 = int(query.get("score1")), int(query.get("score2"))
    except (TypeError, ValueError):
        return None
    return (s1, s2) if max(s1, s2) > MAX_NORMAL_SCORE else None


def _concede_30(mode: str, match: dict, me: int, query: dict) -> bool:
    """Raqib «win sizga» degan va men aynan o'z foydamga 3:0 kiritayapman (chat_concede.py)."""
    from chat_concede import waiver_for
    from chat_rules import TECH_SCORE
    try:
        s1, s2 = int(query.get("score1")), int(query.get("score2"))
    except (TypeError, ValueError):
        return False
    want = (TECH_SCORE, 0) if me == match.get("player1_id") else (0, TECH_SCORE)
    return (s1, s2) == want and waiver_for(mode, match, me)


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


def check(mode: str, match_id: int, init_data: str, query: dict | None = None) -> str | None:
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
    from chat_agree import active_lock
    big = big_score(query or {}) if mode not in BIG_SKIP_MODES else None
    if big and not active_lock(mode, match_id) and user["id"] in (match.get("player1_id"), match.get("player2_id")):
        logger.info("CHAT SHARTI: %s #%s — yirik hisob %s:%s, skrinshot so'raladi", mode, match_id, *big)
        return f"{BIG_CODE}|{mode}|{match_id}|{big[0]}|{big[1]}"   # 2026-11-07: yirik hisob — faqat skrinshot bilan
    ok, why, info = manual_check(mode, match, user["id"])
    if ok:
        return None
    if why.startswith("room_") and _concede_30(mode, match, user["id"], query or {}):
        return None                                      # raqib «win sizga» degan — xona ID siz faqat 3:0
    if why.startswith("room_"):
        from chat_concede import waiver_for
        if waiver_for(mode, match, user["id"]):
            why = "concede_only_30"
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
                err = await asyncio.to_thread(check, mode, mid, request.headers.get("x-telegram-init-data", ""),
                                              dict(request.query_params))
            except Exception:
                logger.exception("CHAT SHARTI: tekshiruv xatosi (%s #%s) — o'tkazildi", mode, mid)
                err = None
            if err:
                return JSONResponse(status_code=400, content={"detail": err})
        return await call_next(request)
