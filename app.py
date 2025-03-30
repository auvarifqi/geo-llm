"""
GeoViz3D - Main Application

This is the main entry point for the GeoViz3D application.
It sets up the Streamlit interface and coordinates the various components.
"""
import streamlit as st
from pathlib import Path
import os

# Import configuration
from config.settings import (
    APP_TITLE, 
    DEFAULT_ZOOM_LEVEL,
    DEFAULT_BUILDING_HEIGHT_FACTOR,
    DEFAULT_LAYERS
)

# Import components
from components.sidebar import render_sidebar
from components.map import render_map
from components.chat import render_chat_interface

# Import services
from services.llm_service import process_user_query
from services.overpass_service import query_overpass, extract_overpass_query
from services.geocoding_service import geocode_location
from services.elevation_service import get_elevation_data

# Import utilities
from utils.data_processing import process_overpass_results

# Initialize application state
def init_session_state():
    """Initialize the session state variables if they don't exist."""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    if 'map_data' not in st.session_state:
        st.session_state.map_data = None
        
    if 'map_center' not in st.session_state:
        st.session_state.map_center = [0, 0]
        
    if 'zoom_level' not in st.session_state:
        st.session_state.zoom_level = DEFAULT_ZOOM_LEVEL
        
    if 'selected_layers' not in st.session_state:
        st.session_state.selected_layers = DEFAULT_LAYERS
        
    if 'building_height_factor' not in st.session_state:
        st.session_state.building_height_factor = DEFAULT_BUILDING_HEIGHT_FACTOR

    if 'searched_locations' not in st.session_state:
        st.session_state.searched_locations = []

def main():
    """Main function to run the Streamlit app."""
    # Configure the page
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🌏",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    init_session_state()

    # Apply custom CSS
    apply_custom_css()

    # App title and description
    st.markdown('<div class="main-title">🌏 GeoViz3D</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">An AI-powered 3D Geospatial Visualization Platform</div>', unsafe_allow_html=True)

    # Create sidebar
    render_sidebar()

    # Main app layout
    col1, col2 = st.columns([1, 1])

    # Chat interface in left column
    with col1:
        user_input, location_input = render_chat_interface()
        
        # Process location search request
        if location_input and st.button("Go to Location"):
            process_location_search(location_input)
            
        # Process chat input
        if user_input and st.button("Ask"):
            process_chat_input(user_input)

    # Map visualization in right column
    with col2:
        st.subheader("🗺️ 3D Visualization")
        render_map(
            st.session_state.map_data, 
            center=st.session_state.map_center,
            zoom=st.session_state.zoom_level
        )

    # Footer
    st.markdown("""
    <div style='text-align: center; margin-top: 20px;'>
        <p style='font-size: 0.8em; color: #888;'>GeoViz3D - Bringing geospatial data to life in 3D</p>
    </div>
    """, unsafe_allow_html=True)

def process_location_search(location_name):
    """Process a location search request."""
    with st.spinner(f"Finding {location_name}..."):
        location_data = geocode_location(location_name)
        if location_data:
            st.success(f"Found: {location_data['display_name']}")
            
            # Update map center
            st.session_state.map_center = [location_data["lat"], location_data["lon"]]
            
            # Add to history
            if location_data not in st.session_state.searched_locations:
                st.session_state.searched_locations.append({
                    "name": location_name,
                    "lat": location_data["lat"],
                    "lon": location_data["lon"]
                })
            
            # Create a simple query for this location
            lat, lon = location_data["lat"], location_data["lon"]
            simple_query = f"""
            [out:json];
            (
              node(around:500,{lat},{lon});
              way(around:500,{lat},{lon});
              relation(around:500,{lat},{lon});
            );
            out body;
            >;
            out skel qt;
            """
            
            # Process the query
            overpass_result = query_overpass(simple_query)
            if overpass_result:
                st.session_state.map_data = process_overpass_results(overpass_result)
                
                # Trigger a rerun to update the UI
                st.rerun()
        else:
            st.error(f"Could not find location: {location_name}")

def process_chat_input(user_input):
    """Process a chat input from the user."""
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    # Query the LLM service
    with st.spinner("Thinking..."):
        llm_response = process_user_query(user_input, st.session_state.chat_history)
    
    if llm_response:
        # Add bot response to chat history
        st.session_state.chat_history.append({"role": "assistant", "content": llm_response})
        
        # Try to extract and run an Overpass query
        overpass_query = extract_overpass_query(llm_response)
        if overpass_query:
            with st.spinner("Fetching map data..."):
                overpass_result = query_overpass(overpass_query)
                if overpass_result:
                    # Process the Overpass result for visualization
                    st.session_state.map_data = process_overpass_results(
                        overpass_result,
                        building_height_factor=st.session_state.building_height_factor
                    )
                    
                    # Try to extract a location from the first element
                    if "elements" in overpass_result and overpass_result["elements"]:
                        first_element = overpass_result["elements"][0]
                        if "lat" in first_element and "lon" in first_element:
                            lat, lon = first_element["lat"], first_element["lon"]
                            st.session_state.map_center = [lat, lon]
                            
                            # Add to history
                            place_name = first_element.get("tags", {}).get("name", "Unknown location")
                            location_info = {
                                "name": place_name,
                                "lat": lat,
                                "lon": lon
                            }
                            
                            if not any(
                                abs(loc["lat"] - lat) < 0.001 and abs(loc["lon"] - lon) < 0.001 
                                for loc in st.session_state.searched_locations
                            ):
                                st.session_state.searched_locations.append(location_info)
    
    # Trigger a rerun to update the UI
    st.rerun()

def apply_custom_css():
    """Apply custom CSS styling to the application."""
    st.markdown("""
    <style>
    .main-title {
        font-size: 3em;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5em;
    }
    .subtitle {
        font-size: 1.2em;
        color: #5A5A5A;
        text-align: center;
        margin-bottom: 2em;
    }
    .chat-container {
        border-radius: 10px;
        background-color: #f0f2f6;
        padding: 20px;
        margin-bottom: 20px;
    }
    .user-message {
        background-color: #DCF8C6;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
    .bot-message {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 10px;
        margin: 5px 0;
    }
    .sidebar-section {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()