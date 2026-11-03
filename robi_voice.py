"""
robi_voice.py — «ROBI» GAPIRADI: matnni ovozga aylantirish (TTS), 2026-11-03.

Xizmat: Microsoft Azure AI Speech, BEPUL F0 tarif (config.ROBI_AZURE_KEY / ROBI_AZURE_REGION — faqat .env).
Ovozlar: o'zbek — Madina, rus — Svetlana, ingliz — Jenny (config.ROBI_VOICE_*), biroz baland va tez
(ROBI_VOICE_PITCH / RATE) — robotchaga mos yoqimli ohang.
  * Har matn BIR MARTA yaratiladi va keshga yoziladi (fayl, baza yonida) — Robining tayyor gaplari
    keyin limit sarflamaydi; faqat yangi matnlar (savollarga javoblar) hisobga kiradi (robi_usage.py).
  * Matn tozalanadi: **qalin**, emoji olinadi; qisqartmalar to'liq o'qiladi (ChL -> Chempionlar ligasi).
  * SSML ichiga faqat escape qilingan matn tushadi; ovoz nomi / ohang qiymatlari regex bilan tekshiriladi.
Qaytaradi: (True, mp3 bytes) | (False, sabab): tts_off, empty, too_long, quota_month, quota_user, upstream.
"""

import hashlib
import logging
import os
import re
from xml.sax.saxutils import escape

import httpx

from config import (DB_PATH, ROBI_AZURE_KEY, ROBI_AZURE_REGION, ROBI_HTTP_TIMEOUT, ROBI_TTS_CACHE_DIR,
                    ROBI_TTS_MAX_CHARS, ROBI_TTS_MONTHLY_CHARS, ROBI_TTS_USER_DAILY, ROBI_VOICE_EN,
                    ROBI_VOICE_PITCH, ROBI_VOICE_RATE, ROBI_VOICE_RU, ROBI_VOICE_UZ)
from robi_usage import KIND_TTS, release, reserve

logger = logging.getLogger(__name__)

LANGS = {"uz": ("uz-UZ", ROBI_VOICE_UZ), "ru": ("ru-RU", ROBI_VOICE_RU), "en": ("en-US", ROBI_VOICE_EN)}
OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
_VOICE_RE = re.compile(r"^[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural$")
_PROSODY_RE = re.compile(r"^[+-]?\d{1,2}%$")
_REGION_RE = re.compile(r"^[a-z0-9]{3,30}$")
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍⃣]")
# Qisqartmalar — ovozda to'liq (so'z chegarasi bilan; uzunroq qisqartma oldin)
_SAY = {
    "uz": ((r"OChL", "Osiyo Chempionlar ligasi"), (r"ChL", "Chempionlar ligasi"), (r"YeL", "Yevropa ligasi"),
           (r"JCh", "Jahon chempionati"), (r"KL", "Konferensiya ligasi"), (r"eF Token", "i-ef token"),
           (r"1v1", "birga-bir"), (r"TOP-(\d+)", r"top \1")),
    "ru": ((r"ЛЧ", "Лига чемпионов"), (r"ЛЕ", "Лига Европы"), (r"ЧМ", "чемпионат мира"),
           (r"eF Token", "и-эф токен"), (r"1v1", "один на один"), (r"ТОП-(\d+)", r"топ \1")),
    "en": ((r"UCL", "Champions League"), (r"UEL", "Europa League"), (r"WC", "World Cup"),
           (r"1v1", "one on one"), (r"TOP-(\d+)", r"top \1")),
}


def tts_enabled() -> bool:
    return bool(ROBI_AZURE_KEY and _REGION_RE.match(ROBI_AZURE_REGION or ""))


def clean_text(text: str, lang: str) -> str:
    s = str(text or "").replace("**", "")
    s = _EMOJI_RE.sub("", s)
    s = re.sub(r"\s*—\s*", ", ", s.replace("«", "").replace("»", ""))
    for pat, rep in _SAY.get(lang, ()):
        s = re.sub(rf"(?<![\w-]){pat}(?![\w])", rep, s)
    return re.sub(r"\s+", " ", s).strip()


def _voice(lang: str) -> tuple[str, str]:
    code, voice = LANGS.get(lang, LANGS["uz"])
    if not _VOICE_RE.match(voice):
        logger.warning("Robi: ovoz nomi noto'g'ri (%s) — standart ishlatiladi", voice)
        voice = {"uz-UZ": "uz-UZ-MadinaNeural", "ru-RU": "ru-RU-SvetlanaNeural"}.get(code, "en-US-JennyNeural")
    return code, voice


def _prosody(v: str, default: str) -> str:
    return v if _PROSODY_RE.match(v or "") else default


def _cache_dir() -> str:
    return ROBI_TTS_CACHE_DIR or os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "robi_tts_cache")


def _cache_path(code: str, voice: str, pitch: str, rate: str, text: str) -> str:
    key = hashlib.sha256(f"{code}|{voice}|{pitch}|{rate}|{text}".encode("utf-8")).hexdigest()
    return os.path.join(_cache_dir(), f"{key}.mp3")


def _cache_read(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def _cache_write(path: str, data: bytes) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)          # yarim yozilgan fayl ko'rinmaydi
    except OSError:
        logger.exception("Robi: ovoz keshiga yozib bo'lmadi")


def _azure_tts(code: str, voice: str, pitch: str, rate: str, text: str) -> bytes | None:
    ssml = (f"<speak version='1.0' xml:lang='{code}'><voice name='{voice}'>"
            f"<prosody pitch='{pitch}' rate='{rate}'>{escape(text)}</prosody></voice></speak>")
    try:
        r = httpx.post(f"https://{ROBI_AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
                       content=ssml.encode("utf-8"), timeout=ROBI_HTTP_TIMEOUT,
                       headers={"Ocp-Apim-Subscription-Key": ROBI_AZURE_KEY,
                                "Content-Type": "application/ssml+xml",
                                "X-Microsoft-OutputFormat": OUTPUT_FORMAT, "User-Agent": "turnir-robi"})
    except httpx.HTTPError as exc:
        logger.warning("Robi TTS: tarmoq xatosi: %s", exc)
        return None
    if r.status_code != 200 or not r.content:
        logger.warning("Robi TTS: Azure javobi %s", r.status_code)   # kalit logga yozilmaydi
        return None
    return r.content


def synthesize(text: str, lang: str, telegram_id: int) -> tuple[bool, bytes | str]:
    if not tts_enabled():
        return False, "tts_off"
    lang = lang if lang in LANGS else "uz"
    clean = clean_text(text, lang)
    if not clean:
        return False, "empty"
    if len(clean) > ROBI_TTS_MAX_CHARS:
        return False, "too_long"
    code, voice = _voice(lang)
    pitch, rate = _prosody(ROBI_VOICE_PITCH, "+8%"), _prosody(ROBI_VOICE_RATE, "+4%")
    path = _cache_path(code, voice, pitch, rate, clean)
    cached = _cache_read(path)
    if cached:
        return True, cached
    ok, reason = reserve(KIND_TTS, telegram_id, len(clean), ROBI_TTS_MONTHLY_CHARS, ROBI_TTS_USER_DAILY)
    if not ok:
        return False, reason
    audio = _azure_tts(code, voice, pitch, rate, clean)
    if audio is None:
        release(KIND_TTS, telegram_id, len(clean))
        return False, "upstream"
    _cache_write(path, audio)
    return True, audio
