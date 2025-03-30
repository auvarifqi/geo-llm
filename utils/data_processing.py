"""
Data Processing Utilities for GeoViz3D

This module contains utilities for processing geospatial data from the Overpass API.
"""
import logging
from typing import Dict, List, Any, Optional, Tuple

# Import services
from services.elevation_service import get_elevation_data

# Import settings
from config.settings import (
    DEFAULT_BUILDING_HEIGHT_FACTOR,
    MAX_FEATURES
)

# Set up logging
logger = logging.getLogger(__name__)

def process_overpass_results(
    data: Dict[str, Any],
    building_height_factor: float = DEFAULT_BUILDING_HEIGHT_FACTOR
) -> Optional[Dict[str, Any]]:
    """
    Process Overpass API results into a format suitable for 3D visualization.
    
    Args:
        data (Dict[str, Any]): The raw Overpass API response
        building_height_factor (float, optional): Factor to scale building heights. 
            Defaults to DEFAULT_BUILDING_HEIGHT_FACTOR.
        
    Returns:
        Optional[Dict[str, Any]]: Processed data for visualization, or None if processing failed
    """
    if not data or "elements" not in data:
        logger.warning("No elements found in Overpass API response")
        return None
        
    elements = data["elements"]
    
    # Limit the number of elements to process
    if len(elements) > MAX_FEATURES:
        logger.warning(f"Limiting processing to {MAX_FEATURES} elements (from {len(elements)})")
        elements = elements[:MAX_FEATURES]
    
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
            process_node(element, points)
            
        # Process ways (lines or polygons)
        elif element_type == "way" and "nodes" in element:
            process_way(element, buildings, roads, polygons, building_height_factor)
            
        # Process relations (multipolygons, etc.)
        elif element_type == "relation" and "members" in element:
            # Relation processing is more complex and omitted for brevity
            # In a full implementation, you would process relations as well
            pass
    
    # Get terrain elevation if we have buildings
    terrain_elevation = 0
    if buildings and all(coord for building in buildings for coord in building["coordinates"]):
        all_coords = [coord for building in buildings for coord in building["coordinates"]]
        elevations = get_elevation_data(all_coords[:100])  # Limit to 100 points
        
        # Use the average elevation if we have data
        if elevations:
            terrain_elevation = sum(elevations) / len(elevations)
    
    return {
        "buildings": buildings,
        "roads": roads,
        "points": points,
        "polygons": polygons,
        "terrain_elevation": terrain_elevation
    }

def process_node(element: Dict[str, Any], points: List[Dict[str, Any]]) -> None:
    """
    Process a node element from Overpass API.
    
    Args:
        element (Dict[str, Any]): The node element to process
        points (List[Dict[str, Any]]): List to append the processed point to
    """
    tags = element.get("tags", {})
    
    # Skip nodes that are just part of ways unless they have tags
    if not tags:
        return
    
    # Get the most specific type for the point
    point_type = (
        tags.get("amenity") or 
        tags.get("shop") or 
        tags.get("tourism") or 
        tags.get("historic") or
        tags.get("leisure") or
        "point"
    )
    
    # Get name or derive one
    name = tags.get("name", f"{point_type.capitalize()}")
    
    points.append({
        "coordinates": [element["lon"], element["lat"]],
        "name": name,
        "type": point_type,
        "element_id": element.get("id"),
        "tags": tags
    })

def process_way(
    element: Dict[str, Any], 
    buildings: List[Dict[str, Any]],
    roads: List[Dict[str, Any]],
    polygons: List[Dict[str, Any]],
    building_height_factor: float
) -> None:
    """
    Process a way element from Overpass API.
    
    Args:
        element (Dict[str, Any]): The way element to process
        buildings (List[Dict[str, Any]]): List to append buildings to
        roads (List[Dict[str, Any]]): List to append roads to
        polygons (List[Dict[str, Any]]): List to append other polygons to
        building_height_factor (float): Factor to scale building heights
    """
    tags = element.get("tags", {})
    
    # Get coordinates for the way
    coords = []
    for ref in element.get("geometry", []):
        if "lat" in ref and "lon" in ref:
            coords.append([ref["lon"], ref["lat"]])
    
    # Skip if no coordinates
    if not coords:
        return
    
    # Check if it's a building
    if "building" in tags:
        process_building(element, coords, buildings, building_height_factor)
    
    # Check if it's a road
    elif "highway" in tags:
        process_road(element, coords, roads)
    
    # Other polygons
    elif element.get("geometry") and coords[0] == coords[-1]:  # Closed way
        process_polygon(element, coords, polygons)

