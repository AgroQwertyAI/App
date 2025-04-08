from dotenv import load_dotenv
import os

load_dotenv()

generator_service_host = os.environ.get("GENERATOR_SERVICE_HOST")
generator_service_port = os.environ.get("GENERATOR_SERVICE_PORT")

generator_service_url = f"http://{generator_service_host}:{generator_service_port}"

api_port = int(os.environ.get("API_PORT", 8003))