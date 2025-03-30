"""
Geospatial Data Models for GeoViz3D

This module contains data models for geospatial data.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Union

@dataclass
class Coordinate:
    """Model for a geographic coordinate (longitude, latitude)."""
    lon: float
    lat: float
    
    def as_list(self) -> List[float]:
        """Return the coordinate as a [lon, lat] list."""
        return [self.lon, self.lat]
    
    def as_tuple(self) -> Tuple[float, float]:
        """Return the coordinate as a (lon, lat) tuple."""
        return (self.lon, self.lat)
    
    def as_dict(self) -> Dict[str, float]:
        """Return the coordinate as a dictionary."""
        return {"lon": self.lon, "lat": self.lat}

@dataclass
class BoundingBox:
    """Model for a geographic bounding box."""
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    
    def as_list(self) -> List[float]:
        """Return the bounding box as [min_lon, min_lat, max_lon, max_lat]."""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]
    
    def as_dict(self) -> Dict[str, float]:
        """Return the bounding box as a dictionary."""
        return {
            "min_lon": self.min_lon,
            "min_lat": self.min_lat,
            "max_lon": self.max_lon,
            "max_lat": self.max_lat
        }
    
    def center(self) -> Coordinate:
        """Return the center point of the bounding box."""
        return Coordinate(
            lon=(self.min_lon + self.max_lon) / 2,
            lat=(self.min_lat + self.max_lat) / 2
        )
    
    def contains(self, coord: Coordinate) -> bool:
        """Check if the bounding box contains a coordinate."""
        return (
            self.min_lon <= coord.lon <= self.max_lon and
            self.min_lat <= coord.lat <= self.max_lat
        )

@dataclass
class OSMTag:
    """Model for an OpenStreetMap tag."""
    key: str
    value: str
    
    def as_dict(self) -> Dict[str, str]:
        """Return the tag as a dictionary."""
        return {self.key: self.value}
    
    def as_tuple(self) -> Tuple[str, str]:
        """Return the tag as a (key, value) tuple."""
        return (self.key, self.value)
    
    def __str__(self) -> str:
        """String representation of the tag."""
        return f"{self.key}={self.value}"

@dataclass
class GeoFeature:
    """Base model for a geographic feature."""
    id: str
    name: str
    feature_type: str
    tags: Dict[str, str] = field(default_factory=dict)
    
    def get_tag(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a tag value by key."""
        return self.tags.get(key, default)
    
    def has_tag(self, key: str, value: Optional[str] = None) -> bool:
        """
        Check if the feature has a tag.
        
        Args:
            key (str): Tag key to check
            value (Optional[str], optional): Tag value to check. If None, only checks for key existence.
        
        Returns:
            bool: True if the feature has the tag (and value if specified)
        """
        if key not in self.tags:
            return False
        if value is None:
            return True
        return self.tags[key] == value

@dataclass
class Point(GeoFeature):
    """Model for a point feature."""
    coordinate: Coordinate
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the point as a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.feature_type,
            "coordinates": self.coordinate.as_list(),
            "tags": self.tags
        }

@dataclass
class Road(GeoFeature):
    """Model for a road feature."""
    coordinates: List[Coordinate]
    width: float = 1.0
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the road as a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.feature_type,
            "coordinates": [coord.as_list() for coord in self.coordinates],
            "width": self.width,
            "tags": self.tags
        }
    
    def get_length(self) -> float:
        """
        Calculate the approximate length of the road in meters.
        
        Note: This is a simple approximation that doesn't account for Earth's curvature
        for short distances.
        """
        if len(self.coordinates) < 2:
            return 0
        
        import math
        length = 0
        for i in range(len(self.coordinates) - 1):
            # Convert to radians
            lon1, lat1 = map(math.radians, self.coordinates[i].as_tuple())
            lon2, lat2 = map(math.radians, self.coordinates[i + 1].as_tuple())
            
            # Haversine formula
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            r = 6371000  # Earth radius in meters
            segment_length = c * r
            
            length += segment_length
        
        return length

@dataclass
class Building(GeoFeature):
    """Model for a building feature."""
    coordinates: List[Coordinate]
    height: float = 8.0
    color: List[int] = field(default_factory=lambda: [74, 140, 247, 200])
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the building as a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.feature_type,
            "coordinates": [coord.as_list() for coord in self.coordinates],
            "height": self.height,
            "color": self.color,
            "tags": self.tags
        }
    
    def get_footprint_area(self) -> float:
        """
        Calculate the approximate area of the building footprint in square meters.
        
        Note: This is a simple approximation that doesn't account for Earth's curvature.
        """
        if len(self.coordinates) < 3:
            return 0
        
        # Convert to a local coordinate system (meters)
        # Assuming first point as origin
        origin = self.coordinates[0]
        
        # Approximate conversion factors (1 degree ~ 111km at equator)
        import math
        lat_factor = 111000  # meters per degree of latitude
        lon_factor = 111000 * math.cos(math.radians(origin.lat))  # meters per degree of longitude
        
        local_coords = []
        for coord in self.coordinates:
            x = (coord.lon - origin.lon) * lon_factor
            y = (coord.lat - origin.lat) * lat_factor
            local_coords.append((x, y))
        
        # Calculate area using Shoelace formula
        area = 0
        n = len(local_coords)
        for i in range(n):
            j = (i + 1) % n
            area += local_coords[i][0] * local_coords[j][1]
            area -= local_coords[j][0] * local_coords[i][1]
        
        return abs(area) / 2

