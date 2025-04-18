import os
import logging

TELEGRAM_API_KEY = os.environ["TELEGRAM_API_KEY"]
MESSENGER_API_SERVICE_URL = os.environ["MESSENGER_API_SERVICE_URL"]
DATA_SERVICE_URL = os.environ["DATA_SERVICE_URL"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)