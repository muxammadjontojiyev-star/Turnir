"""
profanity.py — chatdagi haqoratli so'zlarni yashirish (2026-09-22).

Muammo (qoida #52): ishtirokchilar chatda bir-birini so'kmoqda.

Yechim: haqoratli so'z O'RNIGA "***" ko'rsatiladi. Faqat o'sha so'z
yashiriladi, qolgan matn o'qiladi ("sen *** odamsan").

MUHIM DIZAYN QARORI (qoida #19): asl matn bazada O'ZGARISHSIZ saqlanadi,
yashirish faqat KO'RSATISHDA bo'ladi. Sabab:
  - admin nizoda kim nima yozganini AYNAN ko'rishi kerak (chat_report.py);
  - so'z ro'yxati keyin to'g'rilansa, eski xabarlar ham to'g'ri ko'rinadi;
  - noto'g'ri aniqlangan so'z (false positive) matnni butunlay buzmaydi.

Ikkala tomon ham (yozgan odam ham) yashirilgan holda ko'radi — shunda
"men yozganimni u ko'rmadi" degan chalkashlik bo'lmaydi.

RO'YXATNI KENGAYTIRISH: _ROOTS ga yangi o'zak qo'shish kifoya. O'zaklar
so'z CHEGARASI bilan qidiriladi, shuning uchun bexosdan boshqa so'zni
ushlab qolmaydi (masalan "huquq" so'zi ta'sirlanmaydi).
"""

import logging
import re

logger = logging.getLogger(__name__)

MASK = "***"

# Har bir element — so'z O'ZAGI. Qo'shimchalar (-ing, -san, -lar, -ga ...)
# avtomatik qamraladi. Lotin va kirill variantlari alohida yoziladi, chunki
# ishtirokchilar ikkala alifboda ham yozadi.
_ROOTS = [
    # --- o'zbekcha (lotin) ---
    r"ko[’'`ʻ]?t", r"am[ei]ng", r"jala[bp]", r"qan[jc]iq", r"pad[ae]r",
    r"onangni", r"onasini", r"otangni", r"siktir", r"sikish", r"sikaman",
    r"a[hx]moq", r"tentak", r"nodon", r"iflos", r"haromi", r"harom[zx]ada",
    r"eshshak", r"eshak", r"itvach", r"it\s*og[’'`ʻ]?li",
    # --- o'zbekcha (kirill) — ҳ/х va қ/к almashinuvi hisobga olingan ---
    r"[кқ][ўуo]т", r"жала[бп]", r"[кқ]анжи[кқ]", r"падар", r"сиктир",
    r"[ҳх]аром", r"а[ҳх]мо[қк]", r"тентак", r"эшшак", r"ифлос",
    # --- ruscha (kirill) ---
    r"бля", r"сук[аи]", r"пизд", r"ху[йеё]", r"ебат", r"ебан", r"еба[лт]",
    r"пидор", r"мраз", r"гандон", r"долбо",
    # --- ruscha (lotin yozuvida) ---
    r"bly[ae]", r"suk[ai]", r"pizd", r"hu[yj]n", r"eban", r"pidor", r"mraz",
    # --- inglizcha ---
    r"fuck", r"bitch", r"asshole", r"bastard",
]

# Faqat TO'LIQ so'z sifatida qidiriladiganlar — o'zak sifatida qidirilsa
# begunoh so'zlarni ushlab qolardi ("shitake", "dickens").
_EXACT = [r"shit", r"dick", r"ass", r"suk"]

# So'z chegarasi: o'zak so'z boshida turishi va undan keyin faqat harf-qo'shimcha
# kelishi mumkin. (?<![\w]) — oldidan harf bo'lmasin (masalan "huquq" ushlanmasin).
_WORD_RE = re.compile(
    r"(?<![^\W\d_])(?:"
    r"(?:" + "|".join(_ROOTS) + r")[^\W\d_]*"
    r"|(?:" + "|".join(_EXACT) + r")"
    r")(?![^\W\d_])",
    re.IGNORECASE | re.UNICODE,
)


def contains_profanity(text: str) -> bool:
    """Matnda haqoratli so'z bormi?"""
    if not text:
        return False
    return _WORD_RE.search(text) is not None


def mask_text(text: str) -> tuple[str, bool]:
    """
    Haqoratli so'zlarni "***" bilan almashtiradi.

    Qaytaradi: (yashirilgan_matn, topildimi)
    Topilmasa matn O'ZGARISHSIZ qaytadi (qo'shimcha ish bajarilmaydi).
    """
    if not text:
        return text, False
    masked, count = _WORD_RE.subn(MASK, text)
    return masked, count > 0
