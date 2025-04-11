import http.client
import json

import uuid

conn = http.client.HTTPConnection("localhost", 8001)

long_message = """Пахота зяби под сою 
По ПУ 7/1402
Отд 17 7/141

Вырав-ие зяби под кук/силос
По ПУ 16/16
Отд 12 16/16

Вырав-ие зяби под сах/свёклу
По ПУ 67/912
Отд 12 67/376

2-ое диск-ие сах/свёкла 
По ПУ 59/1041
Отд 17 59/349"""

payload = {
    "message_id": str(uuid.uuid4()),
    "source_name": "whatsapp",
    "chat_id": "120363416114039646@g.us",
    "text": long_message,
    "sender_name": "Test User",
    "sender_id": "user_123"
}

headers = {"Content-Type": "application/json"}
conn.request("POST", "/new_message", body=json.dumps(payload), headers=headers)

response = conn.getresponse()
print(f"Status Code: {response.status}")
print("Response:")
print(response.read().decode())
conn.close()