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
    auto_resolve_matches,
    get_deadline_passed_matchday,
    get_leagues_needing_deadline_notice,
    set_deadline_notice_sent,
    wc_auto_resolve_all_groups,
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
    # === 1) AVTOMATIK TASDIQLASH — BARCHA qur'a o'tkazilgan ligalar uchun ===
    # MUHIM: bu blok xabar yuborishdan MUSTAQIL. Ilgari auto_resolve faqat
    # "yangi tur ochilgan" ligalar tsikli ichida chaqirilardi; oxirgi tur (38)
    # ochilib bo'lgach yangi tur ochilmaydi -> liga ro'yxatga tushmaydi ->
    # deadline o'tgan o'yinlar hech qachon avtomatik tasdiqlanmasdi.
    try:
        from queries_matchdays import get_all_drawn_leagues
        for lg in get_all_drawn_leagues():
            league_id = lg["league_id"]
            try:
                up_to = get_deadline_passed_matchday(league_id)
                if up_to >= 1:
                    resolved = auto_resolve_matches(league_id, up_to)
                    if resolved["pending_resolved"] or resolved["awaiting_resolved"]:
                        logger.info(
                            "Scheduler: '%s' ligasida avtomatik tasdiq — "
                            "pending(0:0): %d, awaiting: %d (tur %d gacha).",
                            lg["name"], resolved["pending_resolved"],
                            resolved["awaiting_resolved"], up_to,
                        )
            except Exception as exc:
                logger.warning("Scheduler: '%s' avtomatik tasdiqda xato: %s",
                               lg["name"], exc)
    except Exception as exc:
        logger.warning("Scheduler: avtomatik tasdiqlash blokida xato: %s", exc)

    # === 2) YANGI TUR OCHILDI XABARI ===
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

    # Deadline eslatmasi: har kuni 00:00-01:00 oynasida (01:00 dan 1 soat oldin)
    # ligalardagi a'zolarga "deadline yaqin" xabarini bir marta yuboramiz.
    try:
        deadline_leagues = get_leagues_needing_deadline_notice()
    except Exception as exc:
        logger.warning("Scheduler: deadline eslatma ligalarini olishda xato: %s", exc)
        deadline_leagues = []

    for lg in deadline_leagues:
        league_id = lg["league_id"]
        try:
            members = get_league_members_for_notify(league_id)
            await notify_members(members, "notify_deadline_soon", league=lg["name"])
            set_deadline_notice_sent(league_id)
            logger.info(
                "Scheduler: '%s' ligasiga deadline eslatmasi yuborildi (%d a'zo).",
                lg["name"], len(members),
            )
        except Exception as exc:
            logger.warning(
                "Scheduler: '%s' deadline eslatmasida xato: %s", lg["name"], exc
            )

    # === WORLD CUP: deadline o'tgan guruh o'yinlarini avtomatik yopish ===
    # Deadline (23:30) o'tgan, lekin o'ynalmagan WC guruh o'yinlari 0:0 durang
    # qilinadi; bir tomon kiritgani tasdiqlanadi. Liga bilan bir xil mantiq.
    try:
        wc_result = wc_auto_resolve_all_groups()
        if wc_result["total_pending"] or wc_result["total_awaiting"]:
            logger.info(
                "Scheduler: WC guruhlarida avtomatik tasdiq — 0:0 durang: %d, awaiting: %d.",
                wc_result["total_pending"], wc_result["total_awaiting"],
            )
    except Exception as exc:
        logger.warning("Scheduler: WC avtomatik yopishda xato: %s", exc)

    # === CHEMPIONLAR LIGASI: 23:30 da joriy tur yopiladi, keyingisi ochiladi ===
    # awaiting -> confirmed, pending -> 0:0 durang (variant A). Idempotent (kuniga 1 marta).
    try:
        from cl_rounds import cl_tick
        cl_res = cl_tick()
        if cl_res:
            logger.info(
                "Scheduler: ChL %d-tur yopildi (awaiting: %d, 0:0: %d) → %d-tur ochildi.",
                cl_res["closed_matchday"], cl_res["awaiting_resolved"],
                cl_res["pending_resolved"], cl_res["opened_matchday"],
            )
    except Exception as exc:
        logger.warning("Scheduler: ChL tur siljitishda xato: %s", exc)

    # === DIVIZION: 19:00 dan keyin qur'a + telegram xabar; 23:30 dan keyin yopish ===
    try:
        await _division_tick()
    except Exception as exc:
        logger.warning("Scheduler: Divizion tsiklida xato: %s", exc)


