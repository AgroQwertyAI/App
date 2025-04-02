from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
import bcrypt
import uvicorn
import requests
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
import datetime

# Load environment variables
load_dotenv()

# Data sources config
def get_data_sources_config():
    """Get data sources configuration from environment variables"""
    data_source_names = os.getenv("DATA_SOURCES_NAMES", "").split(",")
    data_sources = {}
    
    for name in data_source_names:
        name = name.strip()
        if name:
            url = os.getenv(f"DATA_SOURCE_{name}", "")
            if url:
                data_sources[name] = url
    
    return data_sources

# Load data sources configuration
data_sources_config = get_data_sources_config()

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['admin_panel']
users = db['users']
settings = db['settings']  # Settings collection
telegram_chats = db['telegram_chats']  # Collection for telegram chats
telegram_api_keys = db['telegram_api_keys']  # Collection for telegram API keys
processed_messages = db['processed_messages']  # Collection for processed messages

# Create indexes
users.create_index("username", unique=True)
telegram_chats.create_index([("source_name", 1), ("chat_id", 1)], unique=True)
telegram_api_keys.create_index("source_name", unique=True)
processed_messages.create_index([("chat_id", 1), ("source_name", 1)])

# Initialize settings if they don't exist
if settings.count_documents({}) == 0:
    settings.insert_one({
        "llm_entrypoint": "http://localhost:8001",
        "allowed_llms": [""],
        "allowed_vlms": [""]
    })

app = FastAPI()

# Disable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request validation
class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    role: str = "user"

class UserLogin(BaseModel):
    username: str
    password: str

class LLMEntrypoint(BaseModel):
    url: str

class AllowedLLMs(BaseModel):
    models: List[str]

class AllowedVLMs(BaseModel):
    models: List[str]
    
class TelegramChatModel(BaseModel):
    source_name: str
    chat_id: str
    chat_name: str = ""

class TelegramApiKeyModel(BaseModel):
    source_name: str
    api_key: str
    
class TelegramApiKeyModel(BaseModel):
    source_name: str
    api_key: str

class MessageData(BaseModel):
    sender: str
    text: str
    type: str
    data: Dict[str, Any]

class ProcessedMessageSubmit(BaseModel):
    chat_id: str
    source_name: str
    message: MessageData
    
class ActiveChatsModel(BaseModel):
    source_name: str
    chat_ids: List[str]

# FRONTEND AUTH API

