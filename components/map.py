"""
Map Visualization Component for GeoViz3D

This module contains the components for rendering the 3D map visualization.
"""
import streamlit as st
import pydeck as pdk
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple

from utils.data_processing import summarize_map_data
from config.settings import (
    DEFAULT_MAP_STYLE,
    DEFAULT_ZOOM_LEVEL,
    OSM_TAGS_URL
)

def render_map(
    data: Optional[Dict[str, Any]] = None, 
    center: Optional[List[float]] = None, 
    zoom: int = DEFAULT_ZOOM_LEVEL
) -> None:
    """
    Render the 3D map visualization component.
    
    Args:
        data (Optional[Dict[str, Any]], optional): The processed map data. Defaults to None.
        center (Optional[List[float]], optional): The center coordinates [lat, lon]. Defaults to None.
        zoom (int, optional): The zoom level. Defaults to DEFAULT_ZOOM_LEVEL.
    """
    # Create the 3D map
    deck = create_3d_map(data, center, zoom)
    st.pydeck_chart(deck)
    
    # Display data summary if data is available
    if data:
        with st.expander("Data Summary", expanded=True):
            st.markdown(summarize_map_data(data))
            
            # Display a table of tags for educational purposes
            if st.checkbox("Show common OSM tags"):
                st.write("Common OpenStreetMap tags:")
                try:
                    import requests
                    response = requests.get(OSM_TAGS_URL, params={"page": 1, "rp": 10})
                    tags_data = response.json()
                    tags_df = pd.DataFrame(tags_data["data"])
                    st.dataframe(tags_df[["key", "value", "count", "description"]])
                except Exception as e:
                    st.write(f"Could not fetch tag data: {str(e)}")

def create_3d_map(
    data: Optional[Dict[str, Any]] = None, 
    center: Optional[List[float]] = None, 
    zoom: int = DEFAULT_ZOOM_LEVEL
) -> pdk.Deck:
    """
    Create a 3D map visualization using PyDeck.
    
    Args:
        data (Optional[Dict[str, Any]], optional): The processed map data. Defaults to None.
        center (Optional[List[float]], optional): The center coordinates [lat, lon]. Defaults to None.
        zoom (int, optional): The zoom level. Defaults to DEFAULT_ZOOM_LEVEL.
        
    Returns:
        pdk.Deck: The PyDeck Deck object
    """
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
            map_style=DEFAULT_MAP_STYLE,
        )

    # Determine map center from data if not provided
    if not center and data.get("buildings", []):
        center_building = data["buildings"][0]["coordinates"][0]
        center = [center_building[1], center_building[0]]  # [lat, lon]
    elif not center and data.get("points", []):
        center_point = data["points"][0]["coordinates"]
        center = [center_point[1], center_point[0]]  # [lat, lon]
    
    layers = []
    
    # Add building layer if selected and data available
    if "buildings" in st.session_state.selected_layers and data.get("buildings", []):
        layers.append(create_buildings_layer(data["buildings"]))
    
    # Add road layer if selected and data available
    if "roads" in st.session_state.selected_layers and data.get("roads", []):
        layers.append(create_roads_layer(data["roads"]))
    
    # Add point layer if selected and data available
    if "points" in st.session_state.selected_layers and data.get("points", []):
        layers.append(create_points_layer(data["points"]))
    
    # Add polygon layer if selected and data available
    if "polygons" in st.session_state.selected_layers and data.get("polygons", []):
        layers.append(create_polygons_layer(data["polygons"]))
    
    # Add a heatmap layer if selected
    if "heatmap" in st.session_state.selected_layers and data.get("points", []):
        layers.append(create_heatmap_layer(data["points"]))
    
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
        map_style=DEFAULT_MAP_STYLE,
        tooltip={"text": "{name}\nType: {type}\nID: {element_id}"}
    )

def create_buildings_layer(buildings: List[Dict[str, Any]]) -> pdk.Layer:
    """
    Create a buildings layer for PyDeck.
    
    Args:
        buildings (List[Dict[str, Any]]): List of building data
        
    Returns:
        pdk.Layer: PyDeck layer for buildings
    """
    building_data = []
    for building in buildings:
        # Create a polygon for each building
        building_data.append({
            "polygon": building["coordinates"],
            "name": building["name"],
            "height": building["height"],
            "element_id": building["element_id"],
            "type": "building",
            "color": building.get("color", [74, 140, 247, 200])
        })
    
    return pdk.Layer(
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

def create_roads_layer(roads: List[Dict[str, Any]]) -> pdk.Layer:
    """
    Create a roads layer for PyDeck.
    
    Args:
        roads (List[Dict[str, Any]]): List of road data
        
    Returns:
        pdk.Layer: PyDeck layer for roads
    """
    roads_data = []
    for road in roads:
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
    
    return pdk.Layer(
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

def create_points_layer(points: List[Dict[str, Any]]) -> pdk.Layer:
    """
    Create a points layer for PyDeck.
    
    Args:
        points (List[Dict[str, Any]]): List of point data
        
    Returns:
        pdk.Layer: PyDeck layer for points
    """
    points_data = []
    for point in points:
        points_data.append({
            "position": point["coordinates"],
            "name": point["name"],
            "type": point["type"],
            "element_id": point["element_id"]
        })
    
    return pdk.Layer(
        "ScatterplotLayer",
        data=points_data,
        get_position="position",
        get_color=[255, 0, 0, 200],
        get_radius=15,
        pickable=True,
        highlight_color=[255, 200, 0, 200],
        auto_highlight=True
    )

def create_polygons_layer(polygons: List[Dict[str, Any]]) -> pdk.Layer:
    """
    Create a polygons layer for PyDeck.
    
    Args:
        polygons (List[Dict[str, Any]]): List of polygon data
        
    Returns:
        pdk.Layer: PyDeck layer for polygons
    """
    polygon_data = []
    for polygon in polygons:
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
    
    return pdk.Layer(
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

def create_heatmap_layer(points: List[Dict[str, Any]]) -> pdk.Layer:
    """
    Create a heatmap layer for PyDeck.
    
    Args:
        points (List[Dict[str, Any]]): List of point data
        
    Returns:
        pdk.Layer: PyDeck layer for heatmap
    """
    heatmap_data = []
    for point in points:
        heatmap_data.append({
            "position": point["coordinates"],
            "weight": 1  # Could be based on some attribute in real data
        })
    
    return pdk.Layer(
        "HeatmapLayer",
        data=heatmap_data,
        get_position="position",
        get_weight="weight",
        radiusPixels=60,
        opacity=0.7,
        threshold=0.1
    )