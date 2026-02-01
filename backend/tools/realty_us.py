"""RealtyUS API tools for property search."""
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import re
import requests
from backend.config.settings import settings
from backend.utils.retry import retry_on_http_error
from backend.utils.cache import cached

# Common city name corrections (typos / nicknames -> "City Name, ST") for API
_LOCATION_NORMALIZE = {
    "san fransicso": "San Francisco, CA",
    "san francisco": "San Francisco, CA",
    "sf": "San Francisco, CA",
    "nyc": "New York, NY",
    "new york city": "New York, NY",
    "new york": "New York, NY",
    "la": "Los Angeles, CA",
    "los angeles": "Los Angeles, CA",
    "seattle": "Seattle, WA",
    "chicago": "Chicago, IL",
    "austin": "Austin, TX",
    "miami": "Miami, FL",
    "boston": "Boston, MA",
    "denver": "Denver, CO",
    "phoenix": "Phoenix, AZ",
    "dallas": "Dallas, TX",
    "houston": "Houston, TX",
    "san diego": "San Diego, CA",
    "portland": "Portland, OR",
    "las vegas": "Las Vegas, NV",
    "atlanta": "Atlanta, GA",
    "philadelphia": "Philadelphia, PA",
    "washington dc": "Washington, DC",
    "washington d.c.": "Washington, DC",
}


def _normalize_location(location: str) -> str:
    """Ensure location is in 'city:City Name, ST' format for Realty-US API."""
    raw = (location or "").strip()
    if not raw:
        return raw
    # Already in city: format
    if raw.lower().startswith("city:"):
        return raw
    # Try to match known city names (typos / nicknames)
    key = re.sub(r"\s+", " ", raw.lower()).strip()
    if key in _LOCATION_NORMALIZE:
        return "city:" + _LOCATION_NORMALIZE[key]
    # If it looks like "City, ST" or "City Name", add "city:" prefix
    if "," in raw and len(raw) <= 80:
        return "city:" + raw
    if raw and len(raw) <= 80:
        return "city:" + raw
    return raw


class RealtyUSSearchBuyInput(BaseModel):
    """Input schema for RealtyUS search buy tool."""
    location: str = Field(..., description="Search location. Use 'city:City Name, ST' (e.g. 'city:San Francisco, CA') or natural language like 'San Francisco', 'san fransicso', 'NYC'; typos and nicknames are normalized automatically.")
    resultsPerPage: Optional[int] = Field(8, ge=8, le=200, description="Number of results per page (8–200). Default is 8.")
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination. Default is 1.")
    sortBy: Optional[str] = Field('relevance', description="Sort order. One of: 'relevance', 'newest', 'lowest_price', 'highest_price', 'open_house_date', 'price_reduced', 'largest_squarefoot', 'photo_count'. Default is 'relevance'.")
    propertyType: Optional[str] = Field(None, description="Comma-separated property types. E.g., 'condo,co_op'. Options: 'condo', 'co_op', 'cond_op', 'townhome', 'single_family_home', 'multi_family', 'mobile_mfd', 'farm_ranch', 'land'.")
    prices: Optional[str] = Field(None, description="Price range as 'min,max', 'min,', or ',max'.")
    bedrooms: Optional[int] = Field(None, ge=0, le=5, description="Minimum number of bedrooms (0–5).")
    bathrooms: Optional[int] = Field(None, ge=1, le=5, description="Minimum number of bathrooms (1–5).")


@tool("realty_us_search_buy", args_schema=RealtyUSSearchBuyInput)
@cached(ttl=3600, prefix="realty_us")  # Cache for 1 hour
@retry_on_http_error(max_attempts=3)
def realty_us_search_buy(
    location: str,
    resultsPerPage: int = 8,
    page: int = 1,
    sortBy: str = 'relevance',
    propertyType: Optional[str] = None,
    prices: Optional[str] = None,
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
) -> dict:
    """
    Search for properties listed for sale in the US only, using the Realty-US API. 
    Returns a list of properties and their details.
    """
    if not settings.rapidapi_key:
        return {"error": "RAPIDAPI_KEY not configured", "results": [], "total": 0}

    location = _normalize_location(location)

    url = "https://realty-us.p.rapidapi.com/properties/search-buy"
    headers = {
        "x-rapidapi-key": settings.rapidapi_key,
        "x-rapidapi-host": "realty-us.p.rapidapi.com"
    }
    payload = {
        "location": location,
        "resultsPerPage": resultsPerPage,
        "page": page,
        "sortBy": sortBy,
        "hidePendingContingent": True,
        "hideHomesNotYetBuilt": True,
        "hideForeclosures": True
    }
    if propertyType:
        payload["propertyType"] = propertyType
    if prices:
        payload["prices"] = prices
    if bedrooms is not None:
        payload["bedrooms"] = bedrooms
    if bathrooms is not None:
        payload["bathrooms"] = bathrooms
    
    try:
        response = requests.get(url, headers=headers, params=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("data", {}).get("results", [])
        simplified = []
        for prop in results:
            address = prop.get("location", {}).get("address", {}).get("line")
            price = prop.get("list_price")
            beds = prop.get("description", {}).get("beds")
            baths = prop.get("description", {}).get("baths")
            main_photo = prop.get("primary_photo", {}).get("href")
            all_photos = [p.get("href") for p in prop.get("photos", []) if p.get("href")]
            listing_url = prop.get("href")
            coordinates = prop.get("location", {}).get("address", {}).get("coordinate")
            list_date = prop.get("list_date")
            simplified.append({
                "address": address,
                "price": price,
                "beds": beds,
                "baths": baths,
                "main_photo": main_photo,
                "all_photos": all_photos,
                "listing_url": listing_url,
                "coordinates": coordinates,
                "list_date": list_date
            })
        return {"results": simplified, "total": len(simplified)}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "results": [], "total": 0}