def process_building(
    element: Dict[str, Any], 
    coords: List[List[float]], 
    buildings: List[Dict[str, Any]],
    building_height_factor: float
) -> None:
    """
    Process a building element.
    
    Args:
        element (Dict[str, Any]): The element to process
        coords (List[List[float]]): Coordinates of the building
        buildings (List[Dict[str, Any]]): List to append the building to
        building_height_factor (float): Factor to scale building heights
    """
    tags = element.get("tags", {})
    
    # Calculate building height
    height = estimate_building_height(tags, building_height_factor)
    
    # Get building name or derive one
    name = tags.get("name", "Building")
    
    # Determine building color based on type
    color = get_building_color(tags)
    
    buildings.append({
        "coordinates": coords,
        "name": name,
        "height": height,
        "element_id": element.get("id"),
        "color": color,
        "tags": tags
    })

def process_road(
    element: Dict[str, Any], 
    coords: List[List[float]], 
    roads: List[Dict[str, Any]]
) -> None:
    """
    Process a road element.
    
    Args:
        element (Dict[str, Any]): The element to process
        coords (List[List[float]]): Coordinates of the road
        roads (List[Dict[str, Any]]): List to append the road to
    """
    tags = element.get("tags", {})
    
    # Determine road width based on highway type
    highway_type = tags.get("highway", "road")
    width = get_road_width(highway_type)
    
    # Get road name or derive one
    name = tags.get("name", f"{highway_type.capitalize()}")
    
    roads.append({
        "coordinates": coords,
        "name": name,
        "width": width,
        "element_id": element.get("id"),
        "type": highway_type,
        "tags": tags
    })

def process_polygon(
    element: Dict[str, Any], 
    coords: List[List[float]], 
    polygons: List[Dict[str, Any]]
) -> None:
    """
    Process a polygon element.
    
    Args:
        element (Dict[str, Any]): The element to process
        coords (List[List[float]]): Coordinates of the polygon
        polygons (List[Dict[str, Any]]): List to append the polygon to
    """
    tags = element.get("tags", {})
    
    # Determine polygon type
    polygon_type = (
        tags.get("landuse") or 
        tags.get("natural") or 
        tags.get("leisure") or 
        "other"
    )
    
    # Get polygon name or derive one
    name = tags.get("name", f"{polygon_type.capitalize()} Area")
    
    polygons.append({
        "coordinates": coords,
        "name": name,
        "type": polygon_type,
        "element_id": element.get("id"),
        "tags": tags
    })

def estimate_building_height(tags: Dict[str, str], height_factor: float) -> float:
    """
    Estimate a building's height based on its tags.
    
    Args:
        tags (Dict[str, str]): The building's tags
        height_factor (float): Factor to scale building heights
        
    Returns:
        float: Estimated height in meters
    """
    # Check if explicit height is available
    if "height" in tags:
        try:
            # Height might be stored as "20 m" or similar
            height_str = tags["height"].split()[0]
            return float(height_str) * height_factor
        except (ValueError, IndexError):
            pass
    
    # Check for building:levels
    if "building:levels" in tags:
        try:
            levels = float(tags["building:levels"])
            # Assume ~3 meters per level
            return levels * 3 * height_factor
        except ValueError:
            pass
    
    # If no height data, estimate based on building type
    building_type = tags.get("building", "yes")
    base_heights = {
        "apartments": 15,
        "residential": 8,
        "house": 6,
        "detached": 6,
        "commercial": 10,
        "industrial": 8,
        "office": 15,
        "retail": 6,
        "warehouse": 8,
        "church": 15,
        "cathedral": 25,
        "mosque": 15,
        "temple": 15,
        "synagogue": 15,
        "school": 9,
        "university": 12,
        "hospital": 15,
        "hotel": 15,
        "train_station": 12,
        "stadium": 20,
        "yes": 8  # Default
    }
    
    base_height = base_heights.get(building_type, 8)
    return base_height * height_factor

def get_building_color(tags: Dict[str, str]) -> List[int]:
    """
    Determine a building's color based on its tags.
    
    Args:
        tags (Dict[str, str]): The building's tags
        
    Returns:
        List[int]: RGBA color as [r, g, b, a]
    """
    building_type = tags.get("building", "yes")
    
    # Color scheme for different building types
    color_scheme = {
        "apartments": [102, 102, 156, 200],
        "residential": [102, 102, 156, 200],
        "house": [119, 119, 165, 200],
        "detached": [119, 119, 165, 200],
        "commercial": [99, 99, 184, 200],
        "industrial": [150, 150, 150, 200],
        "office": [74, 140, 247, 200],
        "retail": [61, 129, 224, 200],
        "warehouse": [150, 150, 150, 200],
        "church": [251, 140, 0, 200],
        "cathedral": [251, 140, 0, 200],
        "mosque": [251, 140, 0, 200],
        "temple": [251, 140, 0, 200],
        "synagogue": [251, 140, 0, 200],
        "school": [255, 128, 128, 200],
        "university": [255, 100, 100, 200],
        "hospital": [226, 122, 171, 200],
        "hotel": [51, 163, 255, 200],
        "train_station": [51, 163, 255, 200],
        "stadium": [54, 202, 155, 200],
        "yes": [74, 140, 247, 200]  # Default
    }
    
    return color_scheme.get(building_type, [74, 140, 247, 200])

