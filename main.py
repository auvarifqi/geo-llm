import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import requests
import os
import json
import time
from PIL import Image
from io import BytesIO
from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from transformers import pipeline

# Set OpenAI API key

# Constants
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
ELEVATION_API_URL = "https://api.open-elevation.com/api/v1/lookup"
NOMINATIM_API_URL = "https://nominatim.openstreetmap.org/search"
OSM_TAGS_URL = "https://taginfo.openstreetmap.org/api/4/tags/popular"

# Set page configuration
st.set_page_config(
    page_title="GeoViz3D - 3D Geospatial AI Assistant",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'map_data' not in st.session_state:
    st.session_state.map_data = None

if 'map_center' not in st.session_state:
    st.session_state.map_center = [0, 0]

if 'zoom_level' not in st.session_state:
    st.session_state.zoom_level = 11

if 'selected_layers' not in st.session_state:
    st.session_state.selected_layers = ["buildings", "roads"]

if 'building_height_factor' not in st.session_state:
    st.session_state.building_height_factor = 1.0

if 'searched_locations' not in st.session_state:
    st.session_state.searched_locations = []

# Improved LLM prompts
SYSTEM_PROMPT = """You are GeoViz3D, an expert geospatial AI assistant. 
For each user question about locations, provide:

1. An Overpass API query to fetch relevant geographical data. Enclose it in ```overpass blocks.
2. A brief explanation of what the query will show.
3. A suggestion for how to best visualize this data in 3D.
4. A fascinating geographical fact related to the query.

If a user asks about 3D visualization features, explain how different OSM features can be visualized in 3D.
If a user asks a question not relevant to geospatial data, politely redirect them and suggest a geospatial question.
"""

# Utility functions
def query_openai(messages):
    """Query OpenAI API with improved prompts"""
    try:
        response = client.chat.completions.create(model="gpt-4",
        messages=messages,
        temperature=0.3,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0)
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error querying OpenAI API: {e}")
        return None

def query_overpass(query):
    """Query Overpass API with better error handling"""
    try:
        payload = {"data": query}
        response = requests.post(OVERPASS_API_URL, data=payload, timeout=30)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error querying Overpass API: {e}")
        return None

def get_elevation_data(coords_list):
    """Get elevation data for a list of coordinates"""
    try:
        if not coords_list:
            return []

        # Prepare the request payload
        locations = [{"latitude": lat, "longitude": lon} for lon, lat in coords_list]
        payload = {"locations": locations}

        # Make the request
        response = requests.post(ELEVATION_API_URL, json=payload, timeout=30)
        response.raise_for_status()

        # Extract the elevation data
        results = response.json().results
        return [result["elevation"] for result in results]
    except Exception as e:
        st.warning(f"Could not fetch elevation data: {e}")
        # Return zero elevations as fallback
        return [0] * len(coords_list)

def geocode_location(query):
    """Convert location name to coordinates using Nominatim"""
    try:
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        response = requests.get(NOMINATIM_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data:
            return {
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
                "display_name": data[0]["display_name"]
            }
        else:
            return None
    except Exception as e:
        st.error(f"Error with geocoding: {e}")
        return None

def extract_overpass_query(text):
    """Extract Overpass query from AI response"""
    if "```overpass" in text and "```" in text.split("```overpass")[1]:
        return text.split("```overpass")[1].split("```")[0].strip()
    elif "```" in text:
        # Fallback if the specific format isn't followed
        parts = text.split("```")
        if len(parts) >= 3:
            return parts[1].strip()
    return None

def process_overpass_results(data):
    """Process Overpass API results into format suitable for 3D visualization"""
    if not data or "elements" not in data:
        return None

    elements = data["elements"]

    # Initialize empty collections for different feature types
    buildings = []
    roads = []
    points = []
    polygons = []

    # Process each element
    for element in elements:
        element_type = element.get("type")
        tags = element.get("tags", {})

        # Process nodes (points)
        if element_type == "node" and "lat" in element and "lon" in element:
            points.append({
                "coordinates": [element["lon"], element["lat"]],
                "name": tags.get("name", "Unknown"),
                "type": tags.get("amenity") or tags.get("shop") or tags.get("tourism") or "point",
                "element_id": element.get("id"),
                "tags": tags
            })

        # Process ways (lines or polygons)
        elif element_type == "way" and "nodes" in element:
            # Get coordinates for the way
            coords = []
            for ref in element.get("geometry", []):
                if "lat" in ref and "lon" in ref:
                    coords.append([ref["lon"], ref["lat"]])

            # Skip if no coordinates
            if not coords:
                continue

            # Check if it's a building
            if "building" in tags:
                height = float(tags.get("height", tags.get("building:levels", 1))) * 3 * st.session_state.building_height_factor
                buildings.append({
                    "coordinates": coords,
                    "name": tags.get("name", "Unknown Building"),
                    "height": height,
                    "element_id": element.get("id"),
                    "color": [74, 140, 247, 200],
                    "tags": tags
                })

            # Check if it's a road
            elif "highway" in tags:
                width = {
                    "motorway": 4,
                    "trunk": 3.5,
                    "primary": 3,
                    "secondary": 2.5,
                    "tertiary": 2,
                    "residential": 1.5
                }.get(tags["highway"], 1)

                roads.append({
                    "coordinates": coords,
                    "name": tags.get("name", "Unknown Road"),
                    "width": width,
                    "element_id": element.get("id"),
                    "type": tags["highway"],
                    "tags": tags
                })

            # Other polygons
            elif element.get("geometry") and coords[0] == coords[-1]:  # Closed way
                polygons.append({
                    "coordinates": coords,
                    "name": tags.get("name", "Unknown Area"),
                    "type": next((k for k in ["landuse", "natural", "leisure"] if k in tags), "other"),
                    "element_id": element.get("id"),
                    "tags": tags
                })

    # Get terrain elevation if we have buildings
    if buildings and all(coord for building in buildings for coord in building["coordinates"]):
        all_coords = [coord for building in buildings for coord in building["coordinates"]]
        elevations = get_elevation_data(all_coords[:100])  # Limit to 100 points to avoid API overload

        # Use the average elevation if we have data
        if elevations:
            avg_elevation = sum(elevations) / len(elevations)
        else:
            avg_elevation = 0
    else:
        avg_elevation = 0

    return {
        "buildings": buildings,
        "roads": roads,
        "points": points,
        "polygons": polygons,
        "terrain_elevation": avg_elevation
    }

def create_3d_map(data, center=None, zoom=11):
    """Create a 3D map visualization using PyDeck"""
    if not data:
        # Create an empty map centered at the specified location
        view_state = pdk.ViewState(
            longitude=center[1] if center else 0,
            latitude=center[0] if center else 0,
            zoom=zoom,
            pitch=45,
            bearing=0
        )
        return pdk.Deck(
            initial_view_state=view_state,
            map_style="mapbox://styles/mapbox/satellite-streets-v11",
        )

    # Determine map center from data if not provided
    if not center and data["buildings"]:
        center_building = data["buildings"][0]["coordinates"][0]
        center = [center_building[1], center_building[0]]  # [lat, lon]
    elif not center and data["points"]:
        center_point = data["points"][0]["coordinates"]
        center = [center_point[1], center_point[0]]  # [lat, lon]

    layers = []

    # Add building layer if selected and data available
    if "buildings" in st.session_state.selected_layers and data["buildings"]:
        building_data = []
        for building in data["buildings"]:
            # Create a polygon for each building
            building_data.append({
                "polygon": building["coordinates"],
                "name": building["name"],
                "height": building["height"],
                "element_id": building["element_id"],
                "color": building.get("color", [74, 140, 247, 200])
            })

        buildings_layer = pdk.Layer(
            "PolygonLayer",
            data=building_data,
            get_polygon="polygon",
            get_elevation="height",
            get_fill_color="color",
            get_line_color=[255, 255, 255],
            get_line_width=2,
            highlight_color=[255, 200, 0, 200],
            auto_highlight=True,
            pickable=True,
            extruded=True,
            elevation_scale=1,
            coverage=1,
        )
        layers.append(buildings_layer)

    # Add road layer if selected and data available
    if "roads" in st.session_state.selected_layers and data["roads"]:
        roads_data = []
        for road in data["roads"]:
            roads_data.append({
                "path": road["coordinates"],
                "name": road["name"],
                "width": road["width"],
                "type": road["type"],
                "element_id": road["element_id"]
            })

        # Different colors for different road types
        road_colors = {
            "motorway": [255, 0, 0, 200],
            "trunk": [255, 97, 0, 200],
            "primary": [255, 170, 0, 200],
            "secondary": [255, 255, 0, 200],
            "tertiary": [171, 221, 164, 200],
            "residential": [255, 255, 255, 200]
        }

        roads_layer = pdk.Layer(
            "PathLayer",
            data=roads_data,
            get_path="path",
            get_width="width * 5",  # Scale width for visibility
            get_color=lambda d: road_colors.get(d["type"], [180, 180, 180, 200]),
            width_scale=1,
            width_min_pixels=2,
            rounded=True,
            pickable=True,
            highlight_color=[255, 200, 0, 200],
            auto_highlight=True
        )
        layers.append(roads_layer)

    # Add point layer if selected and data available
    if "points" in st.session_state.selected_layers and data["points"]:
        points_data = []
        for point in data["points"]:
            points_data.append({
                "position": point["coordinates"],
                "name": point["name"],
                "type": point["type"],
                "element_id": point["element_id"]
            })

        points_layer = pdk.Layer(
            "ScatterplotLayer",
            data=points_data,
            get_position="position",
            get_color=[255, 0, 0, 200],
            get_radius=15,
            pickable=True,
            highlight_color=[255, 200, 0, 200],
            auto_highlight=True
        )
        layers.append(points_layer)

    # Add polygon layer if selected and data available
    if "polygons" in st.session_state.selected_layers and data["polygons"]:
        polygon_data = []
        for polygon in data["polygons"]:
            polygon_data.append({
                "polygon": polygon["coordinates"],
                "name": polygon["name"],
                "type": polygon["type"],
                "element_id": polygon["element_id"]
            })

        # Different colors for different polygon types
        polygon_colors = {
            "landuse": [200, 200, 100, 150],
            "natural": [100, 200, 100, 150],
            "leisure": [100, 200, 200, 150],
            "other": [150, 150, 150, 150]
        }

        polygons_layer = pdk.Layer(
            "PolygonLayer",
            data=polygon_data,
            get_polygon="polygon",
            get_fill_color=lambda d: polygon_colors.get(d["type"], [150, 150, 150, 150]),
            get_line_color=[255, 255, 255],
            get_line_width=2,
            highlight_color=[255, 200, 0, 200],
            auto_highlight=True,
            pickable=True
        )
        layers.append(polygons_layer)

    # Add a terrain layer using elevation data
    if "terrain" in st.session_state.selected_layers:
        # This would ideally use a proper terrain elevation API or dataset
        # For demonstration, we're using a simplified approach
        pass  # This would be implemented with a proper terrain data source

    # Add a 3D heatmap layer if selected
    if "heatmap" in st.session_state.selected_layers and data["points"]:
        heatmap_data = []
        for point in data["points"]:
            heatmap_data.append({
                "position": point["coordinates"],
                "weight": 1  # Could be based on some attribute in real data
            })

        heatmap_layer = pdk.Layer(
            "HeatmapLayer",
            data=heatmap_data,
            get_position="position",
            get_weight="weight",
            radiusPixels=60,
            opacity=0.7,
            threshold=0.1
        )
        layers.append(heatmap_layer)

    # Create the view state
    view_state = pdk.ViewState(
        longitude=center[1],
        latitude=center[0],
        zoom=zoom,
        pitch=45,
        bearing=0
    )

    # Return the deck
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/satellite-streets-v11",
        tooltip={"text": "{name}\nType: {type}\nID: {element_id}"}
    )

def summarize_map_data(data):
    """Generate a summary of the map data for the user"""
    if not data:
        return "No data to display. Try a different query."

    summary = []

    # Summarize buildings
    if data["buildings"]:
        num_buildings = len(data["buildings"])
        avg_height = sum(b["height"] for b in data["buildings"]) / num_buildings
        summary.append(f"🏢 {num_buildings} buildings found with average height of {avg_height:.1f}m")

    # Summarize roads
    if data["roads"]:
        road_types = {}
        total_length = 0
        for road in data["roads"]:
            road_type = road["type"]
            road_types[road_type] = road_types.get(road_type, 0) + 1

            # Calculate approximate length
            coords = road["coordinates"]
            length = 0
            for i in range(len(coords) - 1):
                # Simple distance calculation (not accurate for long distances)
                length += ((coords[i+1][0] - coords[i][0])**2 + (coords[i+1][1] - coords[i][1])**2)**0.5
            total_length += length * 111000  # Rough conversion to meters

        summary.append(f"🛣️ {len(data['roads'])} roads found, approximately {total_length:.1f}m total length")
        summary.append(f"   Road types: {', '.join([f'{k} ({v})' for k, v in road_types.items()])}")

    # Summarize points
    if data["points"]:
        point_types = {}
        for point in data["points"]:
            point_type = point["type"]
            point_types[point_type] = point_types.get(point_type, 0) + 1

        summary.append(f"📍 {len(data['points'])} points of interest found")
        if point_types:
            summary.append(f"   Types: {', '.join([f'{k} ({v})' for k, v in point_types.items()])}")

    # Summarize polygons
    if data["polygons"]:
        polygon_types = {}
        for polygon in data["polygons"]:
            polygon_type = polygon["type"]
            polygon_types[polygon_type] = polygon_types.get(polygon_type, 0) + 1

        summary.append(f"🔷 {len(data['polygons'])} areas/polygons found")
        if polygon_types:
            summary.append(f"   Types: {', '.join([f'{k} ({v})' for k, v in polygon_types.items()])}")

    return "\n".join(summary)

def main():
    """Main function to run the Streamlit app"""
    # Custom CSS for styling
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

    # App title and description
    st.markdown('<div class="main-title">🌏 GeoViz3D</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">An AI-powered 3D Geospatial Visualization Platform</div>', unsafe_allow_html=True)

    # Create a sidebar with options
    with st.sidebar:
        st.image("https://raw.githubusercontent.com/streamlit/streamlit/master/examples/data/logo.png", width=200)
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

                    # Process the query
                    overpass_result = query_overpass(simple_query)
                    if overpass_result:
                        st.session_state.map_data = process_overpass_results(overpass_result)
        else:
            st.write("No locations in history yet")

        if st.session_state.searched_locations and st.button("Clear History"):
            st.session_state.searched_locations = []

        st.markdown('</div>', unsafe_allow_html=True)

        # Help section
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
        st.markdown('</div>', unsafe_allow_html=True)

        # Credits
        st.markdown("""
        <div style='text-align: center; margin-top: 20px;'>
            <p style='font-size: 0.8em; color: #888;'>Powered by<br>OpenStreetMap, PyDeck, and OpenAI</p>
        </div>
        """, unsafe_allow_html=True)

    # Main app layout
    col1, col2 = st.columns([1, 1])

    # Chat interface
    with col1:
        st.subheader("📝 Ask me about places")

        # Display chat history
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'<div class="user-message">👤 <b>You:</b> {message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bot-message">🌏 <b>GeoViz3D:</b> {message["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Input field
        user_input = st.text_area("What can I help you find or visualize?", key="user_input")

        # Direct geocoding option
        location_name = st.text_input("Or enter a location name to jump directly to it:", key="location_input")

        # Process geocoding request
        if location_name and st.button("Go to Location"):
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
                else:
                    st.error(f"Could not find location: {location_name}")

        # Process chat input
        if user_input and st.button("Ask"):
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            # Create messages for OpenAI
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
            ]

            # Add chat history (limit to last 5 exchanges to save tokens)
            for message in st.session_state.chat_history[-10:]:
                messages.append({"role": message["role"], "content": message["content"]})

            # Query OpenAI
            with st.spinner("Thinking..."):
                response = query_openai(messages)

            if response:
                # Add bot response to chat history
                st.session_state.chat_history.append({"role": "assistant", "content": response})

                # Try to extract and run an Overpass query
                overpass_query = extract_overpass_query(response)
                if overpass_query:
                    with st.spinner("Fetching map data..."):
                        overpass_result = query_overpass(overpass_query)
                        if overpass_result:
                            # Process the Overpass result for visualization
                            st.session_state.map_data = process_overpass_results(overpass_result)

                            # Try to extract a location from the first element
                            if "elements" in overpass_result and overpass_result["elements"]:
                                first_element = overpass_result["elements"][0]
                                if "lat" in first_element and "lon" in first_element:
                                    lat, lon = first_element["lat"], first_element["lon"]
                                    st.session_state.map_center = [lat, lon]

                                    # Add to history
                                    place_name = first_element.get("tags", {}).get("name", "Unknown location")
                                    if all(loc["lat"] != lat or loc["lon"] != lon for loc in st.session_state.searched_locations):
                                        st.session_state.searched_locations.append({
                                            "name": place_name,
                                            "lat": lat,
                                            "lon": lon
                                        })

            # Rerun to update the display
            st.rerun()

    # Map visualization
    with col2:
        st.subheader("🗺️ 3D Visualization")

        # Display 3D map
        deck = create_3d_map(
            st.session_state.map_data, 
            center=st.session_state.map_center,
            zoom=st.session_state.zoom_level
        )
        st.pydeck_chart(deck)

        # Display data summary
        if st.session_state.map_data:
            with st.expander("Data Summary", expanded=True):
                st.markdown(summarize_map_data(st.session_state.map_data))

                # Display a table of tags for educational purposes
                if st.checkbox("Show common OSM tags"):
                    st.write("Common OpenStreetMap tags:")
                    try:
                        response = requests.get(OSM_TAGS_URL, params={"page": 1, "rp": 10})
                        tags_data = response.json()
                        tags_df = pd.DataFrame(tags_data["data"])
                        st.dataframe(tags_df[["key", "value", "count", "description"]])
                    except:
                        st.write("Could not fetch tag data.")

    # Footer
    st.markdown("""
    <div style='text-align: center; margin-top: 20px;'>
        <p style='font-size: 0.8em; color: #888;'>GeoViz3D - Bringing geospatial data to life in 3D</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()