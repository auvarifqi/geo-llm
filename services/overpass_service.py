"""
Overpass API Service for GeoViz3D

This module handles interactions with the Overpass API for querying OpenStreetMap data.
"""
import requests
import logging
import time
import re
from typing import Dict, Any, Optional

# Import configuration
from config.settings import (
    OVERPASS_API_URL,
    API_TIMEOUT,
    MAX_RETRIES,
    ENABLE_CACHE,
    CACHE_TTL
)

# Set up logging
logger = logging.getLogger(__name__)

# Simple in-memory cache
if ENABLE_CACHE:
    query_cache = {}

def query_overpass(query: str) -> Optional[Dict[str, Any]]:
    """
    Query the Overpass API with better error handling and caching.
    
    Args:
        query (str): The Overpass QL query
        
    Returns:
        Optional[Dict[str, Any]]: The JSON response from the API, or None if there was an error
    """
    # Check cache first if enabled
    if ENABLE_CACHE and query in query_cache:
        cache_entry = query_cache[query]
        if time.time() - cache_entry["timestamp"] < CACHE_TTL:
            logger.info("Cache hit for Overpass query")
            return cache_entry["data"]
    
    # Log the query
    logger.info(f"Querying Overpass API: {query[:100]}...")
    
    # Initialize retry counter
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            payload = {"data": query}
            response = requests.post(OVERPASS_API_URL, data=payload, timeout=API_TIMEOUT)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            # Parse the response
            data = response.json()
            
            # Cache the result if caching is enabled
            if ENABLE_CACHE:
                query_cache[query] = {
                    "data": data,
                    "timestamp": time.time()
                }
                
                # Keep cache size manageable
                if len(query_cache) > 100:  # Arbitrary limit
                    # Remove oldest entries
                    sorted_keys = sorted(query_cache.keys(), 
                                         key=lambda k: query_cache[k]["timestamp"])
                    for key in sorted_keys[:10]:  # Remove 10 oldest
                        del query_cache[key]
            
            return data
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on Overpass API request (attempt {retries+1}/{MAX_RETRIES})")
            retries += 1
            if retries < MAX_RETRIES:
                # Exponential backoff
                time.sleep(2 ** retries)
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                logger.warning(f"Rate limit hit on Overpass API (attempt {retries+1}/{MAX_RETRIES})")
                retries += 1
                if retries < MAX_RETRIES:
                    # Parse Retry-After header if available, otherwise use exponential backoff
                    retry_after = int(e.response.headers.get("Retry-After", 2 ** retries))
                    time.sleep(retry_after)
            else:
                logger.error(f"HTTP error from Overpass API: {str(e)}")
                return None
        
        except Exception as e:
            logger.error(f"Error querying Overpass API: {str(e)}")
            return None
    
    # If we've exhausted all retries
    logger.error(f"Failed to query Overpass API after {MAX_RETRIES} attempts")
    return None

def extract_overpass_query(text: str) -> Optional[str]:
    """
    Extract an Overpass query from text, such as an AI response.
    
    Args:
        text (str): The text to extract the query from
        
    Returns:
        Optional[str]: The extracted query, or None if no query was found
    """
    # Check for query in ```overpass blocks
    if "```overpass" in text and "```" in text.split("```overpass")[1]:
        return text.split("```overpass")[1].split("```")[0].strip()
    
    # Check for query in generic code blocks
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            code_block = parts[1].strip()
            
            # Check if it looks like an Overpass query (contains common Overpass syntax)
            overpass_indicators = [
                "[out:json]",
                "out body",
                "out skel",
                "node[",
                "way[",
                "relation["
            ]
            
            if any(indicator in code_block for indicator in overpass_indicators):
                return code_block
    
    # Try to find with regex as a last resort
    overpass_pattern = r'\[out:json\];.*?out skel'
    match = re.search(overpass_pattern, text, re.DOTALL)
    if match:
        return match.group(0)
    
    return None