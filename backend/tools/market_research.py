"""Market research and trends analysis tools."""
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import Optional
import logging
from datetime import datetime, timedelta
import requests
from backend.config.settings import settings
from backend.utils.retry import retry_on_http_error
from backend.utils.cache import cached

logger = logging.getLogger(__name__)

# Try to import Tavily client
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    TavilyClient = None


class SearchMarketTrendsInput(BaseModel):
    """Input schema for market trends search."""
    location: str = Field(..., description="Location to research (e.g., 'San Francisco, CA')")
    timeframe: Optional[str] = Field("1 year", description="Timeframe for trends (e.g., '1 year', '6 months', '2 years')")
    topic: Optional[str] = Field(None, description="Specific topic (e.g., 'home prices', 'rental rates', 'inventory')")


@tool("search_market_trends", args_schema=SearchMarketTrendsInput)
@cached(ttl=3600, prefix="market_trends")  # Cache for 1 hour
@retry_on_http_error(max_attempts=3)
def search_market_trends(location: str, timeframe: str = "1 year", topic: Optional[str] = None) -> dict:
    """
    Search for real estate market trends and analysis for a specific location.
    Returns market insights, price trends, and market conditions.
    
    Uses Tavily API for web search if available, otherwise falls back to placeholder.
    """
    try:
        # Try Tavily API first (recommended)
        if TAVILY_AVAILABLE and settings.tavily_api_key:
            try:
                client = TavilyClient(api_key=settings.tavily_api_key)
                
                # Build search query
                query = f"real estate market trends {location}"
                if topic:
                    query += f" {topic}"
                if timeframe:
                    query += f" {timeframe}"
                
                # Search with Tavily
                response = client.search(
                    query=query,
                    search_depth="advanced",  # Use "basic" for faster results
                    max_results=10
                )
                
                # Extract and structure results
                results = response.get("results", [])
                trends = []
                for result in results:
                    trends.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", "")[:500],  # First 500 chars
                        "score": result.get("score", 0)
                    })
                
                # Extract key insights from results
                price_trend = "stable"
                inventory_trend = "normal"
                days_on_market = "unknown"
                
                # Try to extract insights from content (simplified)
                all_content = " ".join([t.get("content", "") for t in trends])
                if any(word in all_content.lower() for word in ["rising", "increasing", "up", "growth"]):
                    price_trend = "rising"
                elif any(word in all_content.lower() for word in ["falling", "decreasing", "down", "decline"]):
                    price_trend = "falling"
                
                return {
                    "location": location,
                    "timeframe": timeframe,
                    "topic": topic or "general market trends",
                    "query": query,
                    "trends": trends,
                    "total_results": len(trends),
                    "data_source": "Tavily API",
                    "market_indicators": {
                        "price_trend": price_trend,
                        "inventory_trend": inventory_trend,
                        "days_on_market": days_on_market,
                    },
                    "summary": f"Found {len(trends)} relevant market trend articles for {location}"
                }
            except Exception as tavily_error:
                logger.warning(f"Tavily API error: {tavily_error}. Falling back to placeholder.")
        
        # Fallback: Try Serper API if available
        if settings.serper_api_key:
            try:
                query = f"real estate market trends {location}"
                if topic:
                    query += f" {topic}"
                if timeframe:
                    query += f" {timeframe}"
                
                url = "https://google.serper.dev/search"
                headers = {
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json"
                }
                payload = {"q": query, "num": 10}
                
                response = requests.post(url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                trends = []
                for item in data.get("organic", []):
                    trends.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "content": item.get("snippet", ""),
                        "score": 0.8  # Default score for Serper
                    })
                
                return {
                    "location": location,
                    "timeframe": timeframe,
                    "topic": topic or "general market trends",
                    "query": query,
                    "trends": trends,
                    "total_results": len(trends),
                    "data_source": "Serper API",
                    "market_indicators": {
                        "price_trend": "unknown",
                        "inventory_trend": "unknown",
                        "days_on_market": "unknown",
                    },
                    "summary": f"Found {len(trends)} relevant market trend articles for {location}"
                }
            except Exception as serper_error:
                logger.warning(f"Serper API error: {serper_error}. Falling back to placeholder.")
        
        # Fallback: Placeholder implementation
        search_query = f"real estate market trends {location}"
        if topic:
            search_query += f" {topic}"
        if timeframe:
            search_query += f" {timeframe}"
        
        result = {
            "location": location,
            "timeframe": timeframe,
            "topic": topic or "general market trends",
            "search_query": search_query,
            "trends": [],
            "total_results": 0,
            "data_source": "placeholder",
            "market_indicators": {
                "price_trend": "unknown",
                "inventory_trend": "unknown",
                "days_on_market": "unknown",
            },
            "recommendations": [
                "Configure TAVILY_API_KEY for market trends search",
                "Or configure SERPER_API_KEY as alternative",
                "Get Tavily API key: https://tavily.com/",
                "Get Serper API key: https://serper.dev/"
            ],
            "note": "This is a placeholder. Configure TAVILY_API_KEY or SERPER_API_KEY for actual market trends."
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Market trends search error: {e}")
        return {
            "error": f"Failed to search market trends: {str(e)}",
            "location": location
        }


class GetPriceHistoryInput(BaseModel):
    """Input schema for price history."""
    address: str = Field(..., description="Property address")
    location: Optional[str] = Field(None, description="Location (city, state) for area price history")


@tool("get_price_history", args_schema=GetPriceHistoryInput)
@cached(ttl=86400, prefix="price_history")  # Cache for 24 hours
@retry_on_http_error(max_attempts=3)
def get_price_history(address: str, location: Optional[str] = None) -> dict:
    """
    Get price history for a property or area.
    Returns historical price data and trends.
    
    Uses web scraping approach since Zillow/Redfin APIs require partnerships.
    """
    try:
        # Try Zillow API if partnership available
        if settings.zillow_api_key:
            try:
                # Zillow API endpoint (example - actual endpoint may vary)
                url = "https://api.zillow.com/v1/GetPriceHistory"
                params = {
                    "zws-id": settings.zillow_api_key,
                    "address": address,
                    "citystatezip": location or ""
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                price_history = data.get("price_history", [])
                
                return {
                    "address": address,
                    "location": location,
                    "price_history": price_history,
                    "data_source": "Zillow API"
                }
            except Exception as zillow_error:
                logger.warning(f"Zillow API error: {zillow_error}. Falling back to web scraping.")
        
        # Fallback: Use web scraping (will be enhanced in web_scraping.py)
        # For now, return placeholder with instructions
        result = {
            "address": address,
            "location": location,
            "price_history": {
                "note": "Price history requires web scraping implementation",
                "suggested_approach": "Use scrape_property_page tool with Zillow/Redfin URLs",
                "example": f"scrape_property_page('https://www.zillow.com/homes/{address.replace(' ', '-')}', source='zillow')"
            },
            "area_trends": {
                "note": "Use market data APIs for neighborhood price trends"
            },
            "recommendations": [
                "Use scrape_property_page tool to get property data",
                "Configure SCRAPERAPI_KEY for reliable scraping",
                "Or use Zillow API if partnership is available"
            ],
            "data_source": "placeholder"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Price history error: {e}")
        return {
            "error": f"Failed to get price history: {str(e)}",
            "address": address
        }


class CompareMarketsInput(BaseModel):
    """Input schema for comparing multiple markets."""
    locations: str = Field(..., description="Comma-separated list of locations to compare")


@tool("compare_markets", args_schema=CompareMarketsInput)
@cached(ttl=3600, prefix="market_comparison")  # Cache for 1 hour
@retry_on_http_error(max_attempts=3)
def compare_markets(locations: str) -> dict:
    """
    Compare real estate markets across multiple locations.
    Returns comparative analysis of market conditions.
    
    Uses Tavily API to search for market data for each location.
    """
    try:
        location_list = [loc.strip() for loc in locations.split(",")]
        
        if len(location_list) < 2:
            return {"error": "Please provide at least 2 locations to compare"}
        
        comparisons = {}
        
        # Try Tavily API first
        if TAVILY_AVAILABLE and settings.tavily_api_key:
            try:
                client = TavilyClient(api_key=settings.tavily_api_key)
                
                for location in location_list:
                    # Search for market data for each location
                    query = f"real estate market data {location} median home price inventory days on market"
                    response = client.search(query=query, max_results=5, search_depth="basic")
                    
                    results = response.get("results", [])
                    market_data = []
                    for result in results:
                        market_data.append({
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "content": result.get("content", "")[:300],
                            "score": result.get("score", 0)
                        })
                    
                    comparisons[location] = {
                        "market_data": market_data,
                        "query": query,
                        "results_count": len(market_data)
                    }
                
                return {
                    "locations": location_list,
                    "comparisons": comparisons,
                    "data_source": "Tavily API",
                    "summary": f"Compared {len(location_list)} markets using Tavily API"
                }
            except Exception as tavily_error:
                logger.warning(f"Tavily API error: {tavily_error}. Falling back to placeholder.")
        
        # Fallback: Try Serper API
        if settings.serper_api_key:
            try:
                for location in location_list:
                    query = f"real estate market data {location} median home price"
                    url = "https://google.serper.dev/search"
                    headers = {
                        "X-API-KEY": settings.serper_api_key,
                        "Content-Type": "application/json"
                    }
                    payload = {"q": query, "num": 5}
                    
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    market_data = []
                    for item in data.get("organic", []):
                        market_data.append({
                            "title": item.get("title", ""),
                            "url": item.get("link", ""),
                            "content": item.get("snippet", ""),
                            "score": 0.8
                        })
                    
                    comparisons[location] = {
                        "market_data": market_data,
                        "query": query,
                        "results_count": len(market_data)
                    }
                
                return {
                    "locations": location_list,
                    "comparisons": comparisons,
                    "data_source": "Serper API",
                    "summary": f"Compared {len(location_list)} markets using Serper API"
                }
            except Exception as serper_error:
                logger.warning(f"Serper API error: {serper_error}. Falling back to placeholder.")
        
        # Fallback: Placeholder
        result = {
            "locations": location_list,
            "comparisons": {
                loc: {
                    "market_data": [],
                    "note": "Configure TAVILY_API_KEY or SERPER_API_KEY for market comparisons"
                }
                for loc in location_list
            },
            "data_source": "placeholder",
            "recommendations": [
                "Configure TAVILY_API_KEY for market comparisons",
                "Or configure SERPER_API_KEY as alternative",
                "Get Tavily API key: https://tavily.com/",
                "Get Serper API key: https://serper.dev/"
            ],
            "note": "This is a placeholder. Configure TAVILY_API_KEY or SERPER_API_KEY for actual market comparisons."
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Market comparison error: {e}")
        return {
            "error": f"Failed to compare markets: {str(e)}",
            "locations": locations
        }