async def _division_tick() -> None:
    """
    Divizion kunlik tsikli (idempotent — div_state belgilariga tayanadi):
      - now >= 19:00 va qur'a qilinmagan bo'lsa: div_pair_day() + har ishtirokchiga
        qur'a natijasi (raqib nomi yoki avto-g'alaba) telegram orqali yuboriladi.
      - now >= 23:30 bo'lsa: div_auto_resolve_day() (0:0 durang / avto tasdiq).
    """
    from division import div_pair_day, div_auto_resolve_day
    from config import (DIV_REG_START_HOUR, DIV_REG_END_HOUR,
                        DIV_DEADLINE_HOUR, DIV_DEADLINE_MINUTE)
    from queries_leagues import _tournament_now
    from models import get_connection
    from notify import notify_user

    now = _tournament_now()

    # 0) 2026-07-16: 17:00 — BARCHA /start bosgan foydalanuvchilarga
    #    "ro'yxat ochildi" e'loni ("Kirish" WebApp tugmasi bilan).
    #    Kuniga bir marta (div_state.reg_announced_at, qoida #38).
    if DIV_REG_START_HOUR <= now.hour < DIV_REG_END_HOUR:
        from division import div_is_reg_announced, div_mark_reg_announced
        if not div_is_reg_announced():
            # Avval belgilaymiz — scheduler har tsiklda qayta yubormasin
            div_mark_reg_announced()
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT telegram_id, language FROM users "
                "WHERE telegram_id IS NOT NULL"
            )
            recipients = [dict(r) for r in cursor.fetchall()]
            conn.close()
            sent = 0
            for u in recipients:
                ok = await notify_user(u["telegram_id"], "notify_div_reg_open",
                                       u.get("language"),
                                       open_button_key="btn_open_app")
                if ok:
                    sent += 1
                # Telegram rate limit (~30 msg/s) uchun sekinlashtirish
                await asyncio.sleep(0.05)
            logger.info("Scheduler: Divizion 17:00 e'loni yuborildi: %d/%d.",
                        sent, len(recipients))

    # 1) Qur'a — ro'yxat yopilgach (19:00+)
    if now.hour >= DIV_REG_END_HOUR:
        result = div_pair_day()
        if result:
            # telegram_id -> {nickname, language} (xabar uchun bitta so'rov)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT u.telegram_id, u.nickname, u.language FROM div_registrations r "
                "JOIN users u ON u.id = r.user_id WHERE r.day = ?",
                (result["day"],),
            )
            info = {r["telegram_id"]: dict(r) for r in cursor.fetchall()}
            conn.close()

            for tg1, tg2 in result["pairs"]:
                if tg2 is None:
                    await notify_user(tg1, "notify_div_bye",
                                      info.get(tg1, {}).get("language"))
                else:
                    await notify_user(tg1, "notify_div_pair",
                                      info.get(tg1, {}).get("language"),
                                      opponent=info.get(tg2, {}).get("nickname", "?"))
                    await notify_user(tg2, "notify_div_pair",
                                      info.get(tg2, {}).get("language"),
                                      opponent=info.get(tg1, {}).get("nickname", "?"))
            logger.info("Scheduler: Divizion qur'asi yuborildi (%d o'yin).",
                        result["matches"])

    # 2) Deadline (23:30) — avtomatik yopish
    if (now.hour, now.minute) >= (DIV_DEADLINE_HOUR, DIV_DEADLINE_MINUTE):
        res = div_auto_resolve_day()
        if not res.get("already") and (res["pending"] or res["awaiting"]):
            logger.info("Scheduler: Divizion deadline — 0:0 durang: %d, tasdiq: %d.",
                        res["pending"], res["awaiting"])


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
