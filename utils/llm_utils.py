"""
LLM Utility Functions for GeoViz3D

This module contains utility functions for working with LLMs.
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

def extract_code_blocks(text: str) -> List[Tuple[Optional[str], str]]:
    """
    Extract code blocks from a text string.
    
    Args:
        text (str): Text containing code blocks
        
    Returns:
        List[Tuple[Optional[str], str]]: List of (language, code) tuples
    """
    # Regular expression to match code blocks
    pattern = r'```([\w]*)\n(.*?)```'
    
    # Find all matches
    matches = re.findall(pattern, text, re.DOTALL)
    
    # Process matches
    code_blocks = []
    for lang, code in matches:
        # Check if language was specified
        language = lang.strip() if lang.strip() else None
        
        # Add to list
        code_blocks.append((language, code.strip()))
    
    return code_blocks

def format_message_for_display(message: Dict[str, Any]) -> str:
    """
    Format a message for display in the UI.
    
    Args:
        message (Dict[str, Any]): Message dictionary with 'role' and 'content'
        
    Returns:
        str: Formatted message
    """
    role = message.get("role", "unknown")
    content = message.get("content", "")
    
    if role == "user":
        return f"User: {content}"
    elif role == "assistant":
        return f"Assistant: {content}"
    elif role == "system":
        return f"System: {content}"
    else:
        return f"{role.capitalize()}: {content}"

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count the number of tokens in a text string.
    
    This is a simple approximation as true tokenization depends on the model.
    
    Args:
        text (str): Text to count tokens for
        model (str, optional): Model to count tokens for. Defaults to "gpt-4".
        
    Returns:
        int: Approximate token count
    """
    # Simple approximation based on word count
    # On average, 1 token is about 4 characters for English text
    return len(text) // 4 + 1

def truncate_chat_history(
    chat_history: List[Dict[str, Any]], 
    max_tokens: int = 3000
) -> List[Dict[str, Any]]:
    """
    Truncate chat history to fit within token limits.
    
    Args:
        chat_history (List[Dict[str, Any]]): Chat history
        max_tokens (int, optional): Maximum number of tokens. Defaults to 3000.
        
    Returns:
        List[Dict[str, Any]]: Truncated chat history
    """
    # Estimate total tokens
    total_tokens = sum(count_tokens(message.get("content", "")) for message in chat_history)
    
    # If within limit, return as is
    if total_tokens <= max_tokens:
        return chat_history
    
    # Otherwise, truncate from the beginning
    truncated_history = []
    current_tokens = 0
    
    # Start from the end and work backwards
    for message in reversed(chat_history):
        message_tokens = count_tokens(message.get("content", ""))
        
        if current_tokens + message_tokens <= max_tokens:
            truncated_history.insert(0, message)
            current_tokens += message_tokens
        else:
            # We've reached the limit
            break
    
    logger.info(f"Truncated chat history from {len(chat_history)} to {len(truncated_history)} messages")
    return truncated_history

def format_prompt_with_variables(prompt: str, variables: Dict[str, Any]) -> str:
    """
    Format a prompt template with variables.
    
    Args:
        prompt (str): Prompt template
        variables (Dict[str, Any]): Variables to fill in
        
    Returns:
        str: Formatted prompt
    """
    try:
        return prompt.format(**variables)
    except KeyError as e:
        logger.error(f"Missing variable in prompt template: {e}")
        # Return the original template with a warning
        return f"{prompt}\n\n[Warning: Missing variable {e}]"
    except Exception as e:
        logger.error(f"Error formatting prompt: {e}")
        return prompt

def build_system_prompt(
    base_prompt: str,
    context: Optional[str] = None,
    instructions: Optional[str] = None
) -> str:
    """
    Build a system prompt with optional context and instructions.
    
    Args:
        base_prompt (str): Base system prompt
        context (Optional[str], optional): Additional context. Defaults to None.
        instructions (Optional[str], optional): Additional instructions. Defaults to None.
        
    Returns:
        str: Full system prompt
    """
    prompt_parts = [base_prompt]
    
    if context:
        prompt_parts.append("\nCONTEXT:")
        prompt_parts.append(context)
    
    if instructions:
        prompt_parts.append("\nADDITIONAL INSTRUCTIONS:")
        prompt_parts.append(instructions)
    
    return "\n".join(prompt_parts)