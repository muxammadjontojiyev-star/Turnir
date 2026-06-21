"""
main.py — Bot ishga tushirish nuqtasi (entrypoint).

Ishga tushirish: python main.py
"""

import logging

from telegram.ext import Application

from config import BOT_TOKEN
from models import init_db
from main_menu import register_main_menu_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. Environment variable sifatida belgilang.")

    init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    application = Application.builder().token(BOT_TOKEN).build()

    register_main_menu_handlers(application)

    logger.info("Bot ishga tushdi.")
    application.run_polling()


if __name__ == "__main__":
    main()
