import sqlite3
import os
from src.auxiliary import log_info

DB_PATH = "user_phone_numbers.db"

def initialize_db():
    """Create the SQLite database and tables if they don't exist"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create the phone_numbers table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS phone_numbers (
            chat_id TEXT PRIMARY KEY,
            phone_number TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        log_info("Phone number database initialized", 'info')
    except Exception as e:
        log_info(f"Error initializing database: {str(e)}", 'error')
        raise e

def save_phone_number(chat_id: str, phone_number: str):
    """Save or update a user's phone number in the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert or replace the phone number for the chat_id
        cursor.execute('''
        INSERT OR REPLACE INTO phone_numbers (chat_id, phone_number)
        VALUES (?, ?)
        ''', (chat_id, phone_number))
        
        conn.commit()
        conn.close()
        log_info(f"Phone number saved for chat_id {chat_id}", 'info')
        return True
    except Exception as e:
        log_info(f"Error saving phone number: {str(e)}", 'error')
        return False

def get_phone_number(chat_id: str) -> str | None:
    """Retrieve a phone number for a given chat_id"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT phone_number FROM phone_numbers WHERE chat_id = ?', (chat_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        log_info(f"Error retrieving phone number: {str(e)}", 'error')
        return None

def get_chat_id_by_phone_number(phone_number: str) -> str | None:
    """Retrieve a chat_id for a given phone number"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT chat_id FROM phone_numbers WHERE phone_number = ?', (phone_number,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        log_info(f"Error retrieving chat ID: {str(e)}", 'error')
        return None

def get_mapping() -> dict | None:
    """Retrieve all chat_id to phone_number mappings from the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT chat_id, phone_number, created_at FROM phone_numbers')
        results = cursor.fetchall()
        
        conn.close()
        
        if results:
            mapping = [
                    {
                        "chat_id": row[0],
                        "phone_number": row[1],
                        "created_at": row[2]
                    } for row in results
                ]
            
            return mapping
        return []
    except Exception as e:
        log_info(f"Error retrieving mappings: {str(e)}", 'error')
        return None 