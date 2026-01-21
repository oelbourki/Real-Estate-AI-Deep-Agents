"""Zillow API integration for property data and price history."""
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import Optional
import requests
import logging
from backend.config.settings import settings
from backend.utils.retry import retry_on_http_error
from backend.utils.cache import cached

logger = logging.getLogger(__name__)


def _get_zillow_price_history_official(address: str, citystatezip: str) -> dict:
    """
    Get price history using official Zillow API (requires partnership).
    
    Args:
        address: Property address
        citystatezip: City, state, ZIP code
    
    Returns:
        dict with price history data
    """
    if not settings.zillow_api_key:
        return {"error": "ZILLOW_API_KEY not configured"}
    
    try:
        # Zillow API endpoint (actual endpoint may vary based on partnership)
        # Common endpoints:
        # - GetDeepSearchResults
        # - GetUpdatedPropertyDetails
        # - GetPriceHistory (if available)
        
        url = "https://www.zillow.com/webservice/GetPriceHistory.htm"
        params = {
            "zws-id": settings.zillow_api_key,
            "address": address,
            "citystatezip": citystatezip
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse XML response (Zillow API returns XML)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # Extract price history
        price_history = []
        for event in root.findall(".//event"):
            price_history.append({
                "date": event.get("date"),
                "price": event.get("price"),
                "event_type": event.get("type")
            })
        
        return {
            "success": True,
            "address": address,
            "citystatezip": citystatezip,
            "price_history": price_history,
            "data_source": "Zillow Official API"
        }
    except Exception as e:
        logger.warning(f"Zillow official API error: {e}")
        return {"error": f"Zillow API request failed: {str(e)}"}


def _get_zillow_price_history_hasdata(location: str) -> dict:
    """
    Get price history using HasData API as fallback.
    
    Args:
        location: Location (city, state)
    
    Returns:
        dict with price history data
    """
    try:
        from backend.tools.web_scraping import _get_zillow_listings_hasdata
        
        hasdata_result = _get_zillow_listings_hasdata(location, "forSale")
        
        if "error" not in hasdata_result and hasdata_result.get("success"):
            data = hasdata_result.get("data", {})
            listings = data.get("listings", []) if isinstance(data, dict) else []
            if isinstance(data, list):
                listings = data
            
            price_history = []
            for listing in listings:
                if listing.get("price") or listing.get("list_price"):
                    price_history.append({
                        "date": listing.get("list_date") or listing.get("date"),
                        "price": listing.get("price") or listing.get("list_price"),
                        "address": listing.get("address") or listing.get("street_address"),
                        "event_type": "listing"
                    })
            
            return {
                "success": True,
                "location": location,
                "price_history": price_history,
                "data_source": "HasData API (Zillow)",
                "note": "Price history from current listings. For historical data, official Zillow API partnership required."
            }
    except Exception as e:
        logger.error(f"HasData fallback error: {e}")
        return {"error": f"HasData fallback failed: {str(e)}"}


class ZillowPriceHistoryInput(BaseModel):
    """Input schema for Zillow price history."""
    address: str = Field(..., description="Property address")
    citystatezip: Optional[str] = Field(None, description="City, state, ZIP code (e.g., 'San Francisco, CA 94102')")
    location: Optional[str] = Field(None, description="Location (city, state) as fallback if citystatezip not provided")


@tool("zillow_get_price_history", args_schema=ZillowPriceHistoryInput)
@cached(ttl=86400, prefix="zillow_price_history")  # Cache for 24 hours
@retry_on_http_error(max_attempts=3)
def zillow_get_price_history(address: str, citystatezip: Optional[str] = None, location: Optional[str] = None) -> dict:
    """
    Get price history for a property using Zillow API.
    
    Tries official Zillow API first (if partnership available), then falls back to HasData API.
    Returns historical price data and trends.
    """
    try:
        # Try official Zillow API first
        if settings.zillow_api_key and citystatezip:
            result = _get_zillow_price_history_official(address, citystatezip)
            if "error" not in result:
                return result
            logger.info("Official Zillow API not available, trying HasData fallback")
        
        # Fallback to HasData API
        if settings.hasdata_api_key:
            fallback_location = citystatezip or location or address
            result = _get_zillow_price_history_hasdata(fallback_location)
            if "error" not in result:
                return result
        
        # If both fail, return error with recommendations
        return {
            "error": "Unable to get price history",
            "address": address,
            "recommendations": [
                "Configure ZILLOW_API_KEY for official Zillow API access (requires partnership)",
                "Or configure HASDATA_API_KEY for HasData API access",
                "Get Zillow API key: Contact Zillow for partnership",
                "Get HasData API key: https://api.hasdata.com/"
            ]
        }
    except Exception as e:
        logger.error(f"Zillow price history error: {e}")
        return {
            "error": f"Failed to get Zillow price history: {str(e)}",
            "address": address
        }
