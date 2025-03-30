"""
GeoViz3D - Configuration and Settings Module

This module loads environment variables and defines application settings.
It serves as a central place for application configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Find the .env file - look in the project root directory
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# API Keys - Never hardcode these values
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")  # Optional, for enhanced styling

# API Endpoints
OVERPASS_API_URL = os.getenv("OVERPASS_API_URL", "https://overpass-api.de/api/interpreter")
NOMINATIM_API_URL = os.getenv("NOMINATIM_API_URL", "https://nominatim.openstreetmap.org/search")
ELEVATION_API_URL = os.getenv("ELEVATION_API_URL", "https://api.open-elevation.com/api/v1/lookup")
OSM_TAGS_URL = os.getenv("OSM_TAGS_URL", "https://taginfo.openstreetmap.org/api/4/tags/popular")

# LLM Configuration
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1000"))

# Application Settings
APP_TITLE = os.getenv("APP_TITLE", "GeoViz3D - 3D Geospatial AI Assistant")
DEFAULT_ZOOM_LEVEL = int(os.getenv("DEFAULT_ZOOM_LEVEL", "11"))
DEFAULT_BUILDING_HEIGHT_FACTOR = float(os.getenv("DEFAULT_BUILDING_HEIGHT_FACTOR", "1.0"))
DEFAULT_MAP_STYLE = os.getenv("DEFAULT_MAP_STYLE", "mapbox://styles/mapbox/satellite-streets-v11")
DEFAULT_LATITUDE = float(os.getenv("DEFAULT_LATITUDE", "0"))
DEFAULT_LONGITUDE = float(os.getenv("DEFAULT_LONGITUDE", "0"))
DEFAULT_LAYERS = os.getenv("DEFAULT_LAYERS", "buildings,roads,points,polygons").split(",")

# Request settings
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Data processing settings
MAX_FEATURES = int(os.getenv("MAX_FEATURES", "1000"))
MAX_ELEVATION_POINTS = int(os.getenv("MAX_ELEVATION_POINTS", "100"))

# Cache settings
ENABLE_CACHE = os.getenv("ENABLE_CACHE", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour in seconds

# Path settings
STATIC_DIR = Path(__file__).resolve().parent.parent / 'static'
PROMPTS_DIR = Path(__file__).resolve().parent.parent / 'prompts'

# Verify critical environment variables
def verify_env_variables():
    """Verify that critical environment variables are set."""
    critical_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in critical_vars if not globals().get(var)]
    
    if missing_vars:
        missing_vars_str = ", ".join(missing_vars)
        raise EnvironmentError(
            f"Missing critical environment variables: {missing_vars_str}. "
            f"Please check your .env file or environment variables."
        )

# Call verification function when module is imported
verify_env_variables()