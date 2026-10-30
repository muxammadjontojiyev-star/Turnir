"""
auction_notify.py — AUKSION bot xabarlari (2026-10-30). Scheduler (daqiqada) chaqiradi: auction_send_notices().
Xabar yuborilmasa ham holat saqlanadi (bir martalik belgi auction_admin._take da) — qoida #37.
"""

import logging

from config import ADMIN_TELEGRAM_IDS

logger = logging.getLogger(__name__)
NO_BIDS = {"uz": "takliflarsiz yopildi", "ru": "закрыт без ставок", "en": "closed with no bids"}


def money(n) -> str:
    return f"{int(n or 0):,}".replace(",", " ")


async def _safe(tg, key, lang, **fmt) -> None:
    from notify import notify_user
    try:
        await notify_user(tg, key, lang, open_button_key="btn_open_app", **fmt)
    except Exception as exc:
        logger.warning("Auksion xabari (%s -> %s) yuborilmadi: %s", key, tg, exc)


async def auction_send_notices() -> int:
    """Yakunlangan lotlar (g'olib + adminlar) va yangi mavsumda klubga yozilganlar haqida xabarlar."""
    from auction_admin import auction_take_apply_notices, auction_take_end_notices
    from queries import get_user_by_telegram_id
    sent = 0
    for lot in auction_take_end_notices():
        fmt = {"club": lot["club_name"], "league": lot["league_name"]}
        if lot["telegram_id"]:
            await _safe(lot["telegram_id"], "auction_notify_won", lot["language"], amount=money(lot["current_bid"]), **fmt)
        for admin_tg in ADMIN_TELEGRAM_IDS:
            admin = get_user_by_telegram_id(admin_tg)
            lang = (admin.get("language") if admin else None) or "uz"
            who = ("@" + lot["username"]) if lot.get("username") else (lot.get("nickname") or "")
            result = f"{who}, {money(lot['current_bid'])} eF Token" if lot["telegram_id"] else NO_BIDS.get(lang, NO_BIDS["uz"])
            await _safe(admin_tg, "auction_notify_admin_end", lang, result=result, **fmt)
        sent += 1
    for lot in auction_take_apply_notices():
        if lot["telegram_id"]:
            key = "auction_notify_applied" if lot["status"] == "applied" else "auction_notify_failed"
            await _safe(lot["telegram_id"], key, lot["language"], club=lot["club_name"], league=lot["league_name"],
                        amount=money(lot["current_bid"]))
            sent += 1
    return sent
