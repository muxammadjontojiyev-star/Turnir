"""
handlers/main_menu.py — Botning yagona kirish nuqtasi.

Oqim: /start -> til tanlash (inline) -> "Kirish" tugmasi -> WebApp ochiladi.
Botda boshqa hech qanday funksional handler yo'q — qolgan hammasi WebApp ichida.
2026-10-08: /stats — faqat bosh admin uchun bot statistikasi (stats.py).
2026-10-25: /help, /qollanma — qo'llanma (WebApp ?guide=list); «Kirish» xabarida ham «📖 Qo'llanma» tugmasi.
"""

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import (
    LANGUAGE_UZ, LANGUAGE_RU, LANGUAGE_EN, WEBAPP_URL,
    REQUIRED_CHANNEL_URL,
)
from queries import get_or_create_user, update_user_language
from texts import t
from membership import is_user_subscribed_sync

# Til tanlash uchun callback_data prefiksi
LANGUAGE_CALLBACK_PREFIX = "set_lang:"
# A'zolikni qayta tekshirish tugmasi uchun callback_data prefiksi (til bilan)
CHECK_SUB_CALLBACK_PREFIX = "check_sub:"


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
    """Til tanlangandan keyin chiqadigan "Kirish" WebApp tugmasi (+ 2026-10-25: qo'llanma)."""
    buttons = [
        [
            InlineKeyboardButton(
                t("enter_webapp", language),
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ],
        [_guide_button(language)],
    ]
    return InlineKeyboardMarkup(buttons)


# 2026-10-25: qo'llanma — WebApp ?guide=list (bo'limlar ro'yxati), static/guide.js
GUIDE_URL_PARAM = "guide"
GUIDE_URL_LIST = "list"


def _guide_button(language: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(t("guide_button", language),
                                web_app=WebAppInfo(url=_webapp_url_with(GUIDE_URL_PARAM, GUIDE_URL_LIST)))


def _build_subscribe_keyboard(language: str) -> InlineKeyboardMarkup:
    """A'zo bo'lmaganlar uchun: kanal tugmasi + "Tekshirish" tugmasi."""
    buttons = [
        [InlineKeyboardButton(t("subscribe_button", language), url=REQUIRED_CHANNEL_URL)],
        [InlineKeyboardButton(
            t("subscribe_check_button", language),
            callback_data=f"{CHECK_SUB_CALLBACK_PREFIX}{language}",
        )],
    ]
    return InlineKeyboardMarkup(buttons)


async def _show_gate_or_enter(query, telegram_id: int, language: str) -> None:
    """
    A'zolikka qarab xabarni yangilaydi:
    - a'zo bo'lsa → "Kirish" WebApp tugmasi,
    - a'zo bo'lmasa → "Kanalga a'zo bo'ling" + "Tekshirish" tugmasi.
    """
    if is_user_subscribed_sync(telegram_id):
        await query.edit_message_text(
            t("language_changed", language),
            reply_markup=_build_enter_webapp_keyboard(language),
        )
    else:
        await query.edit_message_text(
            t("subscribe_required", language),
            reply_markup=_build_subscribe_keyboard(language),
        )


def _webapp_url_with(param: str, value: str) -> str:
    """WEBAPP_URL ga so'rov parametri qo'shadi (URL'da allaqachon '?' bo'lishi mumkin)."""
    sep = "&" if "?" in WEBAPP_URL else "?"
    return f"{WEBAPP_URL}{sep}{param}={value}"


async def _send_pt_invite(update: Update, user: dict, code: str) -> None:
    """
    2026-10-02: shaxsiy turnir taklif havolasi (/start pt_<kod>).
    Turnir nomi + WebApp tugmasi (ilova qo'shilish ekranida ochiladi: ?pt_join=<kod>).
    Kanal a'zoligini WebApp o'zi tekshiradi (mavjud gate).
    """
    from pt_members import pt_invite_preview
    lang = user.get("language") or LANGUAGE_UZ
    preview = pt_invite_preview(code)
    if preview is None:
        await update.message.reply_text(t("pt_invite_invalid", lang))
        return
    owner = "@" + preview["owner_username"] if preview.get("owner_username") else (preview.get("owner_nickname") or "")
    text = t("pt_invite_message", lang).format(name=preview["name"], owner=owner)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
        t("pt_invite_button", lang), web_app=WebAppInfo(url=_webapp_url_with("pt_join", code)))]])
    await update.message.reply_text(text, reply_markup=keyboard)


async def _send_tb_invite(update: Update, user: dict, code: str) -> None:
    """2026-10-15: Teamlar jangi taklif havolasi (/start tb_<kod>) — team nomi + WebApp tugmasi (?tb_join=<kod>)."""
    from tb_core import tb_invite_preview
    lang = user.get("language") or LANGUAGE_UZ
    preview = tb_invite_preview(code)
    if preview is None:
        await update.message.reply_text(t("tb_invite_invalid", lang))
        return
    captain = "@" + preview["captain_username"] if preview.get("captain_username") else (preview.get("captain_nickname") or "")
    text = t("tb_invite_message", lang).format(name=preview["name"], captain=captain)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
        t("tb_invite_button", lang), web_app=WebAppInfo(url=_webapp_url_with("tb_join", code)))]])
    await update.message.reply_text(text, reply_markup=keyboard)


