"""
GEVER MANAGEMENT SYSTEM
Gever Entrepreneurship Business Consulting and Investments
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_api():
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting API on port {port}")
    uvicorn.run("api:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "api"
    logger.info(f"Starting in mode: {mode}")

    if mode == "api":
        run_api()
    elif mode == "bot":
        from channels import GeverTelegramBot
        bot = GeverTelegramBot()
        bot.run()
    else:
        run_api()
