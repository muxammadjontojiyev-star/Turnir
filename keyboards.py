"""
keyboards.py — Pastki asosiy tugmalar (reply keyboard).

4 ta asosiy tugma: Asosiy, Reyting, Profil, Sovrinlar.
Matnlar texts.py dan olinadi (hardcode qilinmaydi).
"""

from telegram import ReplyKeyboardMarkup, KeyboardButton
from bot.texts import t


def get_main_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Pastki asosiy 4 ta tugmani qaytaradi: Asosiy, Reyting, Profil, Sovrinlar.
    Tugma matnlari foydalanuvchi tiliga mos tarjima qilinadi.
    """
    keyboard = [
        [KeyboardButton(t("menu_main", language)), KeyboardButton(t("menu_rating", language))],
        [KeyboardButton(t("menu_profile", language)), KeyboardButton(t("menu_prizes", language))],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
