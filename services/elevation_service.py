"""
Elevation Data Service for GeoViz3D

This module handles fetching and processing elevation data.
"""
import requests
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

# Import configuration
from config.settings import (
    ELEVATION_API_URL,
    API_TIMEOUT,
    MAX_RETRIES,
    MAX_ELEVATION_POINTS,
    ENABLE_CACHE
)

# Set up logging
logger = logging.getLogger(__name__)

# Simple in-memory cache
if ENABLE_CACHE:
    elevation_cache = {}

def get_elevation_data(coords_list: List[Tuple[float, float]]) -> List[float]:
    """
    Get elevation data for a list of coordinates.
    
    Args:
        coords_list (List[Tuple[float, float]]): List of coordinates as (lon, lat) tuples
        
    Returns:
        List[float]: List of elevations in meters, or zeros if data couldn't be fetched
    """
    if not coords_list:
        return []

    # Limit the number of points to request to avoid overloading the API
    # and to stay within typical API limits
    if len(coords_list) > MAX_ELEVATION_POINTS:
        logger.warning(f"Limiting elevation request to {MAX_ELEVATION_POINTS} points (from {len(coords_list)})")
        
        # Sample points from the full list
        indices = np.linspace(0, len(coords_list) - 1, MAX_ELEVATION_POINTS, dtype=int)
        coords_list = [coords_list[i] for i in indices]

    # Check cache for each point
    elevations = []
    coords_to_fetch = []
    coords_indices = []

    for i, coord in enumerate(coords_list):
        cache_key = f"{coord[0]:.5f},{coord[1]:.5f}"
        if ENABLE_CACHE and cache_key in elevation_cache:
            elevations.append(elevation_cache[cache_key])
        else:
            # Mark this coordinate for fetching
            elevations.append(None)
            coords_to_fetch.append(coord)
            coords_indices.append(i)

    # If we have coordinates to fetch
    if coords_to_fetch:
        try:
            # Prepare the request payload
            locations = [{"latitude": lat, "longitude": lon} for lon, lat in coords_to_fetch]
            payload = {"locations": locations}
            
            # Make the request
            response = requests.post(ELEVATION_API_URL, json=payload, timeout=API_TIMEOUT)
            response.raise_for_status()
            
            # Extract the elevation data
            results = response.json().get("results", [])
            
            # Update elevations and cache
            for i, result in enumerate(results):
                elevation = result.get("elevation", 0)
                original_idx = coords_indices[i]
                elevations[original_idx] = elevation
                
                # Cache the result
                if ENABLE_CACHE:
                    coord = coords_to_fetch[i]
                    cache_key = f"{coord[0]:.5f},{coord[1]:.5f}"
                    elevation_cache[cache_key] = elevation
                
        except Exception as e:
            logger.warning(f"Could not fetch elevation data: {str(e)}")
            # Fill in with zeros for points we couldn't fetch
            for i in range(len(elevations)):
                if elevations[i] is None:
                    elevations[i] = 0

    # Replace any remaining None values with zeros
    elevations = [0 if e is None else e for e in elevations]
    
    return elevations

def get_terrain_profile(
    start_point: Tuple[float, float], 
    end_point: Tuple[float, float], 
    num_points: int = 50
) -> Dict[str, Any]:
    """
    Get a terrain elevation profile between two points.
    
    Args:
        start_point (Tuple[float, float]): Starting point as (lon, lat)
        end_point (Tuple[float, float]): Ending point as (lon, lat)
        num_points (int, optional): Number of points to sample. Defaults to 50.
        
    Returns:
        Dict[str, Any]: Dictionary with points and elevations
    """
    # Generate points along the line
    start_lon, start_lat = start_point
    end_lon, end_lat = end_point
    
    lons = np.linspace(start_lon, end_lon, num_points)
    lats = np.linspace(start_lat, end_lat, num_points)
    
    points = [(lon, lat) for lon, lat in zip(lons, lats)]
    
    # Get elevations
    elevations = get_elevation_data(points)
    
    # Calculate distances
    distances = [0]
    total_distance = 0
    
    for i in range(1, len(points)):
        prev_lon, prev_lat = points[i-1]
        curr_lon, curr_lat = points[i]
        
        # Simple approximation - for more accuracy, use haversine formula
        # This is a rough approximation assuming 1 degree = 111km
        dx = (curr_lon - prev_lon) * 111000 * np.cos(np.radians(curr_lat))
        dy = (curr_lat - prev_lat) * 111000
        
        segment_distance = np.sqrt(dx**2 + dy**2)
        total_distance += segment_distance
        distances.append(total_distance)
    
    return {
        "points": points,
        "elevations": elevations,
        "distances": distances,
        "total_distance": total_distance,
        "min_elevation": min(elevations),
        "max_elevation": max(elevations),
        "elevation_gain": sum(max(0, elevations[i] - elevations[i-1]) for i in range(1, len(elevations))),
        "elevation_loss": sum(max(0, elevations[i-1] - elevations[i]) for i in range(1, len(elevations)))
    }

def get_area_elevation_grid(
    bounds: Tuple[float, float, float, float],
    resolution: int = 20
) -> Dict[str, Any]:
    """
    Get a grid of elevation data for an area.
    
    Args:
        bounds (Tuple[float, float, float, float]): Bounds as (min_lon, min_lat, max_lon, max_lat)
        resolution (int, optional): Number of points in each dimension. Defaults to 20.
        
    Returns:
        Dict[str, Any]: Dictionary with grid data
    """
    min_lon, min_lat, max_lon, max_lat = bounds
    
    # Generate grid points
    lons = np.linspace(min_lon, max_lon, resolution)
    lats = np.linspace(min_lat, max_lat, resolution)
    
    grid_points = []
    for lat in lats:
        for lon in lons:
            grid_points.append((lon, lat))
    
    # Get elevations
    elevations = get_elevation_data(grid_points)
    
    # Reshape to grid
    elevation_grid = np.array(elevations).reshape((resolution, resolution))
    
    return {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat,
        "resolution": resolution,
        "points": grid_points,
        "elevations": elevations,
        "elevation_grid": elevation_grid.tolist(),
        "min_elevation": min(elevations),
        "max_elevation": max(elevations)
    }