@app.post("/create_user")
async def create_user(user: UserCreate):
    """Create a new user in the database"""
    try:
        # Check if user already exists
        if users.find_one({"username": user.username}):
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Hash password
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user with role
        user_id = users.insert_one({
            "name": user.name,
            "username": user.username,
            "password": hashed_password,
            "role": user.role
        }).inserted_id
        
        return {
            "id": str(user_id), 
            "username": user.username, 
            "name": user.name, 
            "role": user.role
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/authorize")
async def authorize(login: UserLogin):
    """Validate user credentials"""
    try:
        # Find user
        user = users.find_one({"username": login.username})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Check password
        if bcrypt.checkpw(login.password.encode('utf-8'), user['password']):
            return {
                "id": str(user['_id']),
                "name": user['name'],
                "username": user['username'],
                "role": user['role']
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# LLM SELECTION API

@app.post("/set_llm_entrypoint")
async def set_llm_entrypoint(entrypoint: LLMEntrypoint):
    """Set the LLM API entrypoint URL"""
    try:
        settings.update_one({}, {"$set": {"llm_entrypoint": entrypoint.url}}, upsert=True)
        return {"status": "success", "llm_entrypoint": entrypoint.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_llm_entrypoint")
async def get_llm_entrypoint():
    """Get the LLM API entrypoint URL"""
    try:
        setting = settings.find_one({})
        if not setting or "llm_entrypoint" not in setting:
            raise HTTPException(status_code=404, detail="LLM entrypoint not found")
        return {"llm_entrypoint": setting["llm_entrypoint"]}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set_allowed_llms")
async def set_allowed_llms(models: AllowedLLMs):
    """Set the list of allowed LLM models"""
    try:
        settings.update_one({}, {"$set": {"allowed_llms": models.models}}, upsert=True)
        return {"status": "success", "allowed_llms": models.models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_allowed_llms")
async def get_allowed_llms():
    """Get the list of allowed LLM models"""
    try:
        setting = settings.find_one({})
        if not setting or "allowed_llms" not in setting:
            raise HTTPException(status_code=404, detail="Allowed LLMs not found")
        return {"allowed_llms": setting["allowed_llms"]}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set_allowed_vlms")
async def set_allowed_vlms(models: AllowedVLMs):
    """Set the list of allowed VLM models"""
    try:
        settings.update_one({}, {"$set": {"allowed_vlms": models.models}}, upsert=True)
        return {"status": "success", "allowed_vlms": models.models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_allowed_vlms")
async def get_allowed_vlms():
    """Get the list of allowed VLM models"""
    try:
        setting = settings.find_one({})
        if not setting or "allowed_vlms" not in setting:
            raise HTTPException(status_code=404, detail="Allowed VLMs not found")
        return {"allowed_vlms": setting["allowed_vlms"]}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# MESSAGES SOURCE API

@app.get("/get_active_chats/{source_name}")
async def get_active_chats(source_name: str):
    """Get list of active chats for a specific source"""
    try:
        chats = list(telegram_chats.find({"source_name": source_name}, {"_id": 0, "chat_id": 1}))
        return {"chats": [chat["chat_id"] for chat in chats]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_telegram_api_key/{source_name}")
async def get_telegram_api_key(source_name: str):
    """Get Telegram API key for a specific source"""
    try:
        api_key = telegram_api_keys.find_one({"source_name": source_name})
        if not api_key:
            raise HTTPException(status_code=404, detail=f"API key for {source_name} not found")
        return {"api_key": api_key["api_key"]}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_chat")
async def add_chat(chat: TelegramChatModel):
    """Add a chat to the list of active chats"""
    try:
        result = telegram_chats.update_one(
            {"source_name": chat.source_name, "chat_id": chat.chat_id},
            {"$set": {"chat_name": chat.chat_name}},
            upsert=True
        )
        return {"status": "success", "chat_id": chat.chat_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/remove_chat")
async def remove_chat(chat: TelegramChatModel):
    """Remove a chat from the list of active chats"""
    try:
        result = telegram_chats.delete_one({"source_name": chat.source_name, "chat_id": chat.chat_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"status": "success", "chat_id": chat.chat_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set_telegram_api_key")
async def set_telegram_api_key(api_key_data: TelegramApiKeyModel):
    """Set Telegram API key for a specific source"""
    try:
        telegram_api_keys.update_one(
            {"source_name": api_key_data.source_name},
            {"$set": {"api_key": api_key_data.api_key}},
            upsert=True
        )
        return {"status": "success", "source_name": api_key_data.source_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update_all")
async def update_all():
    """Call update endpoint on all data source services"""
    try:
        results = []
        
        for source_name, source_url in data_sources_config.items():
            try:
                response = requests.post(f"{source_url}/update")
                results.append({
                    "source": source_name,
                    "url": source_url,
                    "status": "success" if response.ok else "error",
                    "details": response.json() if response.ok else response.text
                })
            except Exception as e:
                results.append({
                    "source": source_name,
                    "url": source_url,
                    "status": "error",
                    "details": str(e)
                })
                
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CHAT SETTINGS API

@app.get("/get_datasources")
async def get_datasources():
    """Returns a list of available data source names"""
    try:
        return {"datasources": list(data_sources_config.keys())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_chats/{source_name}")
async def get_chats(source_name: str):
    """Returns all chats (IDs and names) for a specific data source"""
    try:
        # Check if source exists
        if source_name not in data_sources_config:
            raise HTTPException(status_code=404, detail=f"Data source '{source_name}' not found")
        
        # Find all chats for this source
        chats = list(telegram_chats.find(
            {"source_name": source_name}, 
            {"_id": 0, "chat_id": 1, "chat_name": 1}
        ))
        return {"chats": chats}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set_active_chats")
async def set_active_chats(active_chats: ActiveChatsModel):
    """Set which chat IDs are active for a given source"""
    try:
        source_name = active_chats.source_name
        
        # Check if source exists
        if source_name not in data_sources_config:
            raise HTTPException(status_code=404, detail=f"Data source '{source_name}' not found")
        
        # First, deactivate all chats for this source by removing them
        telegram_chats.delete_many({"source_name": source_name})
        
        # Then add all active chats
        for chat_id in active_chats.chat_ids:
            # We're storing with empty chat_name - it can be updated later with actual names
            telegram_chats.insert_one({
                "source_name": source_name,
                "chat_id": chat_id,
                "chat_name": ""
            })
        
        return {"status": "success", "active_chats_count": len(active_chats.chat_ids)}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# MESSAGES API

@app.post("/submit_processed_message")
async def submit_processed_message(message_data: ProcessedMessageSubmit):
    """Submit a processed message to the database"""
    try:
        # Insert message with chat_id and source_name as identifiers
        result = processed_messages.insert_one({
            "chat_id": message_data.chat_id,
            "source_name": message_data.source_name,
            "sender": message_data.message.sender,
            "text": message_data.message.text,
            "type": message_data.message.type,
            "data": message_data.message.data,
            "timestamp": datetime.datetime.now()
        })
        
        return {
            "status": "success", 
            "message_id": str(result.inserted_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_processed_messages/{chat_id}")
async def get_processed_messages(chat_id: str):
    """Get all processed messages for a specific chat_id"""
    try:
        # Query messages for the given chat_id
        messages = list(processed_messages.find(
            {"chat_id": chat_id},
            {"_id": 0, "chat_id":1, "source_name":1, "sender": 1, "text": 1, "type": 1, "data": 1}
        ).sort("timestamp", 1))
        
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)