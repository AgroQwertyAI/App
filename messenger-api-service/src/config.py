import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MESSAGE_PROCESSING_SERVICE_URL = os.environ["MESSAGE_PROCESSING_SERVICE_URL"]