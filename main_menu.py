"""
handlers/main_menu.py — Botning yagona kirish nuqtasi.

Oqim: /start -> til tanlash (inline) -> "Kirish" tugmasi -> WebApp ochiladi.
Botda boshqa hech qanday funksional handler yo'q — qolgan hammasi WebApp ichida.
"""

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import LANGUAGE_UZ, LANGUAGE_RU, LANGUAGE_EN, WEBAPP_URL
from queries import get_or_create_user, update_user_language
from texts import t

# Til tanlash uchun callback_data prefiksi
LANGUAGE_CALLBACK_PREFIX = "set_lang:"


def _build_language_keyboard() -> InlineKeyboardMarkup:
    """Til tanlash uchun inline tugmalar: 🇺🇿 / 🇷🇺 / 🇬🇧."""
    buttons = [
        [
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data=f"{LANGUAGE_CALLBACK_PREFIX}{LANGUAGE_UZ}"),
        ],
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data=f"{LANGUAGE_CALLBACK_PREFIX}{LANGUAGE_RU}"),
        ],
        [
            InlineKeyboardButton("🇬🇧 English", callback_data=f"{LANGUAGE_CALLBACK_PREFIX}{LANGUAGE_EN}"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def _build_enter_webapp_keyboard(language: str) -> InlineKeyboardMarkup:
    """Til tanlangandan keyin chiqadigan "Kirish" WebApp tugmasi."""
    buttons = [
        [
            InlineKeyboardButton(
                t("enter_webapp", language),
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ]
    ]
    return InlineKeyboardMarkup(buttons)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start buyrug'i — foydalanuvchini DB'ga yozadi va til tanlashni so'raydi."""
    telegram_user = update.effective_user
    get_or_create_user(telegram_user.id, telegram_user.full_name)

    await update.message.reply_text(
        t("choose_language", LANGUAGE_UZ),
        reply_markup=_build_language_keyboard(),
    )


async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Til tanlangandan keyin DB'ga yoziladi va WebApp kirish tugmasi ko'rsatiladi."""
    query = update.callback_query
    await query.answer()

    language = query.data.removeprefix(LANGUAGE_CALLBACK_PREFIX)

    telegram_user = update.effective_user
    user = get_or_create_user(telegram_user.id, telegram_user.full_name)
    update_user_language(user["id"], language)

    await query.edit_message_text(
        t("language_changed", language),
        reply_markup=_build_enter_webapp_keyboard(language),
    )


def register_main_menu_handlers(application: Application) -> None:
    """Barcha main_menu handlerlarini botga ro'yxatdan o'tkazadi."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(
        CallbackQueryHandler(language_chosen, pattern=f"^{LANGUAGE_CALLBACK_PREFIX}")
    )