class RealtyUSSearchRentInput(BaseModel):
    """Input schema for RealtyUS search rent tool."""
    location: str = Field(..., description="Search location. Use 'city:City Name, ST' (e.g. 'city:San Francisco, CA') or natural language like 'San Francisco', 'san fransicso', 'NYC'; typos and nicknames are normalized automatically.")
    resultsPerPage: Optional[int] = Field(8, ge=8, le=200, description="Number of results per page (8–200). Default is 8.")
    page: Optional[int] = Field(1, ge=1, description="Page number for pagination. Default is 1.")
    sortBy: Optional[str] = Field('relevance', description="Sort order. One of: 'relevance', 'newest', 'lowest_price', 'highest_price', 'open_house_date', 'price_reduced', 'largest_squarefoot', 'photo_count'. Default is 'relevance'.")
    propertyType: Optional[str] = Field(None, description="Comma-separated property types. E.g., 'condo,co_op'. Options: 'condo', 'co_op', 'cond_op', 'townhome', 'single_family_home', 'multi_family', 'mobile_mfd', 'farm_ranch', 'land'.")
    prices: Optional[str] = Field(None, description="Price range as 'min,max', 'min,', or ',max'.")
    bedrooms: Optional[int] = Field(None, ge=0, le=5, description="Minimum number of bedrooms (0–5).")
    bathrooms: Optional[int] = Field(None, ge=1, le=5, description="Minimum number of bathrooms (1–5).")
    pets: Optional[str] = Field(None, description="Comma-separated pet options. E.g., 'cats,dogs'. Options: 'cats', 'dogs', 'no_pets_allowed'.")


@tool("realty_us_search_rent", args_schema=RealtyUSSearchRentInput)
@cached(ttl=3600, prefix="realty_us")  # Cache for 1 hour
@retry_on_http_error(max_attempts=3)
def realty_us_search_rent(
    location: str,
    resultsPerPage: int = 8,
    page: int = 1,
    sortBy: str = 'relevance',
    propertyType: Optional[str] = None,
    prices: Optional[str] = None,
    bedrooms: Optional[int] = None,
    bathrooms: Optional[int] = None,
    pets: Optional[str] = None,
) -> dict:
    """
    Search for properties listed for rent in the US only, using the Realty-US API. 
    Returns a list of rental properties and their details.
    """
    if not settings.rapidapi_key:
        return {"error": "RAPIDAPI_KEY not configured", "results": [], "total": 0}

    location = _normalize_location(location)

    url = "https://realty-us.p.rapidapi.com/properties/search-rent"
    headers = {
        "x-rapidapi-key": settings.rapidapi_key,
        "x-rapidapi-host": "realty-us.p.rapidapi.com"
    }
    payload = {
        "location": location,
        "resultsPerPage": resultsPerPage,
        "page": page,
        "sortBy": sortBy
    }
    if propertyType:
        payload["propertyType"] = propertyType
    if prices:
        payload["prices"] = prices
    if bedrooms is not None:
        payload["bedrooms"] = bedrooms
    if bathrooms is not None:
        payload["bathrooms"] = bathrooms
    if pets:
        payload["pets"] = pets
    
    try:
        response = requests.get(url, headers=headers, params=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("data", {}).get("results", [])
        simplified = []
        for prop in results:
            address = prop.get("location", {}).get("address", {}).get("line")
            price = prop.get("list_price")
            beds = prop.get("description", {}).get("beds")
            baths = prop.get("description", {}).get("baths")
            main_photo = prop.get("primary_photo", {}).get("href")
            all_photos = [p.get("href") for p in prop.get("photos", []) if p.get("href")]
            listing_url = prop.get("href")
            coordinates = prop.get("location", {}).get("address", {}).get("coordinate")
            list_date = prop.get("list_date")
            simplified.append({
                "address": address,
                "price": price,
                "beds": beds,
                "baths": baths,
                "main_photo": main_photo,
                "all_photos": all_photos,
                "listing_url": listing_url,
                "coordinates": coordinates,
                "list_date": list_date
            })
        return {"results": simplified, "total": len(simplified)}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "results": [], "total": 0}
