"""Location analysis tools using OpenStreetMap and geocoding services."""

from pydantic import BaseModel, Field
from langchain_core.tools import tool
import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GeocodeInput(BaseModel):
    """Input schema for geocoding."""

    address: str = Field(
        ...,
        description="The address or place name to geocode (e.g., '123 Main St, San Francisco, CA')",
    )


@tool("geocode_address", args_schema=GeocodeInput)
def geocode_address(address: str) -> dict:
    """
    Geocode an address or place name using OpenStreetMap Nominatim API.
    Returns latitude, longitude, and display name.
    """
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
        headers = {"User-Agent": "EnterpriseRealEstateAI/1.0"}
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            if data:
                result = data[0]
                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "display_name": result["display_name"],
                }

        # Try with more specific parameters
        url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=5&addressdetails=1"
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            if data:
                result = data[0]
                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "display_name": result["display_name"],
                }

        return {"error": "No results found for the given address"}
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return {"error": f"Geocoding failed: {str(e)}"}


class RouteInput(BaseModel):
    """Input schema for route calculation."""

    start_lat: float = Field(..., description="Start latitude")
    start_lon: float = Field(..., description="Start longitude")
    end_lat: float = Field(..., description="End latitude")
    end_lon: float = Field(..., description="End longitude")
    mode: str = Field(
        "driving", description="Mode of transport: 'driving', 'walking', or 'cycling'"
    )


@tool("osm_route", args_schema=RouteInput)
def osm_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    mode: str = "driving",
) -> dict:
    """
    Get a route between two points using OSRM (Open Source Routing Machine).
    Returns distance, duration, and route geometry for map display.
    """
    try:
        url = f"https://router.project-osrm.org/route/v1/{mode}/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            return {"error": f"OSRM API error: {resp.status_code}"}

        data = resp.json()
        if not data.get("routes"):
            return {"error": "No route found"}

        route = data["routes"][0]
        return {
            "distance_m": route["distance"],
            "duration_s": route["duration"],
            "distance_km": round(route["distance"] / 1000, 2),
            "duration_min": round(route["duration"] / 60, 1),
            "geometry": route["geometry"],
        }
    except Exception as e:
        logger.error(f"Route calculation error: {e}")
        return {"error": f"Route calculation failed: {str(e)}"}


class POISearchInput(BaseModel):
    """Input schema for POI search."""

    key: str = Field(
        ..., description="OSM key, e.g., 'amenity', 'tourism', 'shop', 'building'"
    )
    value: str = Field(
        ...,
        description="OSM value, e.g., 'restaurant', 'hotel', 'supermarket', 'school'",
    )
    lat: float = Field(..., description="Latitude of center point")
    lon: float = Field(..., description="Longitude of center point")
    radius: int = Field(1000, description="Search radius in meters (default: 1000)")


@tool("osm_poi_search", args_schema=POISearchInput)
def osm_poi_search(
    key: str, value: str, lat: float, lon: float, radius: int = 1000
) -> dict:
    """
    Search for points of interest (POIs) of a given type within a radius of a point using Overpass API.
    Useful for finding nearby amenities like restaurants, schools, parks, etc.
    """
    try:
        query = f"""
        [out:json][timeout:25];
        node["{key}"="{value}"](around:{radius},{lat},{lon});
        out body;
        """
        url = "https://overpass-api.de/api/interpreter"
        resp = requests.post(url, data={"data": query}, timeout=30)

        if resp.status_code != 200:
            return {"error": f"Overpass API error: {resp.status_code}"}

        data = resp.json()
        pois = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            pois.append(
                {
                    "lat": float(el["lat"]),
                    "lon": float(el["lon"]),
                    "name": tags.get("name", "Unnamed"),
                    "type": value,
                    "tags": tags,
                }
            )

        return {
            "pois": pois,
            "count": len(pois),
            "center": {"lat": lat, "lon": lon},
            "radius_m": radius,
        }
    except Exception as e:
        logger.error(f"POI search error: {e}")
        return {"error": f"POI search failed: {str(e)}"}


class NearbyAmenitiesInput(BaseModel):
    """Input schema for finding nearby amenities."""

    lat: float = Field(..., description="Latitude of center point")
    lon: float = Field(..., description="Longitude of center point")
    radius: int = Field(1000, description="Search radius in meters")
    categories: Optional[str] = Field(
        None,
        description="Comma-separated categories: 'restaurants', 'schools', 'parks', 'shopping', 'transit'",
    )


@tool("find_nearby_amenities", args_schema=NearbyAmenitiesInput)
def find_nearby_amenities(
    lat: float, lon: float, radius: int = 1000, categories: Optional[str] = None
) -> dict:
    """
    Find nearby amenities around a location. Searches for common amenities like restaurants, schools, parks, etc.
    """
    amenity_mapping = {
        "restaurants": ("amenity", "restaurant"),
        "schools": ("amenity", "school"),
        "parks": ("leisure", "park"),
        "shopping": ("shop", "supermarket"),
        "transit": ("public_transport", "station"),
        "hospitals": ("amenity", "hospital"),
        "gas_stations": ("amenity", "fuel"),
    }

    results = {}

    if categories:
        search_categories = [c.strip() for c in categories.split(",")]
    else:
        # Default: search all common amenities
        search_categories = list(amenity_mapping.keys())

    for category in search_categories:
        if category in amenity_mapping:
            key, value = amenity_mapping[category]
            poi_result = osm_poi_search.invoke(
                {"key": key, "value": value, "lat": lat, "lon": lon, "radius": radius}
            )
            if "pois" in poi_result:
                results[category] = poi_result["pois"][:10]  # Limit to 10 per category

    return {
        "location": {"lat": lat, "lon": lon},
        "radius_m": radius,
        "amenities": results,
        "summary": {cat: len(pois) for cat, pois in results.items()},
    }