async def _send_tb_league_invite(update: Update, user: dict, code: str) -> None:
    """2026-10-16: Teamlar jangi LIGA havolasi (/start tbl_<kod>) — liga nomi + WebApp tugmasi (?tbl_join=<kod>)."""
    from tb_leagues import tb_league_by_code
    lang = user.get("language") or LANGUAGE_UZ
    league = tb_league_by_code(code)
    if league is None:
        await update.message.reply_text(t("tb_league_invite_invalid", lang))
        return
    text = t("tb_league_invite_message", lang).format(name=league["name"], emoji=league.get("emoji") or "")
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
        t("tb_league_invite_button", lang), web_app=WebAppInfo(url=_webapp_url_with("tbl_join", code)))]])
    await update.message.reply_text(text, reply_markup=keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start buyrug'i — foydalanuvchini DB'ga yozadi va til tanlashni so'raydi.
    2026-10-02: '/start pt_<kod>' — shaxsiy turnir taklifi (til tanlash o'tkazib yuboriladi)."""
    telegram_user = update.effective_user
    user = get_or_create_user(telegram_user.id, telegram_user.full_name)

    from pt_members import parse_invite_payload
    code = parse_invite_payload(context.args[0] if context.args else None)
    if code:
        await _send_pt_invite(update, user, code)
        return

    # 2026-10-15: '/start tb_<kod>' — Teamlar jangi taklifi
    from tb_core import parse_tb_invite_payload
    tb_code = parse_tb_invite_payload(context.args[0] if context.args else None)
    if tb_code:
        await _send_tb_invite(update, user, tb_code)
        return

    # 2026-10-16: '/start tbl_<kod>' — Teamlar jangi liga havolasi
    from tb_leagues import parse_tb_league_payload
    tbl_code = parse_tb_league_payload(context.args[0] if context.args else None)
    if tbl_code:
        await _send_tb_league_invite(update, user, tbl_code)
        return

    await update.message.reply_text(
        t("choose_language", LANGUAGE_UZ),
        reply_markup=_build_language_keyboard(),
    )


async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Til tanlangandan keyin DB'ga yoziladi va a'zolikka qarab tugma ko'rsatiladi."""
    query = update.callback_query
    await query.answer()

    language = query.data.removeprefix(LANGUAGE_CALLBACK_PREFIX)

    telegram_user = update.effective_user
    user = get_or_create_user(telegram_user.id, telegram_user.full_name)
    update_user_language(user["id"], language)

    await _show_gate_or_enter(query, telegram_user.id, language)


async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """"Tekshirish" tugmasi — a'zolikni qayta tekshiradi."""
    query = update.callback_query
    language = query.data.removeprefix(CHECK_SUB_CALLBACK_PREFIX)
    telegram_user = update.effective_user

    if is_user_subscribed_sync(telegram_user.id):
        await query.answer()
        await _show_gate_or_enter(query, telegram_user.id, language)
    else:
        # Hali a'zo emas — qalqib chiquvchi ogohlantirish (xabar o'zgarmaydi)
        await query.answer(t("subscribe_not_yet", language), show_alert=True)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/stats — bosh adminga bot statistikasi; boshqalarga javob berilmaydi (buyruq borligi oshkor qilinmaydi)."""
    from admin_roles import is_super_admin
    from stats import format_stats_text, get_bot_stats
    tg_user = update.effective_user
    if not tg_user or not is_super_admin(tg_user.id):
        return
    user = get_or_create_user(tg_user.id, tg_user.full_name)
    await update.effective_message.reply_text(format_stats_text(get_bot_stats(), user.get("language")))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """2026-10-25: /help va /qollanma — qisqa tushuntirish + qo'llanmani ochuvchi tugma."""
    tg_user = update.effective_user
    if not tg_user or not update.effective_message:
        return
    user = get_or_create_user(tg_user.id, tg_user.full_name)
    lang = user.get("language") or LANGUAGE_UZ
    await update.effective_message.reply_text(t("guide_message", lang),
                                              reply_markup=InlineKeyboardMarkup([[_guide_button(lang)]]))


def register_main_menu_handlers(application: Application) -> None:
    """Barcha main_menu handlerlarini botga ro'yxatdan o'tkazadi."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler(["help", "qollanma"], help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(
        CallbackQueryHandler(language_chosen, pattern=f"^{LANGUAGE_CALLBACK_PREFIX}")
    )
    application.add_handler(
        CallbackQueryHandler(check_subscription, pattern=f"^{CHECK_SUB_CALLBACK_PREFIX}")
    )
