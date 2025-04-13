import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_API_KEY = os.environ["TELEGRAM_API_KEY"]
MESSENGER_API_SERVICE_URL = os.environ["MESSENGER_API_SERVICE_URL"]