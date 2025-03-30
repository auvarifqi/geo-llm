"""
Visualization Utilities for GeoViz3D

This module contains utilities for data visualization.
"""
import numpy as np
from typing import Dict, List, Any, Tuple, Optional

def generate_color_scale(
    min_value: float, 
    max_value: float, 
    color_range: List[List[int]] = None
) -> Dict[str, Any]:
    """
    Generate a color scale for data visualization.
    
    Args:
        min_value (float): Minimum value in the data
        max_value (float): Maximum value in the data
        color_range (List[List[int]], optional): List of RGB colors to interpolate between.
            Defaults to a blue-to-red scale.
            
    Returns:
        Dict[str, Any]: Color scale information
    """
    if color_range is None:
        # Default blue to red color scale
        color_range = [
            [65, 105, 225],   # Royal Blue
            [100, 149, 237],  # Cornflower Blue
            [135, 206, 250],  # Light Sky Blue
            [176, 224, 230],  # Powder Blue
            [255, 255, 255],  # White
            [255, 228, 196],  # Bisque
            [255, 165, 0],    # Orange
            [255, 69, 0],     # Red-Orange
            [255, 0, 0]       # Red
        ]
    
    # Convert to numpy arrays for easier manipulation
    colors = np.array(color_range)
    
    # Normalize the range
    value_range = max_value - min_value
    if value_range == 0:
        value_range = 1  # Prevent division by zero
    
    return {
        "min_value": min_value,
        "max_value": max_value,
        "colors": colors.tolist(),
        "normalize": lambda x: (x - min_value) / value_range,
        "get_color": lambda x: get_color_for_value(x, min_value, max_value, colors)
    }

def get_color_for_value(
    value: float, 
    min_value: float, 
    max_value: float, 
    colors: np.ndarray
) -> List[int]:
    """
    Get a color for a specific value based on a color scale.
    
    Args:
        value (float): The value to get a color for
        min_value (float): Minimum value in the scale
        max_value (float): Maximum value in the scale
        colors (np.ndarray): Array of RGB colors to interpolate between
        
    Returns:
        List[int]: RGBA color as [r, g, b, 255]
    """
    # Normalize the value to [0, 1]
    value_range = max_value - min_value
    if value_range == 0:
        normalized = 0.5
    else:
        normalized = (value - min_value) / value_range
    
    # Clamp to [0, 1]
    normalized = max(0, min(1, normalized))
    
    # Map to color index
    color_index = normalized * (len(colors) - 1)
    
    # Interpolate between colors
    lower_idx = int(color_index)
    upper_idx = min(lower_idx + 1, len(colors) - 1)
    
    weight = color_index - lower_idx
    
    # Linear interpolation
    color = (1 - weight) * colors[lower_idx] + weight * colors[upper_idx]
    
    # Convert to integer and add alpha
    return [int(c) for c in color] + [255]

def elevation_to_color(
    elevation: float, 
    min_elevation: float, 
    max_elevation: float
) -> List[int]:
    """
    Convert elevation to a color using a terrain color scale.
    
    Args:
        elevation (float): Elevation value
        min_elevation (float): Minimum elevation in the dataset
        max_elevation (float): Maximum elevation in the dataset
        
    Returns:
        List[int]: RGBA color as [r, g, b, a]
    """
    # Define terrain colors from low to high elevation
    terrain_colors = np.array([
        [0, 121, 107],    # Deep green (below sea level)
        [0, 151, 131],    # Middle green
        [0, 188, 163],    # Light green
        [238, 231, 176],  # Sand/beach
        [203, 166, 129],  # Light brown
        [166, 133, 93],   # Medium brown
        [127, 98, 58],    # Dark brown
        [102, 78, 46],    # Darker brown
        [255, 255, 255]   # White (snow)
    ])
    
    return get_color_for_value(elevation, min_elevation, max_elevation, terrain_colors)

