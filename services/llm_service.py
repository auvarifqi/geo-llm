"""
LLM Service for GeoViz3D

This module handles interactions with the OpenAI LLM API for processing user queries
and generating Overpass queries.
"""
from openai import OpenAI


import logging
from typing import List, Dict, Any, Optional

# Import configuration
from config.settings import (
    OPENAI_API_KEY,
    DEFAULT_LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS
)
client = OpenAI(api_key=OPENAI_API_KEY)
# Import prompts
from prompts.system_prompts import SYSTEM_PROMPT

# Set up logging
logger = logging.getLogger(__name__)

# Set the OpenAI API key

def process_user_query(
    query: str, 
    chat_history: List[Dict[str, str]],
    model: str = DEFAULT_LLM_MODEL
) -> Optional[str]:
    """
    Process a user query using the OpenAI LLM API.
    
    Args:
        query (str): The user's query
        chat_history (List[Dict[str, str]]): The chat history
        model (str, optional): The LLM model to use. Defaults to DEFAULT_LLM_MODEL.
        
    Returns:
        Optional[str]: The LLM's response, or None if there was an error
    """
    try:
        # Create messages for OpenAI
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # Add chat history (limit to last 10 exchanges to save tokens)
        history_to_include = chat_history[-10:] if len(chat_history) > 10 else chat_history
        for message in history_to_include:
            messages.append({"role": message["role"], "content": message["content"]})

        # Query OpenAI
        response = client.chat.completions.create(model=model,
        messages=messages,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0)

        # Extract and return the response content
        if response.choices and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            logger.warning("Empty response from OpenAI API")
            return None

    except Exception as e:
        logger.error(f"Error querying OpenAI API: {str(e)}")
        return f"I encountered an error while processing your query. Please try again later. Error details: {str(e)}"

def generate_system_message(
    user_query: str,
    special_context: Optional[str] = None
) -> str:
    """
    Generate a system message for the OpenAI API, optionally with special context.
    
    Args:
        user_query (str): The user's query
        special_context (Optional[str], optional): Special context to add to the system message. 
            Defaults to None.
            
    Returns:
        str: The system message
    """
    system_message = SYSTEM_PROMPT

    # Add special context if provided
    if special_context:
        system_message += f"\n\nAdditional context for this query: {special_context}"

    return system_message

def extract_geographical_context(text: str) -> Dict[str, Any]:
    """
    Extract geographical context from a text, such as location names, coordinates, etc.
    
    This function can be expanded to use more sophisticated NLP techniques or
    specialized APIs for extracting geographical entities.
    
    Args:
        text (str): The text to extract context from
        
    Returns:
        Dict[str, Any]: A dictionary containing the extracted context
    """
    # This is a placeholder implementation
    # In a real implementation, you would use NLP or other techniques to extract
    # geographical entities like place names, coordinates, etc.

    context = {
        "extracted_locations": [],
        "has_geographical_content": False
    }

    # Simple keyword detection
    geographical_keywords = [
        "map", "location", "city", "country", "place", "where", "near",
        "building", "road", "street", "avenue", "town", "village", "park",
        "mountain", "river", "lake", "ocean", "sea", "forest", "desert",
        "north", "south", "east", "west", "latitude", "longitude", "coordinates"
    ]

    for keyword in geographical_keywords:
        if keyword.lower() in text.lower():
            context["has_geographical_content"] = True
            break

    return context