import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_SERVICE_URL = os.environ["DATA_SERVICE_URL"]

WHATSAPP_SERVICE_URL = os.environ["WHATSAPP_SERVICE_URL"]
TELEGRAM_BOT_SERVICE_URL = os.environ["TELEGRAM_BOT_SERVICE_URL"]