"""
robi_stt.py — «ROBI» ESHITADI: ovozli savolni matnga aylantirish (STT), 2026-11-03.

Ilova mikrofon yozuvini telefonning o'zida 16 kHz, 16-bit, mono WAV ga aylantiradi (guide_bot_mic.js) —
serverda ffmpeg kerak emas. Xizmat: Azure AI Speech, BEPUL F0 (qisqa audio REST, 60 soniyagacha).
Tekshiruv: WAV sarlavhasi (PCM 16-bit mono 16 kHz), davomiylik <= ROBI_STT_MAX_SEC, limitlar (robi_usage.py,
oylik soniya va kunlik savol soni). Matn javobda qaytadi va Robining bilimlar bazasidan javob qidiriladi.
Qaytaradi: (True, matn) | (False, sabab): stt_off, bad_audio, too_long, quota_month, quota_user, upstream, no_speech.
"""

import logging
import math
import struct

import httpx

from config import (ROBI_AZURE_KEY, ROBI_AZURE_REGION, ROBI_HTTP_TIMEOUT, ROBI_STT_MAX_SEC,
                    ROBI_STT_MONTHLY_SEC, ROBI_STT_USER_DAILY)
from robi_usage import KIND_STT, release, reserve
from robi_voice import tts_enabled

logger = logging.getLogger(__name__)

STT_LANGS = {"uz": "uz-UZ", "ru": "ru-RU", "en": "en-US"}
WAV_RATE, WAV_BITS, WAV_CHANNELS = 16000, 16, 1
WAV_HEADER_MAX = 512                       # sarlavha qidiriladigan bayt chegarasi
STT_MAX_BYTES = 64 + WAV_RATE * (WAV_BITS // 8) * 60   # 60 soniyadan katta fayl qabul qilinmaydi


def stt_enabled() -> bool:
    return tts_enabled()                   # bitta Azure kaliti ikkalasiga


def wav_seconds(data: bytes) -> float | None:
    """16 kHz / 16-bit / mono PCM WAV bo'lsa — davomiylik (soniya), aks holda None."""
    if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    pos, fmt_ok = 12, False
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = pos + 8
        if cid == b"fmt " and size >= 16:
            fmt, ch, rate, _, _, bits = struct.unpack("<HHIIHH", data[body:body + 16])
            fmt_ok = (fmt, ch, rate, bits) == (1, WAV_CHANNELS, WAV_RATE, WAV_BITS)
        elif cid == b"data":
            if not fmt_ok:
                return None
            size = min(size, len(data) - body)
            return size / (WAV_RATE * WAV_CHANNELS * WAV_BITS // 8)
        if body > WAV_HEADER_MAX and cid != b"data":
            return None
        pos = body + size + (size & 1)
    return None


def _azure_stt(data: bytes, lang: str) -> tuple[bool, str]:
    try:
        r = httpx.post(f"https://{ROBI_AZURE_REGION}.stt.speech.microsoft.com/speech/recognition/"
                       "conversation/cognitiveservices/v1",
                       params={"language": STT_LANGS[lang], "format": "simple", "profanity": "masked"},
                       content=data, timeout=ROBI_HTTP_TIMEOUT,
                       headers={"Ocp-Apim-Subscription-Key": ROBI_AZURE_KEY,
                                "Content-Type": f"audio/wav; codecs=audio/pcm; samplerate={WAV_RATE}"})
    except httpx.HTTPError as exc:
        logger.warning("Robi STT: tarmoq xatosi: %s", exc)
        return False, "upstream"
    if r.status_code != 200:
        logger.warning("Robi STT: Azure javobi %s", r.status_code)
        return False, "upstream"
    try:
        js = r.json()
    except ValueError:
        return False, "upstream"
    text = (js.get("DisplayText") or "").strip()
    if js.get("RecognitionStatus") != "Success" or not text:
        return False, "no_speech"
    return True, text


def transcribe(data: bytes, lang: str, telegram_id: int) -> tuple[bool, str]:
    if not stt_enabled():
        return False, "stt_off"
    lang = lang if lang in STT_LANGS else "uz"
    if len(data) > STT_MAX_BYTES:
        return False, "too_long"
    sec = wav_seconds(data)
    if sec is None or sec <= 0:
        return False, "bad_audio"
    if sec > ROBI_STT_MAX_SEC + 0.5:
        return False, "too_long"
    cost = max(1, math.ceil(sec))
    ok, reason = reserve(KIND_STT, telegram_id, cost, ROBI_STT_MONTHLY_SEC, ROBI_STT_USER_DAILY)
    if not ok:
        return False, reason
    ok, text = _azure_stt(data, lang)
    if not ok and text == "upstream":
        release(KIND_STT, telegram_id, cost)      # xizmat ishlamadi — limit qaytadi
    return ok, text
