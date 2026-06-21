"""
main.py — Bot ishga tushirish nuqtasi (entrypoint).

Ishga tushirish: python main.py
"""

import logging
import os
import threading

import uvicorn
from telegram.ext import Application

from config import BOT_TOKEN
from models import init_db
from main_menu import register_main_menu_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def run_api() -> None:
    """FastAPI serverini alohida threadda ishga tushiradi."""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. Environment variable sifatida belgilang.")

    init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    # API ni alohida threadda ishga tushirish
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    logger.info("FastAPI server ishga tushdi.")

    application = Application.builder().token(BOT_TOKEN).build()

    register_main_menu_handlers(application)

    logger.info("Bot ishga tushdi.")
    application.run_polling()


if __name__ == "__main__":
    main()
