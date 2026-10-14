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
    if old in _IN_CHANNEL and new in LEFT_STATUSES:
        try:
            await notify_admins_about_leaver(cm.new_chat_member.user.id)
        except Exception as exc:
            logger.warning("Kanaldan chiqish xabari yuborilmadi (tg=%s): %s",
                           cm.new_chat_member.user.id, exc)


def register_channel_leave_handler(application: Application) -> None:
    application.add_handler(ChatMemberHandler(on_channel_member, ChatMemberHandler.CHAT_MEMBER))
