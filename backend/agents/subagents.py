"""Subagent definitions for specialized real estate tasks."""
from typing import List
from deepagents.middleware.subagents import SubAgent
from config.subagent_prompts import (
    PROPERTY_RESEARCH_AGENT_PROMPT,
    LOCATION_ANALYSIS_AGENT_PROMPT,
    FINANCIAL_ANALYSIS_AGENT_PROMPT
)
from tools.realty_us import realty_us_search_buy, realty_us_search_rent
from tools.location import (
    geocode_address,
    osm_poi_search,
    osm_route,
    find_nearby_amenities
)
from tools.financial import (
    calculate_roi,
    estimate_mortgage,
    calculate_property_tax,
    compare_properties
)
from tools.web_scraping import scrape_property_page, extract_property_data
from tools.market_research import (
    search_market_trends,
    get_price_history,
    compare_markets
)
from config.subagent_prompts import (
    PROPERTY_RESEARCH_AGENT_PROMPT,
    LOCATION_ANALYSIS_AGENT_PROMPT,
    FINANCIAL_ANALYSIS_AGENT_PROMPT,
    DATA_EXTRACTION_AGENT_PROMPT,
    MARKET_TRENDS_AGENT_PROMPT,
    REPORT_GENERATOR_AGENT_PROMPT,
)
import logging

logger = logging.getLogger(__name__)


def get_subagents() -> List[SubAgent]:
    """
    Get list of subagent definitions.
    
    Returns:
        List of SubAgent dictionaries
    """
    subagents = [
        {
            "name": "property-research",
            "description": "Searches for properties using RealtyUS API. Use this when you need to find properties for sale or rent, search listings, or gather property data.",
            "system_prompt": PROPERTY_RESEARCH_AGENT_PROMPT,
            "tools": [
                realty_us_search_buy,
                realty_us_search_rent,
            ],
        },
        {
            "name": "location-analysis",
            "description": "Analyzes locations, neighborhoods, and points of interest. Use this when you need to find nearby amenities, calculate routes, geocode addresses, or assess neighborhood characteristics.",
            "system_prompt": LOCATION_ANALYSIS_AGENT_PROMPT,
            "tools": [
                geocode_address,
                osm_poi_search,
                osm_route,
                find_nearby_amenities,
            ],
        },
        {
            "name": "financial-analysis",
            "description": "Calculates financial metrics and investment analysis. Use this when you need ROI calculations, mortgage estimates, property tax calculations, or to compare properties financially.",
            "system_prompt": FINANCIAL_ANALYSIS_AGENT_PROMPT,
            "tools": [
                calculate_roi,
                estimate_mortgage,
                calculate_property_tax,
                compare_properties,
            ],
        },
        {
            "name": "data-extraction",
            "description": "Extracts detailed property data from web sources. Use this when you need to scrape property pages, extract data from HTML, or get detailed property information from websites like Zillow, Realtor.com, or Redfin.",
            "system_prompt": DATA_EXTRACTION_AGENT_PROMPT,
            "tools": [
                scrape_property_page,
                extract_property_data,
            ],
        },
        {
            "name": "market-trends",
            "description": "Researches and analyzes real estate market trends. Use this when you need market analysis, price history, market comparisons, or trend research for specific locations.",
            "system_prompt": MARKET_TRENDS_AGENT_PROMPT,
            "tools": [
                search_market_trends,
                get_price_history,
                compare_markets,
            ],
        },
        {
            "name": "report-generator",
            "description": "Generates comprehensive property analysis reports. Use this when you need to compile property data, location analysis, and financial metrics into a formatted report (Markdown, JSON, or HTML).",
            "system_prompt": REPORT_GENERATOR_AGENT_PROMPT,
            "tools": [],  # Uses filesystem tools from DeepAgents middleware
        },
    ]
    
    logger.info(f"Created {len(subagents)} subagents")
    return subagents
