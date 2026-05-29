"""
GEVER MANAGEMENT SYSTEM
גבר יזמות ייעוץ עסקי והשקעות

Entry point - runs both the Telegram bot and FastAPI dashboard.
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_bot():
    """Run the Telegram bot."""
    from channels import GeverTelegramBot
    bot = GeverTelegramBot()
    bot.run()


def run_api():
    """Run the FastAPI dashboard server."""
    import uvicorn
    from api import app
    from config import settings
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "bot"

    if mode == "bot":
        logger.info("Starting Telegram Bot mode...")
        run_bot()
    elif mode == "api":
        logger.info("Starting API/Dashboard mode...")
        run_api()
    elif mode == "both":
        logger.info("Starting both Bot and API...")
        import threading
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        run_bot()
    else:
        print("Usage: python main.py [bot|api|both]")
