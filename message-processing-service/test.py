import pandas as pd
import uuid
import requests

# Configuration
CSV_PATH = 'prompts.csv'
ENDPOINT = 'http://localhost:8001/new_message'
CHAT_ID = '120363416114039646@g.us'
SOURCE_NAME = 'whatsapp'
SENDER_NAME = 'Test User'
SENDER_ID = 'user_123'

def load_prompts(csv_path: str) -> pd.Series:
    """
    Load the CSV and return a Series of non-null prompts.
    """
    # If the file has a header, pandas will pick it up; otherwise it'll treat the first row as data.
    df = pd.read_csv(csv_path, header=0, dtype=str, encoding='utf-8')
    # Assume the first (and only) column holds the prompts:
    prompts = df.iloc[:, 0].dropna().astype(str)
    return prompts

def make_message_payload(prompt: str) -> dict:
    """
    Construct the JSON payload for one prompt.
    """
    message_id = 'msg_' + uuid.uuid4().hex
    return {
        "message_id": message_id,
        "source_name": SOURCE_NAME,
        "chat_id": CHAT_ID,
        "text": prompt,
        "sender_name": SENDER_NAME,
        "sender_id": SENDER_ID
    }

def send_prompt(prompt: str) -> requests.Response:
    """
    Send a single prompt to the endpoint.
    """
    payload = make_message_payload(prompt)
    resp = requests.post(ENDPOINT, json=payload)
    resp.raise_for_status()
    return resp

def main():
    prompts = load_prompts(CSV_PATH)
    for i, prompt in enumerate(prompts, 1):
        try:
            resp = send_prompt(prompt)
            print(f"[{i}/{len(prompts)}] Sent prompt (ID={resp.json().get('message_id', 'unknown')}), status {resp.status_code}")
        except Exception as e:
            print(f"[{i}/{len(prompts)}] Failed to send prompt: {e!r}")

if __name__ == "__main__":
    main()
