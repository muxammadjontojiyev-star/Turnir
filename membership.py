"""
membership.py — Majburiy kanal a'zoligini tekshirish.

Telegram Bot API `getChatMember` orqali foydalanuvchi REQUIRED_CHANNEL_USERNAME
kanaliga a'zo ekanini tekshiradi. Bot va API (WebApp) ikkalasi shu funksiyani
ishlatadi (markazlashtirilgan — bir joyda).

⚠️ Bot tekshiriladigan kanalda ADMIN bo'lishi SHART, aks holda getChatMember
ruxsat bermaydi.

A'zolik holatlari (status): "creator", "administrator", "member" → a'zo.
"left", "kicked", "restricted" (is_member=False) → a'zo emas.
"""

import logging

import httpx

from config import (
    BOT_TOKEN, REQUIRED_CHANNEL_USERNAME, REQUIRE_CHANNEL_MEMBERSHIP,
)

logger = logging.getLogger(__name__)

_API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# A'zo hisoblanadigan statuslar
_MEMBER_STATUSES = {"creator", "administrator", "member"}


async def is_user_subscribed(telegram_id: int) -> bool:
    """
    Foydalanuvchi majburiy kanalga a'zomi — True/False qaytaradi (async).

    REQUIRE_CHANNEL_MEMBERSHIP=False bo'lsa — har doim True (tekshiruv o'chirilgan).
    Xato bo'lsa (kanal topilmadi, bot admin emas, tarmoq) — True qaytaradi
    (foydalanuvchini bloklab qo'ymaslik uchun; xato log qilinadi).
    """
    if not REQUIRE_CHANNEL_MEMBERSHIP:
        return True
    if not BOT_TOKEN:
        return True

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{_API_BASE}/getChatMember",
                params={
                    "chat_id": REQUIRED_CHANNEL_USERNAME,
                    "user_id": telegram_id,
                },
            )
            data = r.json()
            if not data.get("ok"):
                # Bot admin emas yoki kanal topilmadi — bloklamaymiz, lekin log
                logger.warning(
                    "A'zolik tekshiruvi muvaffaqiyatsiz (user=%s): %s",
                    telegram_id, data.get("description"),
                )
                return True
            status = data.get("result", {}).get("status")
            return status in _MEMBER_STATUSES
    except Exception as exc:
        logger.warning("A'zolik tekshiruvida xato (user=%s): %s", telegram_id, exc)
        return True


def is_user_subscribed_sync(telegram_id: int) -> bool:
    """
    is_user_subscribed'ning sinxron varianti (sync bot handlerlari uchun).
    httpx.Client (sync) ishlatadi.
    """
    if not REQUIRE_CHANNEL_MEMBERSHIP:
        return True
    if not BOT_TOKEN:
        return True

    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(
                f"{_API_BASE}/getChatMember",
                params={
                    "chat_id": REQUIRED_CHANNEL_USERNAME,
                    "user_id": telegram_id,
                },
            )
            data = r.json()
            if not data.get("ok"):
                logger.warning(
                    "A'zolik tekshiruvi muvaffaqiyatsiz (user=%s): %s",
                    telegram_id, data.get("description"),
                )
                return True
            status = data.get("result", {}).get("status")
            return status in _MEMBER_STATUSES
    except Exception as exc:
        logger.warning("A'zolik tekshiruvida xato (user=%s): %s", telegram_id, exc)
        return True
