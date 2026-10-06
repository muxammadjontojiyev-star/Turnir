"""
pt_pricing.py — SHAXSIY turnir narxlari (2026-10-03). Faqat hisoblash, DB yo'q (qoida #25).

Bir martalik to'lov — sig'imga qarab 3 pog'ona (admin qarori):
  S: 8–20 kishi (PT_PRICE_UZS)   M: 24–64 (PT_PRICE_M_UZS)   L: 68–128 (PT_PRICE_L_UZS)
Obuna (istalgan sig'im): week 7 kun, month 30 kun, year 365 kun.
Narx 0 bo'lsa — o'sha variant mavjud emas (ilovada ko'rinmaydi).
Obunada bir vaqtda faol (yig'ilayotgan/davom etayotgan) turnirlar: SUB_ACTIVE_LIMIT.
"""

from config import (
    PT_PRICE_L_UZS,
    PT_PRICE_M_UZS,
    PT_PRICE_MONTH_UZS,
    PT_PRICE_UZS,
    PT_PRICE_WEEK_UZS,
    PT_PRICE_YEAR_UZS,
)

SUB_ACTIVE_LIMIT = 2

# (pog'ona, eng katta sig'im, narx)
TIERS = [("s", 20, PT_PRICE_UZS), ("m", 64, PT_PRICE_M_UZS), ("l", 128, PT_PRICE_L_UZS)]
PLANS = {"week": (7, PT_PRICE_WEEK_UZS), "month": (30, PT_PRICE_MONTH_UZS), "year": (365, PT_PRICE_YEAR_UZS)}


def tier_for_size(n: int) -> str:
    for tier, top, _ in TIERS:
        if n <= top:
            return tier
    return TIERS[-1][0]


def price_for_size(n: int) -> int:
    """Bir martalik narx; 0 — bu sig'im uchun narx belgilanmagan."""
    tier = tier_for_size(n)
    return next(p for t, _, p in TIERS if t == tier)


def plan_info(plan: str) -> tuple[int, int] | None:
    """(kunlar, narx) yoki None (noma'lum yoki narxi belgilanmagan tarif)."""
    info = PLANS.get(plan)
    return info if info and info[1] > 0 else None


def public_pricing() -> dict:
    """Frontend uchun: pog'onalar va mavjud tariflar."""
    lo = 8
    tiers = []
    for tier, top, price in TIERS:
        tiers.append({"tier": tier, "min": lo, "max": top, "price_uzs": price})
        lo = top + 4
    plans = [{"plan": p, "days": d, "price_uzs": pr} for p, (d, pr) in PLANS.items() if pr > 0]
    return {"tiers": tiers, "plans": plans, "sub_active_limit": SUB_ACTIVE_LIMIT}
