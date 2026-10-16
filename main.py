import os
import logging
from dotenv import load_dotenv
from src.utils.logger import setup_logger
from src.bot.engine import MasterTradingEngine
from src.utils.telegram_bot import TelegramController

load_dotenv()

if __name__ == "__main__":
    setup_logger()
    logging.info("==================================================")
    logging.info("🚀 Khtb Institutional Command Center v3.5 Initialized")
    logging.info("==================================================")

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    auto_mode = os.getenv("AUTO_MODE", "False").lower() == "true"
    is_demo = os.getenv("IS_DEMO_MODE", "True").lower() == "true"

    engine = MasterTradingEngine(is_demo=is_demo, auto_mode=auto_mode)
    
    if token and chat_id:
        bot = TelegramController(token=token, owner_chat_id=chat_id, engine=engine)
        bot.run()
    else:
        logging.warning("⚠️ Telegram credentials missing. Running engine standalone.")
        while True:
            import time
            time.sleep(30)
