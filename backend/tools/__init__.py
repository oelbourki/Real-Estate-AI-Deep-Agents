"""Real estate tools package."""

# Import all tools for easy access
from .realty_us import realty_us_search_buy, realty_us_search_rent
from .location import geocode_address, osm_route, osm_poi_search, find_nearby_amenities
from .financial import (
    calculate_roi,
    estimate_mortgage,
    calculate_property_tax,
    compare_properties,
)
from .web_scraping import (
    scrape_property_page,
    extract_property_data,
    search_zillow_listings,
    search_redfin_listings,
)
from .zillow_api import zillow_get_price_history
from .redfin_api import redfin_get_price_history

__all__ = [
    # RealtyUS
    "realty_us_search_buy",
    "realty_us_search_rent",
    # Location
    "geocode_address",
    "osm_route",
    "osm_poi_search",
    "find_nearby_amenities",
    # Financial
    "calculate_roi",
    "estimate_mortgage",
    "calculate_property_tax",
    "compare_properties",
    # Web Scraping
    "scrape_property_page",
    "extract_property_data",
    "search_zillow_listings",
    "search_redfin_listings",
    # Zillow/Redfin APIs
    "zillow_get_price_history",
    "redfin_get_price_history",
]
