"""
channel_leave_bot.py — Bot: majburiy kanaldan CHIQISH hodisasini ushlash (2026-10-14).

Telegram kanal a'zoligi o'zgarganda `chat_member` update yuboradi (bot kanalda admin
bo'lsa va polling allowed_updates'da chat_member bo'lsa — main.py). A'zo bo'lgan
foydalanuvchi "left"/"kicked" holatiga o'tsa va u liga ishtirokchisi bo'lsa —
adminlarga xabar (channel_leavers.notify_admins_about_leaver).
"""

import logging

from telegram import Update
from telegram.ext import Application, ChatMemberHandler, ContextTypes

from channel_leavers import LEFT_STATUSES, notify_admins_about_leaver
from config import REQUIRED_CHANNEL_USERNAME

logger = logging.getLogger(__name__)

_IN_CHANNEL = ("creator", "administrator", "member", "restricted")


def _is_required_channel(chat) -> bool:
    want = (REQUIRED_CHANNEL_USERNAME or "").lstrip("@").lower()
    if want.lstrip("-").isdigit():                      # env'da kanal ID berilgan bo'lsa
        return str(chat.id) == want or str(chat.id) == "-" + want.lstrip("-")
    return (chat.username or "").lower() == want


async def on_channel_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cm = update.chat_member
    if not cm or not _is_required_channel(cm.chat):
        return
    old, new = cm.old_chat_member.status, cm.new_chat_member.status
    tg_id = cm.new_chat_member.user.id
    if old in _IN_CHANNEL and new in LEFT_STATUSES:
        # 2026-10-18: klubi bosh sahifadagi "klubini topshirayotganlar" ro'yxatiga chiqadi
        try:
            from club_market import club_offer_left
            club_offer_left([tg_id], True)
        except Exception as exc:
            logger.warning("Tark etgan klubni ro'yxatga qo'yib bo'lmadi (tg=%s): %s", tg_id, exc)
        try:
            await notify_admins_about_leaver(tg_id)
        except Exception as exc:
            logger.warning("Kanaldan chiqish xabari yuborilmadi (tg=%s): %s",
                           tg_id, exc)
    elif old in LEFT_STATUSES and new in _IN_CHANNEL:
        # 2026-10-18: kanalga qaytdi — klub ro'yxatdan olinadi (agar hali hech kim olmagan bo'lsa)
        try:
            from club_market import club_offer_left
            club_offer_left([tg_id], False)
        except Exception as exc:
            logger.warning("Qaytgan ishtirokchi klubini ro'yxatdan olib bo'lmadi (tg=%s): %s", tg_id, exc)


def register_channel_leave_handler(application: Application) -> None:
    application.add_handler(ChatMemberHandler(on_channel_member, ChatMemberHandler.CHAT_MEMBER))
