"""Redfin API integration for property data and price history."""
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import Optional
import requests
import logging
from backend.config.settings import settings
from backend.utils.retry import retry_on_http_error
from backend.utils.cache import cached

logger = logging.getLogger(__name__)


def _get_redfin_price_history_official(zipcode: str, address: Optional[str] = None) -> dict:
    """
    Get price history using official Redfin API (requires partnership).
    
    Args:
        zipcode: ZIP code
        address: Optional property address
    
    Returns:
        dict with price history data
    """
    if not settings.redfin_api_key:
        return {"error": "REDFIN_API_KEY not configured"}
    
    try:
        # Redfin API endpoint (actual endpoint may vary based on partnership)
        # Note: Redfin API typically uses ZIP codes as primary identifier
        
        url = "https://api.redfin.com/v1/property/price-history"
        headers = {
            "Authorization": f"Bearer {settings.redfin_api_key}",
            "Content-Type": "application/json"
        }
        params = {
            "zipcode": zipcode
        }
        if address:
            params["address"] = address
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        price_history = data.get("price_history", [])
        
        return {
            "success": True,
            "zipcode": zipcode,
            "address": address,
            "price_history": price_history,
            "data_source": "Redfin Official API"
        }
    except Exception as e:
        logger.warning(f"Redfin official API error: {e}")
        # Try alternative endpoint format
        try:
            url = "https://www.redfin.com/stingray/api/home/details/price-history"
            params = {
                "zipcode": zipcode,
                "api_key": settings.redfin_api_key
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "zipcode": zipcode,
                "address": address,
                "price_history": data.get("priceHistory", []),
                "data_source": "Redfin Official API (alternative endpoint)"
            }
        except Exception as e2:
            return {"error": f"Redfin API request failed: {str(e2)}"}


def _get_redfin_price_history_hasdata(zipcode: str) -> dict:
    """
    Get price history using HasData API as fallback.
    
    Args:
        zipcode: ZIP code
    
    Returns:
        dict with price history data
    """
    try:
        from backend.tools.web_scraping import _get_redfin_listings_hasdata
        
        hasdata_result = _get_redfin_listings_hasdata(zipcode, "forSale")
        
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
                "zipcode": zipcode,
                "price_history": price_history,
                "data_source": "HasData API (Redfin)",
                "note": "Price history from current listings. For historical data, official Redfin API partnership required."
            }
    except Exception as e:
        logger.error(f"HasData fallback error: {e}")
        return {"error": f"HasData fallback failed: {str(e)}"}


class RedfinPriceHistoryInput(BaseModel):
    """Input schema for Redfin price history."""
    zipcode: str = Field(..., description="ZIP code (e.g., '33321', '10001')")
    address: Optional[str] = Field(None, description="Optional property address for specific property")


@tool("redfin_get_price_history", args_schema=RedfinPriceHistoryInput)
@cached(ttl=86400, prefix="redfin_price_history")  # Cache for 24 hours
@retry_on_http_error(max_attempts=3)
def redfin_get_price_history(zipcode: str, address: Optional[str] = None) -> dict:
    """
    Get price history for a property or area using Redfin API.
    
    Tries official Redfin API first (if partnership available), then falls back to HasData API.
    Returns historical price data and trends.
    
    Note: Redfin API uses ZIP codes as primary identifier.
    """
    try:
        # Try official Redfin API first
        if settings.redfin_api_key:
            result = _get_redfin_price_history_official(zipcode, address)
            if "error" not in result:
                return result
            logger.info("Official Redfin API not available, trying HasData fallback")
        
        # Fallback to HasData API
        if settings.hasdata_api_key:
            result = _get_redfin_price_history_hasdata(zipcode)
            if "error" not in result:
                return result
        
        # If both fail, return error with recommendations
        return {
            "error": "Unable to get price history",
            "zipcode": zipcode,
            "address": address,
            "recommendations": [
                "Configure REDFIN_API_KEY for official Redfin API access (requires partnership)",
                "Or configure HASDATA_API_KEY for HasData API access",
                "Get Redfin API key: Contact Redfin for partnership",
                "Get HasData API key: https://api.hasdata.com/"
            ]
        }
    except Exception as e:
        logger.error(f"Redfin price history error: {e}")
        return {
            "error": f"Failed to get Redfin price history: {str(e)}",
            "zipcode": zipcode
        }
