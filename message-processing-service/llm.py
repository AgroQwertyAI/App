import os
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional

LLM_SERVICE_URL = os.environ["LLM_SERVICE_URL"]

print("URI" + LLM_SERVICE_URL)

client = AsyncOpenAI(
    base_url=LLM_SERVICE_URL,
    api_key="nova-proxy"
)

async def chat(
    model: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    structure: Optional[Any] = None
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
        "max_tokens": 3000
    }
    
    extra_body = {}
    
    if structure:
        extra_body["json_schema"] = structure
        
    if tools:
        kwargs["tools"] = tools
    
    extra_body["reasoning_options_mode"] = "ENABLED_HIDDEN"
    
    try:
        response = await client.chat.completions.create(**kwargs, extra_body=extra_body)
        return response
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        raise