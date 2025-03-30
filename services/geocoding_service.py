"""
Geocoding Service for GeoViz3D

This module handles geocoding operations (converting place names to coordinates).
"""
import requests
import logging
from typing import Dict, Any, Optional

# Import configuration
from config.settings import (
    NOMINATIM_API_URL,
    API_TIMEOUT,
    MAX_RETRIES,
    ENABLE_CACHE
)

# Set up logging
logger = logging.getLogger(__name__)

# Simple in-memory cache
if ENABLE_CACHE:
    geocode_cache = {}

def geocode_location(query: str) -> Optional[Dict[str, Any]]:
    """
    Convert a location name to coordinates using Nominatim.
    
    Args:
        query (str): The location name to geocode
        
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing lat, lon, and display_name,
                                 or None if geocoding failed
    """
    # Check cache first if enabled
    if ENABLE_CACHE and query in geocode_cache:
        logger.info(f"Cache hit for geocoding query: {query}")
        return geocode_cache[query]
    
    logger.info(f"Geocoding location: {query}")
    
    # Initialize retry counter
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            # Prepare the request parameters
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                # Add a user agent as required by Nominatim's usage policy
                # In a production app, replace with your app's name and contact info
                "user-agent": "GeoViz3D"
            }
            
            # Make the request
            response = requests.get(NOMINATIM_API_URL, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            if data:
                result = {
                    "lat": float(data[0]["lat"]),
                    "lon": float(data[0]["lon"]),
                    "display_name": data[0]["display_name"]
                }
                
                # Cache the result if caching is enabled
                if ENABLE_CACHE:
                    geocode_cache[query] = result
                
                return result
            else:
                logger.warning(f"No results found for geocoding query: {query}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on geocoding request (attempt {retries+1}/{MAX_RETRIES})")
            retries += 1
            if retries < MAX_RETRIES:
                # Exponential backoff
                import time
                time.sleep(2 ** retries)
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                logger.warning(f"Rate limit hit on geocoding API (attempt {retries+1}/{MAX_RETRIES})")
                retries += 1
                if retries < MAX_RETRIES:
                    # Parse Retry-After header if available, otherwise use exponential backoff
                    import time
                    retry_after = int(e.response.headers.get("Retry-After", 2 ** retries))
                    time.sleep(retry_after)
            else:
                logger.error(f"HTTP error from geocoding API: {str(e)}")
                return None
        
        except Exception as e:
            logger.error(f"Error with geocoding: {str(e)}")
            return None
    
    # If we've exhausted all retries
    logger.error(f"Failed to geocode location after {MAX_RETRIES} attempts")
    return None

def reverse_geocode(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Convert coordinates to a location name using Nominatim.
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
        
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing address information,
                                 or None if reverse geocoding failed
    """
    cache_key = f"{lat},{lon}"
    
    # Check cache first if enabled
    if ENABLE_CACHE and cache_key in geocode_cache:
        logger.info(f"Cache hit for reverse geocoding: {cache_key}")
        return geocode_cache[cache_key]
    
    logger.info(f"Reverse geocoding coordinates: {lat}, {lon}")
    
    try:
        # Prepare the request parameters
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            # Add a user agent as required by Nominatim's usage policy
            "user-agent": "GeoViz3D"
        }
        
        # Make the request
        response = requests.get(
            NOMINATIM_API_URL.replace("search", "reverse"), 
            params=params, 
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        
        if data and "display_name" in data:
            result = {
                "display_name": data["display_name"],
                "address": data.get("address", {}),
                "lat": lat,
                "lon": lon
            }
            
            # Cache the result if caching is enabled
            if ENABLE_CACHE:
                geocode_cache[cache_key] = result
            
            return result
        else:
            logger.warning(f"No results found for reverse geocoding: {lat}, {lon}")
            return None
            
    except Exception as e:
        logger.error(f"Error with reverse geocoding: {str(e)}")
        return None