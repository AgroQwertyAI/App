import os
import json
import requests
from typing import Optional

# Default to localhost:3000 if not specified
FILE_SERVICE_URL = os.environ.get('FILE_SERVICE_URL', 'http://localhost:3000')

def log(message: str, level: Optional[str] = 'info', source: Optional[str] = 'app') -> dict:
    """
    Send a log message to the file service.
    
    Args:
        message: The log message to be recorded
        level: Log level (default: 'info') - e.g., 'info', 'warn', 'error'
        source: The source of the log (default: 'app')
        
    Returns:
        The response from the server as a dictionary
        
    Raises:
        Exception: If the request fails or returns a non-200 status code
    """
    if not message:
        raise ValueError("Message cannot be empty")
        
    url = f"{FILE_SERVICE_URL}/api/logs/submit"
    
    payload = {
        "message": message,
        "level": level,
        "source": source
    }
    
    try:
        response = requests.post(
            url, 
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Raise an exception if the request failed
        response.raise_for_status()
        
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending log: {e}")
        raise Exception(f"Failed to send log: {e}")