from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
import bcrypt
import uvicorn
from typing import Optional, List

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['admin_panel']
users = db['users']
settings = db['settings']  # New collection for settings

# Create indexes for username
users.create_index("username", unique=True)

# Initialize settings if they don't exist
if settings.count_documents({}) == 0:
    settings.insert_one({
        "llm_entrypoint": "http://localhost:8001",  # Default value
        "allowed_llms": [""],  # Default value
        "allowed_vlms": [""]  # Default value
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

if __name__ == "__main__":
    uvicorn.run(app, port=8000)