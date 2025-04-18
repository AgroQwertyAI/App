import os
import aiohttp
from typing import Dict, Any

# Default API URL
BERT_API_URL = os.getenv("BERT_API_URL", "http://192.168.191.96:52004")

async def classify_text(message: str) -> Dict[str, float]:
    """
    Classifies text using the BERT classification service.
    
    Args:
        message (str): The message to classify
        
    Returns:
        dict: Dictionary containing classification probabilities
    """
    url = f"{BERT_API_URL}/classify"
    payload = {"text": message}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"report": 0.0, "non-report": 1.0}
        except Exception as e:
            print(f"Error connecting to BERT classification service: {e}")
            return {"report": 0.0, "non-report": 1.0}

async def is_report_bert(message: str) -> bool:
    """
    Determines if a message is an agricultural report using BERT classification.
    
    Args:
        message (str): The message to classify
        
    Returns:
        bool: True if the message is classified as a report, False otherwise
    """
    result = await classify_text(message)
    
    print(f"Probability of report: {result.get('report', 0.0)}")
    print(f"Probability of non-report: {result.get('non-report', 1.0)}")
    
    # Consider it a report if the report probability is higher than non-report
    return result.get("report", 1.0) > result.get("non-report", 0.0)