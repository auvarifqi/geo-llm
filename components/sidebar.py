"""
Sidebar Component for GeoViz3D

This module contains the components for rendering the sidebar.
"""
import streamlit as st
from typing import List

def render_sidebar():
    """
    Render the sidebar component with all controls and options.
    """
    with st.sidebar:
        st.title("Controls & Settings")
        
        # Map options section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("Map Options")
        
        # Layer selection
        st.multiselect(
            "Select map layers",
            ["buildings", "roads", "points", "polygons", "terrain", "heatmap"],
            default=st.session_state.selected_layers,
            key="layer_select",
            on_change=lambda: setattr(st.session_state, "selected_layers", st.session_state.layer_select)
        )
        
        # Building height control
        st.slider(
            "Building height factor",
            min_value=0.1,
            max_value=5.0,
            value=st.session_state.building_height_factor,
            step=0.1,
            key="height_factor",
            on_change=lambda: setattr(st.session_state, "building_height_factor", st.session_state.height_factor)
        )
        
        # Camera controls
        st.slider(
            "Zoom level",
            min_value=1,
            max_value=20,
            value=st.session_state.zoom_level,
            step=1,
            key="zoom",
            on_change=lambda: setattr(st.session_state, "zoom_level", st.session_state.zoom)
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # History section
        render_location_history()
        
        # Help section
        render_help_section()
        
        # Credits
        st.markdown("""
        <div style='text-align: center; margin-top: 20px;'>
            <p style='font-size: 0.8em; color: #888;'>Powered by<br>OpenStreetMap, PyDeck, and OpenAI</p>
        </div>
        """, unsafe_allow_html=True)

def render_location_history():
    """
    Render the location history section of the sidebar.
    """
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.subheader("Location History")
    
    if st.session_state.searched_locations:
        for idx, location in enumerate(st.session_state.searched_locations):
            if st.button(f"📍 {location['name']}", key=f"loc_{idx}"):
                # Set the map center to this location
                st.session_state.map_center = [location["lat"], location["lon"]]
                
                # Create a simple query for this location
                lat, lon = location["lat"], location["lon"]
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
                
                # Import here to avoid circular imports
                from services.overpass_service import query_overpass
                from utils.data_processing import process_overpass_results
                
                # Process the query
                overpass_result = query_overpass(simple_query)
                if overpass_result:
                    st.session_state.map_data = process_overpass_results(overpass_result)
                    st.rerun()
    else:
        st.write("No locations in history yet")
    
    if st.session_state.searched_locations and st.button("Clear History"):
        st.session_state.searched_locations = []
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_help_section():
    """
    Render the help and tips section of the sidebar.
    """
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.subheader("Help & Tips")
    
    with st.expander("Example Queries"):
        st.write("""
        - Show me all museums in Paris
        - Find hospitals in Berlin
        - Map tall buildings in Singapore
        - Where are all the parks in Central Park, NYC?
        - Show me the metro stations in Tokyo
        """)
    
    with st.expander("About OSM Data"):
        st.write("""
        OpenStreetMap (OSM) is a collaborative project to create a free editable map of the world. 
        Our app uses the Overpass API to query this rich dataset and visualize it in 3D.
        """)
    
    with st.expander("3D Visualization Guide"):
        st.write("""
        - Buildings are extruded based on their height or number of levels
        - Roads are shown with different colors based on their type
        - Use the mouse to navigate: 
            - Left-click and drag to move around
            - Right-click and drag to rotate
            - Scroll to zoom in/out
        """)
        
    with st.expander("OSM Tags Reference"):
        st.write("""
        Common OpenStreetMap tags:
        
        Buildings:
        - building=yes (generic building)
        - building=residential/commercial/industrial
        - building:levels=* (number of floors)
        - height=* (height in meters)
        
        Roads:
        - highway=motorway/trunk/primary/secondary/residential
        - surface=asphalt/concrete/gravel
        - lanes=* (number of lanes)
        
        Points of Interest:
        - amenity=restaurant/cafe/hospital/school
        - tourism=museum/hotel/attraction
        - shop=supermarket/bakery/clothes
        
        Natural Features:
        - natural=water/wood/peak
        - landuse=forest/meadow/residential
        - leisure=park/garden/playground
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)