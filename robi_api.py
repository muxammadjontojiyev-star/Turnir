"""
robi_api.py — «ROBI» OVOZI API (2026-11-03). api.py OXIRIDA include_router qilinadi.

  GET  /robi/status            -> {tts, stt}  (Azure kaliti sozlanganmi)
  POST /robi/tts {text, lang}  -> audio/mpeg (robi_voice.synthesize — kesh + bepul limit)
  POST /robi/stt?lang=uz       -> {text}      (tana — 16 kHz mono WAV, robi_stt.transcribe)
Hammasi Telegram initData bilan (get_authenticated_user — umumiy rate-limit ham shu yerda).
Xato kodlari: 503 tts_off/stt_off, 400 empty/too_long/bad_audio/no_speech, 429 quota_*, 502 upstream.
"""

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from api import get_authenticated_user

logger = logging.getLogger(__name__)
router = APIRouter()

_STATUS = {"tts_off": 503, "stt_off": 503, "quota_month": 429, "quota_user": 429, "upstream": 502}
TTS_CLIENT_CACHE_SEC = 86400


def _fail(reason: str):
    raise HTTPException(status_code=_STATUS.get(reason, 400), detail=reason)


@router.get("/robi/status")
def robi_status(user: dict = Depends(get_authenticated_user)):
    from robi_stt import stt_enabled
    from robi_voice import tts_enabled
    return {"tts": tts_enabled(), "stt": stt_enabled()}


@router.post("/robi/tts")
def robi_tts(text: str = Body(..., embed=True), lang: str = Body("uz", embed=True),
             user: dict = Depends(get_authenticated_user)):
    from robi_voice import synthesize
    ok, res = synthesize(text, lang, user["telegram_id"])
    if not ok:
        _fail(res)
    return Response(content=res, media_type="audio/mpeg",
                    headers={"Cache-Control": f"private, max-age={TTS_CLIENT_CACHE_SEC}"})


@router.post("/robi/stt")
async def robi_stt(request: Request, lang: str = "uz", user: dict = Depends(get_authenticated_user)):
    from robi_stt import STT_MAX_BYTES, transcribe
    if int(request.headers.get("content-length") or 0) > STT_MAX_BYTES:
        _fail("too_long")
    data = await request.body()
    ok, res = await run_in_threadpool(transcribe, data, lang, user["telegram_id"])
    if not ok:
        _fail(res)
    return {"text": res}
