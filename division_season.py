"""
division_season.py — Divizion mavsumi (2026-07-21).

1 mavsum = 1 oy. Chegara — har oyning DIV_SEASON_FIRST_DAY sanasidagi kuni
(masalan 10-sana): 1-mavsum 10-iyul .. 10-avgust (10-avgust KIRMAYDI),
2-mavsum 10-avgust .. 10-sentabr va hokazo.

Reyting har mavsumda NOLDAN boshlanadi, o'yin tarixi saqlanadi. Buning uchun
div_matches jadvaliga `season` ustuni QO'SHILMAYDI — o'yinning `day` (sana)
ustuni mavsumni allaqachon aniqlaydi, shuning uchun reyting shunchaki joriy
mavsum sana oralig'i bo'yicha filtrlanadi (migratsiya shart emas, qoida #31).

Muhim: chegara kuni har oyda mavjud bo'lishi kerak (1..28 oralig'ida tanlansin) —
29/30/31 kabi sanalar hamma oyda bo'lmagani uchun qo'llab-quvvatlanmaydi.
"""

import logging
from datetime import date

from config import DIV_SEASON_FIRST_DAY
from queries_leagues import _tournament_now

logger = logging.getLogger(__name__)


def _first_day() -> date:
    return date.fromisoformat(DIV_SEASON_FIRST_DAY)


def _add_months(d: date, months: int) -> date:
    """Sanaga oy qo'shadi (kun o'zgarmaydi — chegara kuni 1..28 bo'lgani uchun xavfsiz)."""
    total = (d.year * 12 + d.month - 1) + months
    return date(total // 12, total % 12 + 1, d.day)


def div_season_for(day: str) -> dict:
    """
    Berilgan sana (ISO "YYYY-MM-DD") qaysi mavsumga tegishli.

    Qaytaradi:
      {"number": int, "start": ISO, "end": ISO (kirmaydi),
       "total_days": int, "day_index": int, "days_left": int}

      day_index  — mavsum boshlanganiga necha kun bo'ldi (birinchi kuni = 1)
      days_left  — mavsum tugashiga qolgan kunlar (oxirgi kunida = 1)

    1-mavsumdan OLDINGI sanalar uchun ham 1-mavsum oralig'i qaytariladi
    (eski o'yinlar reytingga kirmaydi, lekin tarixda qoladi).
    """
    d = date.fromisoformat(day)
    first = _first_day()

    months = (d.year - first.year) * 12 + (d.month - first.month)
    if d.day < first.day:
        months -= 1
    if months < 0:      # 1-mavsumdan oldin
        months = 0

    start = _add_months(first, months)
    end = _add_months(first, months + 1)

    total_days = (end - start).days
    day_index = (d - start).days + 1
    days_left = (end - d).days
    # Mavsumdan oldingi sana bo'lsa ko'rsatkichlar chegaradan chiqmasin
    day_index = max(1, min(day_index, total_days))
    days_left = max(0, min(days_left, total_days))

    return {
        "number": months + 1,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total_days": total_days,
        "day_index": day_index,
        "days_left": days_left,
    }


def div_current_season() -> dict:
    """Bugungi (Toshkent vaqti) mavsum ma'lumoti — div_season_for bilan bir xil shakl."""
    return div_season_for(_tournament_now().date().isoformat())


def div_season_range(day: str | None = None) -> tuple[str, str]:
    """
    Reyting so'rovlari uchun sana oralig'i: (start, end) — `day >= start AND day < end`.
    day berilmasa joriy mavsum.
    """
    season = div_season_for(day) if day else div_current_season()
    return season["start"], season["end"]