@dataclass
class Polygon(GeoFeature):
    """Model for a polygon feature."""
    coordinates: List[Coordinate]
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the polygon as a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.feature_type,
            "coordinates": [coord.as_list() for coord in self.coordinates],
            "tags": self.tags
        }

@dataclass
class GeoDataCollection:
    """Collection of geographic features."""
    buildings: List[Building] = field(default_factory=list)
    roads: List[Road] = field(default_factory=list)
    points: List[Point] = field(default_factory=list)
    polygons: List[Polygon] = field(default_factory=list)
    terrain_elevation: float = 0.0
    
    def get_bounds(self) -> BoundingBox:
        """Calculate the bounding box of all features."""
        all_coords = []
        
        # Collect all coordinates
        for building in self.buildings:
            all_coords.extend(building.coordinates)
        for road in self.roads:
            all_coords.extend(road.coordinates)
        for point in self.points:
            all_coords.append(point.coordinate)
        for polygon in self.polygons:
            all_coords.extend(polygon.coordinates)
        
        if not all_coords:
            # Default to a small area around (0, 0) if no coordinates
            return BoundingBox(
                min_lon=-0.01,
                min_lat=-0.01,
                max_lon=0.01,
                max_lat=0.01
            )
        
        # Find min/max values
        min_lon = min(coord.lon for coord in all_coords)
        min_lat = min(coord.lat for coord in all_coords)
        max_lon = max(coord.lon for coord in all_coords)
        max_lat = max(coord.lat for coord in all_coords)
        
        return BoundingBox(
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat
        )
    
    def get_center(self) -> Coordinate:
        """Get the center point of all features."""
        return self.get_bounds().center()
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert the collection to a dictionary."""
        return {
            "buildings": [building.as_dict() for building in self.buildings],
            "roads": [road.as_dict() for road in self.roads],
            "points": [point.as_dict() for point in self.points],
            "polygons": [polygon.as_dict() for polygon in self.polygons],
            "terrain_elevation": self.terrain_elevation
        }
    
    def filter_by_tags(self, tags: Dict[str, str]) -> 'GeoDataCollection':
        """
        Filter features by tags.
        
        Args:
            tags (Dict[str, str]): Tags to filter by (all must match)
            
        Returns:
            GeoDataCollection: New collection with filtered features
        """
        result = GeoDataCollection(terrain_elevation=self.terrain_elevation)
        
        # Helper function to check if a feature matches all tags
        def matches_tags(feature_tags: Dict[str, str]) -> bool:
            return all(
                key in feature_tags and feature_tags[key] == value
                for key, value in tags.items()
            )
        
        # Filter each feature type
        result.buildings = [b for b in self.buildings if matches_tags(b.tags)]
        result.roads = [r for r in self.roads if matches_tags(r.tags)]
        result.points = [p for p in self.points if matches_tags(p.tags)]
        result.polygons = [p for p in self.polygons if matches_tags(p.tags)]
        
        return result
    
    def filter_by_bounds(self, bounds: BoundingBox) -> 'GeoDataCollection':
        """
        Filter features by bounding box.
        
        Args:
            bounds (BoundingBox): Bounding box to filter by
            
        Returns:
            GeoDataCollection: New collection with filtered features
        """
        result = GeoDataCollection(terrain_elevation=self.terrain_elevation)
        
        # Helper function to check if a coordinate is within bounds
        def in_bounds(coord: Coordinate) -> bool:
            return bounds.contains(coord)
        
        # Helper function to check if any coordinate of a feature is within bounds
        def any_in_bounds(coords: List[Coordinate]) -> bool:
            return any(in_bounds(coord) for coord in coords)
        
        # Filter each feature type
        result.buildings = [b for b in self.buildings if any_in_bounds(b.coordinates)]
        result.roads = [r for r in self.roads if any_in_bounds(r.coordinates)]
        result.points = [p for p in self.points if in_bounds(p.coordinate)]
        result.polygons = [p for p in self.polygons if any_in_bounds(p.coordinates)]
        
        return result