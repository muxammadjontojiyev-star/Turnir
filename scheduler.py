"""
scheduler.py — Turnir matchday (tur) ochilishi bildirishnomalarini yuboruvchi
background scheduler.

Botdan va API'dan MUSTAQIL alohida thread'da ishlaydi (xuddi API kabi). Botning
polling jarayoniga tegmaydi. Xabarlarni mavjud notify.py (httpx → Telegram) orqali
yuboradi, shuning uchun yangi dependency talab qilmaydi.

Mexanizm:
- Har CHECK_INTERVAL_SECONDS soniyada vaqtni tekshiradi.
- Har kuni MATCHDAY_UNLOCK_HOUR (01:00, Toshkent) atrofidagi oynada (yoki bot
  o'chiq turgan vaqt o'tkazib yuborilgan bo'lsa keyinroq ham), qaysi ligalarda
  yangi tur ochilganini aniqlaydi (queries.get_leagues_needing_matchday_notice)
  va ishtirokchilarga "Tur ochildi" xabarini yuboradi.
- last_notified_matchday DB'da saqlanadi → idempotent: bot qayta ishga tushsa
  ham bir tur uchun xabar bir marta yuboriladi.

DIQQAT: cheklov mantig'i (kelajak tur natijasini kiritmaslik) bu scheduler'ga
BOG'LIQ EMAS — u get_open_matchday'dan real vaqtda hisoblanadi (api.py). Scheduler
faqat xabar yuborish uchun; ishlamay qolsa ham natija cheklovi ishlayveradi.
"""

import asyncio
import logging
import threading

from queries import (
    get_leagues_needing_matchday_notice,
    set_last_notified_matchday,
    get_league_members_for_notify,
)
from notify import notify_members

logger = logging.getLogger(__name__)

# Har necha soniyada bir tekshiramiz (60s — daqiqada bir marta yetarli)
CHECK_INTERVAL_SECONDS = 60


async def _check_and_notify_once() -> None:
    """
    Bir martalik tekshiruv: yangi tur ochilgan ligalarga xabar yuboradi.
    Xato bo'lsa jim yutiladi (bitta liga qolganlarini to'xtatmasligi kerak).
    """
    try:
        leagues = get_leagues_needing_matchday_notice()
    except Exception as exc:
        logger.warning("Scheduler: ligalarni olishda xato: %s", exc)
        return

    for lg in leagues:
        league_id = lg["league_id"]
        open_md = lg["open_matchday"]
        try:
            members = get_league_members_for_notify(league_id)
            await notify_members(members, "notify_matchday_open", matchday=open_md)
            # Xabar yuborilgach belgilaymiz — takror yuborilmasligi uchun
            set_last_notified_matchday(league_id, open_md)
            logger.info(
                "Scheduler: '%s' ligasida %d-tur ochildi xabari yuborildi (%d a'zo).",
                lg["name"], open_md, len(members),
            )
        except Exception as exc:
            logger.warning(
                "Scheduler: '%s' ligasiga xabar yuborishda xato: %s", lg["name"], exc
            )


async def _scheduler_loop() -> None:
    """Cheksiz tekshiruv tsikli."""
    logger.info("Matchday scheduler ishga tushdi (har %ds tekshiradi).", CHECK_INTERVAL_SECONDS)
    while True:
        await _check_and_notify_once()
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def _run_scheduler_thread() -> None:
    """Yangi event loop yaratib, scheduler tsiklini ishga tushiradi (alohida thread uchun)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_scheduler_loop())
    except Exception as exc:
        logger.error("Scheduler thread to'xtadi: %s", exc)


def start_scheduler() -> threading.Thread:
    """
    Scheduler'ni daemon thread sifatida ishga tushiradi va thread'ni qaytaradi.
    main.py'dan chaqiriladi (API thread'i kabi).
    """
    thread = threading.Thread(target=_run_scheduler_thread, daemon=True)
    thread.start()
    return thread