def generate_heatmap_colors(
    data: List[float], 
    color_scheme: str = "viridis"
) -> List[List[int]]:
    """
    Generate colors for a heatmap visualization.
    
    Args:
        data (List[float]): Data values
        color_scheme (str, optional): Color scheme name. 
            Options: "viridis", "plasma", "inferno", "magma", "blues", "greens", "reds".
            Defaults to "viridis".
            
    Returns:
        List[List[int]]: List of RGBA colors
    """
    min_val = min(data)
    max_val = max(data)
    
    # Define color schemes
    color_schemes = {
        "viridis": [
            [68, 1, 84],
            [70, 50, 126],
            [54, 92, 141],
            [39, 127, 142],
            [31, 161, 135],
            [74, 193, 109],
            [159, 218, 57],
            [253, 231, 37]
        ],
        "plasma": [
            [13, 8, 135],
            [75, 3, 161],
            [125, 3, 168],
            [168, 34, 150],
            [203, 70, 121],
            [229, 107, 93],
            [248, 148, 65],
            [253, 195, 40],
            [240, 249, 33]
        ],
        "blues": [
            [247, 251, 255],
            [222, 235, 247],
            [198, 219, 239],
            [158, 202, 225],
            [107, 174, 214],
            [66, 146, 198],
            [33, 113, 181],
            [8, 81, 156],
            [8, 48, 107]
        ],
        "greens": [
            [247, 252, 245],
            [229, 245, 224],
            [199, 233, 192],
            [161, 217, 155],
            [116, 196, 118],
            [65, 171, 93],
            [35, 139, 69],
            [0, 109, 44],
            [0, 68, 27]
        ],
        "reds": [
            [255, 245, 240],
            [254, 224, 210],
            [252, 187, 161],
            [252, 146, 114],
            [251, 106, 74],
            [239, 59, 44],
            [203, 24, 29],
            [165, 15, 21],
            [103, 0, 13]
        ]
    }
    
    # Use viridis as fallback
    colors = color_schemes.get(color_scheme, color_schemes["viridis"])
    colors_array = np.array(colors)
    
    # Generate colors for each data point
    return [get_color_for_value(val, min_val, max_val, colors_array) for val in data]

def generate_legend(
    color_scale: Dict[str, Any], 
    num_stops: int = 5, 
    decimals: int = 1
) -> Dict[str, Any]:
    """
    Generate legend information for a color scale.
    
    Args:
        color_scale (Dict[str, Any]): Color scale information
        num_stops (int, optional): Number of legend stops. Defaults to 5.
        decimals (int, optional): Number of decimal places for labels. Defaults to 1.
        
    Returns:
        Dict[str, Any]: Legend information
    """
    min_val = color_scale["min_value"]
    max_val = color_scale["max_value"]
    
    # Generate evenly spaced values
    values = np.linspace(min_val, max_val, num_stops)
    
    # Generate colors and labels
    colors = [color_scale["get_color"](val) for val in values]
    labels = [f"{val:.{decimals}f}" for val in values]
    
    return {
        "values": values.tolist(),
        "colors": colors,
        "labels": labels
    }

def create_hillshade(
    elevation_data: np.ndarray, 
    cell_size: float = 10.0, 
    azimuth: float = 315.0, 
    altitude: float = 45.0
) -> np.ndarray:
    """
    Create a hillshade array from elevation data.
    
    Args:
        elevation_data (np.ndarray): 2D array of elevation values
        cell_size (float, optional): Cell size in meters. Defaults to 10.0.
        azimuth (float, optional): Azimuth in degrees. Defaults to 315.0.
        altitude (float, optional): Altitude in degrees. Defaults to 45.0.
        
    Returns:
        np.ndarray: 2D array of hillshade values (0-255)
    """
    # Convert angles to radians
    azimuth = np.radians(azimuth)
    altitude = np.radians(altitude)
    
    # Calculate gradients
    dx, dy = np.gradient(elevation_data, cell_size)
    
    # Calculate slope and aspect
    slope = np.arctan(np.sqrt(dx*dx + dy*dy))
    aspect = np.arctan2(-dx, dy)
    
    # Calculate hillshade
    hillshade = np.sin(altitude) * np.sin(slope) + \
                np.cos(altitude) * np.cos(slope) * np.cos(azimuth - aspect)
    
    # Scale to 0-255 and convert to uint8
    hillshade = np.uint8(255 * (hillshade + 1) / 2)
    
    return hillshade