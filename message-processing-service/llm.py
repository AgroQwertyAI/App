import os
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional

LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "http://37.194.195.213:6325/v1")

client = AsyncOpenAI(
    base_url=LLM_SERVICE_URL,
    api_key="nova-proxy"
)

async def chat(
    model: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Asynchronously call the LLM API with the given parameters.
    
    Args:
        model: The model name to use
        messages: Array of message objects with role and content
        tools: Optional list of tools for function calling capability
    
    Returns:
        The API response as a dictionary
    """
    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": 8192
    }
    
    if tools:
        kwargs["tools"] = tools
    
    try:
        response = await client.chat.completions.create(**kwargs)
        print(response)
        return response
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        raise