import os

from dotenv import load_dotenv

load_dotenv()

app_api_port = int(os.environ["API_PORT"])

message_handler_host = os.environ["MESSAGE_HANDLER_HOST"]
message_handler_port = int(os.environ["MESSAGE_HANDLER_PORT"])

data_service_host = os.environ["DATA_SERVICE_HOST"]
data_service_port = int(os.environ["DATA_SERVICE_PORT"])

message_handler_url = f"http://{message_handler_host}:{message_handler_port}"
data_service_url = f"http://{data_service_host}:{data_service_port}"