def get_road_width(highway_type: str) -> float:
    """
    Determine a road's width based on its highway type.
    
    Args:
        highway_type (str): The highway type
        
    Returns:
        float: Width in meters
    """
    # Width for different highway types
    width_scheme = {
        "motorway": 4,
        "trunk": 3.5,
        "primary": 3,
        "secondary": 2.5,
        "tertiary": 2,
        "residential": 1.5,
        "service": 1,
        "footway": 0.5,
        "cycleway": 0.5,
        "path": 0.5,
        "track": 1,
        "unclassified": 1.5,
        "road": 1.5  # Default
    }
    
    return width_scheme.get(highway_type, 1.5)

def summarize_map_data(data: Dict[str, Any]) -> str:
    """
    Generate a summary of the map data for the user.
    
    Args:
        data (Dict[str, Any]): The processed map data
        
    Returns:
        str: A human-readable summary
    """
    if not data:
        return "No data to display. Try a different query."
    
    summary = []
    
    # Summarize buildings
    if data.get("buildings", []):
        num_buildings = len(data["buildings"])
        avg_height = sum(b["height"] for b in data["buildings"]) / num_buildings
        
        # Count building types
        building_types = {}
        for building in data["buildings"]:
            building_type = building.get("tags", {}).get("building", "unknown")
            building_types[building_type] = building_types.get(building_type, 0) + 1
        
        # Get most common types
        common_types = sorted(building_types.items(), key=lambda x: x[1], reverse=True)[:3]
        common_types_str = ", ".join([f"{t} ({c})" for t, c in common_types])
        
        summary.append(f"🏢 **{num_buildings} buildings found** with average height of {avg_height:.1f}m")
        summary.append(f"   Most common types: {common_types_str}")
    
    # Summarize roads
    if data.get("roads", []):
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
                import math
                dx = (coords[i+1][0] - coords[i][0]) * 111000 * math.cos(math.radians((coords[i+1][1] + coords[i][1])/2))
                dy = (coords[i+1][1] - coords[i][1]) * 111000
                length += math.sqrt(dx**2 + dy**2)
            total_length += length
        
        summary.append(f"🛣️ **{len(data['roads'])} roads found**, approximately {total_length/1000:.1f} km total length")
        
        # Get most common types
        common_types = sorted(road_types.items(), key=lambda x: x[1], reverse=True)[:3]
        common_types_str = ", ".join([f"{t} ({c})" for t, c in common_types])
        summary.append(f"   Most common types: {common_types_str}")
    
    # Summarize points
    if data.get("points", []):
        point_types = {}
        for point in data["points"]:
            point_type = point["type"]
            point_types[point_type] = point_types.get(point_type, 0) + 1
        
        summary.append(f"📍 **{len(data['points'])} points of interest found**")
        if point_types:
            # Get most common types
            common_types = sorted(point_types.items(), key=lambda x: x[1], reverse=True)[:3]
            common_types_str = ", ".join([f"{t} ({c})" for t, c in common_types])
            summary.append(f"   Types: {common_types_str}")
    
    # Summarize polygons
    if data.get("polygons", []):
        polygon_types = {}
        for polygon in data["polygons"]:
            polygon_type = polygon["type"]
            polygon_types[polygon_type] = polygon_types.get(polygon_type, 0) + 1
        
        summary.append(f"🔷 **{len(data['polygons'])} areas/polygons found**")
        if polygon_types:
            # Get most common types
            common_types = sorted(polygon_types.items(), key=lambda x: x[1], reverse=True)[:3]
            common_types_str = ", ".join([f"{t} ({c})" for t, c in common_types])
            summary.append(f"   Types: {common_types_str}")
    
    # Add elevation information if available
    if "terrain_elevation" in data and data["terrain_elevation"] > 0:
        summary.append(f"⛰️ **Terrain elevation**: approximately {data['terrain_elevation']:.1f}m above sea level")
    
    return "\n".join(summary)