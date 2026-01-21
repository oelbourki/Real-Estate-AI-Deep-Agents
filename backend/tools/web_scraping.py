"""Web scraping tools for property data extraction."""
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from typing import Optional
import requests
import logging
from bs4 import BeautifulSoup
import json
import re
from backend.config.settings import settings
from backend.utils.retry import retry_on_http_error
from backend.utils.cache import cached

logger = logging.getLogger(__name__)


def _get_zillow_listings_hasdata(keyword: str, listing_type: str = "forSale") -> dict:
    """
    Get Zillow listings using HasData API.
    
    Args:
        keyword: Location keyword (e.g., "New York, NY")
        listing_type: "forSale" or "forRent"
    
    Returns:
        dict with listings data
    """
    if not settings.hasdata_api_key:
        return {"error": "HASDATA_API_KEY not configured"}
    
    try:
        import http.client
        import urllib.parse
        
        conn = http.client.HTTPSConnection("api.hasdata.com")
        
        headers = {
            'x-api-key': settings.hasdata_api_key,
            'Content-Type': "application/json"
        }
        
        # URL encode the keyword
        encoded_keyword = urllib.parse.quote(keyword)
        path = f"/scrape/zillow/listing?keyword={encoded_keyword}&type={listing_type}"
        
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            import json
            result = json.loads(data.decode("utf-8"))
            return {"success": True, "data": result, "source": "HasData API (Zillow)"}
        else:
            return {"error": f"HasData API error: {res.status} - {data.decode('utf-8')}"}
    except Exception as e:
        logger.error(f"HasData Zillow API error: {e}")
        return {"error": f"HasData API request failed: {str(e)}"}


def _get_redfin_listings_hasdata(zipcode: str, listing_type: str = "forSale") -> dict:
    """
    Get Redfin listings using HasData API.
    
    Args:
        zipcode: ZIP code (e.g., "33321")
        listing_type: "forSale" or "forRent"
    
    Returns:
        dict with listings data
    """
    if not settings.hasdata_api_key:
        return {"error": "HASDATA_API_KEY not configured"}
    
    try:
        import http.client
        
        conn = http.client.HTTPSConnection("api.hasdata.com")
        
        headers = {
            'x-api-key': settings.hasdata_api_key,
            'Content-Type': "application/json"
        }
        
        path = f"/scrape/redfin/listing?keyword={zipcode}&type={listing_type}"
        
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            import json
            result = json.loads(data.decode("utf-8"))
            return {"success": True, "data": result, "source": "HasData API (Redfin)"}
        else:
            return {"error": f"HasData API error: {res.status} - {data.decode('utf-8')}"}
    except Exception as e:
        logger.error(f"HasData Redfin API error: {e}")
        return {"error": f"HasData API request failed: {str(e)}"}


def _scrape_with_scraperapi(url: str) -> requests.Response:
    """Scrape URL using ScraperAPI if available."""
    if settings.scraperapi_key:
        scraperapi_url = "http://api.scraperapi.com"
        params = {
            "api_key": settings.scraperapi_key,
            "url": url,
            "render": "true"  # Render JavaScript
        }
        response = requests.get(scraperapi_url, params=params, timeout=30)
        return response
    else:
        # Fallback to direct request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        return response


def _parse_zillow(soup: BeautifulSoup, url: str) -> dict:
    """Parse Zillow-specific property page."""
    result = {
        "url": url,
        "source": "zillow",
        "address": None,
        "price": None,
        "bedrooms": None,
        "bathrooms": None,
        "square_feet": None,
        "lot_size": None,
        "year_built": None,
        "property_type": None,
        "description": None,
        "image_urls": [],
    }
    
    text = soup.get_text()
    
    # Try to find address in title or h1
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text()
        # Zillow titles often have format: "Address | Zillow"
        if '|' in title_text:
            result["address"] = title_text.split('|')[0].strip()
    
    # Try data-testid attributes (Zillow uses these)
    price_elem = soup.find(attrs={"data-testid": "price"}) or soup.find(class_=re.compile(r'price', re.I))
    if price_elem:
        price_text = price_elem.get_text()
        price_match = re.search(r'\$([\d,]+)', price_text)
        if price_match:
            result["price"] = price_match.group(0)
    
    # Extract bedrooms/bathrooms
    bed_bath_elem = soup.find(attrs={"data-testid": "bed-bath"}) or soup.find(class_=re.compile(r'bed|bath', re.I))
    if bed_bath_elem:
        bed_bath_text = bed_bath_elem.get_text()
        bed_match = re.search(r'(\d+)\s*(?:bed|bedroom)', bed_bath_text, re.IGNORECASE)
        bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom)', bed_bath_text, re.IGNORECASE)
        if bed_match:
            result["bedrooms"] = int(bed_match.group(1))
        if bath_match:
            result["bathrooms"] = float(bath_match.group(1))
    
    # Extract square feet
    sqft_match = re.search(r'([\d,]+)\s*(?:sq\.?\s*ft|square\s*feet)', text, re.IGNORECASE)
    if sqft_match:
        result["square_feet"] = int(sqft_match.group(1).replace(',', ''))
    
    # Extract lot size
    lot_match = re.search(r'([\d,]+(?:\.\d+)?)\s*(?:acre|acres|sq\.?\s*ft)', text, re.IGNORECASE)
    if lot_match:
        result["lot_size"] = lot_match.group(1)
    
    # Extract year built
    year_match = re.search(r'Built in (\d{4})|Year built[:\s]+(\d{4})', text, re.IGNORECASE)
    if year_match:
        result["year_built"] = int(year_match.group(1) or year_match.group(2))
    
    # Extract images
    img_tags = soup.find_all('img', src=True)
    for img in img_tags[:10]:  # Limit to first 10 images
        src = img.get('src') or img.get('data-src')
        if src and ('property' in src.lower() or 'photo' in src.lower() or 'zillow' in src.lower()):
            if src.startswith('http'):
                result["image_urls"].append(src)
            elif src.startswith('//'):
                result["image_urls"].append('https:' + src)
    
    return result


def _parse_realtor(soup: BeautifulSoup, url: str) -> dict:
    """Parse Realtor.com-specific property page."""
    result = {
        "url": url,
        "source": "realtor",
        "address": None,
        "price": None,
        "bedrooms": None,
        "bathrooms": None,
        "square_feet": None,
        "lot_size": None,
        "year_built": None,
        "property_type": None,
        "description": None,
        "image_urls": [],
    }
    
    text = soup.get_text()
    
    # Realtor.com specific parsing
    # Address in h1 or title
    h1 = soup.find('h1')
    if h1:
        result["address"] = h1.get_text().strip()
    
    # Price
    price_elem = soup.find(class_=re.compile(r'price', re.I)) or soup.find(attrs={"data-testid": "price"})
    if price_elem:
        price_text = price_elem.get_text()
        price_match = re.search(r'\$([\d,]+)', price_text)
        if price_match:
            result["price"] = price_match.group(0)
    
    # Bedrooms/Bathrooms
    bed_bath_text = text
    bed_match = re.search(r'(\d+)\s*(?:bed|bedroom)', bed_bath_text, re.IGNORECASE)
    bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom)', bed_bath_text, re.IGNORECASE)
    if bed_match:
        result["bedrooms"] = int(bed_match.group(1))
    if bath_match:
        result["bathrooms"] = float(bath_match.group(1))
    
    # Square feet
    sqft_match = re.search(r'([\d,]+)\s*(?:sq\.?\s*ft|square\s*feet)', text, re.IGNORECASE)
    if sqft_match:
        result["square_feet"] = int(sqft_match.group(1).replace(',', ''))
    
    return result


def _parse_redfin(soup: BeautifulSoup, url: str) -> dict:
    """Parse Redfin-specific property page."""
    result = {
        "url": url,
        "source": "redfin",
        "address": None,
        "price": None,
        "bedrooms": None,
        "bathrooms": None,
        "square_feet": None,
        "lot_size": None,
        "year_built": None,
        "property_type": None,
        "description": None,
        "image_urls": [],
    }
    
    text = soup.get_text()
    
    # Redfin specific parsing
    # Similar to Zillow/Realtor but with Redfin-specific selectors
    price_match = re.search(r'\$([\d,]+)', text)
    if price_match:
        result["price"] = price_match.group(0)
    
    bed_match = re.search(r'(\d+)\s*(?:bed|bedroom)', text, re.IGNORECASE)
    bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom)', text, re.IGNORECASE)
    if bed_match:
        result["bedrooms"] = int(bed_match.group(1))
    if bath_match:
        result["bathrooms"] = float(bath_match.group(1))
    
    return result


def _parse_generic(soup: BeautifulSoup, url: str) -> dict:
    """Parse generic property page with common patterns."""
    result = {
        "url": url,
        "source": "generic",
        "address": None,
        "price": None,
        "bedrooms": None,
        "bathrooms": None,
        "square_feet": None,
        "lot_size": None,
        "year_built": None,
        "property_type": None,
        "description": None,
        "image_urls": [],
    }
    
    text = soup.get_text()
    
    # Generic extraction
    price_match = re.search(r'\$([\d,]+)', text)
    if price_match:
        result["price"] = price_match.group(0)
    
    bed_match = re.search(r'(\d+)\s*(?:bed|bedroom)', text, re.IGNORECASE)
    bath_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom)', text, re.IGNORECASE)
    if bed_match:
        result["bedrooms"] = int(bed_match.group(1))
    if bath_match:
        result["bathrooms"] = float(bath_match.group(1))
    
    sqft_match = re.search(r'([\d,]+)\s*(?:sq\.?\s*ft|square\s*feet)', text, re.IGNORECASE)
    if sqft_match:
        result["square_feet"] = int(sqft_match.group(1).replace(',', ''))
    
    return result


class ScrapePropertyPageInput(BaseModel):
    """Input schema for scraping a property page."""
    url: str = Field(..., description="URL of the property listing page to scrape")
    source: Optional[str] = Field(None, description="Source website (zillow, realtor, redfin) - helps with parsing")


@tool("scrape_property_page", args_schema=ScrapePropertyPageInput)
@cached(ttl=3600, prefix="scraped_property")  # Cache for 1 hour
@retry_on_http_error(max_attempts=3)
def scrape_property_page(url: str, source: Optional[str] = None) -> dict:
    """
    Scrape property data from a real estate listing page.
    Extracts property details like address, price, bedrooms, bathrooms, etc.
    
    Uses ScraperAPI if configured for reliable scraping with anti-bot protection.
    Falls back to direct requests if ScraperAPI is not available.
    """
    try:
        # Use ScraperAPI if available, otherwise direct request
        response = _scrape_with_scraperapi(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Detect source from URL if not provided
        if not source:
            if 'zillow.com' in url.lower():
                source = "zillow"
            elif 'realtor.com' in url.lower():
                source = "realtor"
            elif 'redfin.com' in url.lower():
                source = "redfin"
            else:
                source = "generic"
        
        # Parse based on source
        if source.lower() == "zillow":
            result = _parse_zillow(soup, url)
        elif source.lower() == "realtor":
            result = _parse_realtor(soup, url)
        elif source.lower() == "redfin":
            result = _parse_redfin(soup, url)
        else:
            result = _parse_generic(soup, url)
        
        # Add metadata
        result["scraping_method"] = "scraperapi" if settings.scraperapi_key else "direct"
        result["raw_html_length"] = len(response.content)
        
        # Add note if ScraperAPI not configured
        if not settings.scraperapi_key:
            result["note"] = "Using direct scraping. Configure SCRAPERAPI_KEY for better reliability and anti-bot protection."
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Scraping error: {e}")
        return {
            "error": f"Failed to scrape page: {str(e)}",
            "url": url,
            "suggestion": "Configure SCRAPERAPI_KEY for reliable web scraping with anti-bot protection. Get key at https://www.scraperapi.com/"
        }
    except Exception as e:
        logger.error(f"Unexpected scraping error: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "url": url
        }


class ExtractPropertyDataInput(BaseModel):
    """Input schema for extracting structured property data."""
    html_content: str = Field(..., description="HTML content of the property page")
    source: str = Field(..., description="Source website (zillow, realtor, redfin)")
    url: Optional[str] = Field(None, description="Original URL")


@tool("extract_property_data", args_schema=ExtractPropertyDataInput)
@cached(ttl=3600, prefix="extracted_property")  # Cache for 1 hour
def extract_property_data(html_content: str, source: str, url: Optional[str] = None) -> dict:
    """
    Extract structured property data from HTML content.
    Returns JSON with property details in snake_case format.
    
    Uses site-specific parsers for better accuracy.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Use site-specific parser
        if source.lower() == "zillow":
            result = _parse_zillow(soup, url or "")
        elif source.lower() == "realtor":
            result = _parse_realtor(soup, url or "")
        elif source.lower() == "redfin":
            result = _parse_redfin(soup, url or "")
        else:
            result = _parse_generic(soup, url or "")
        
        # Add extraction metadata
        result["extraction_method"] = "site_specific_parsing"
        result["source"] = source
        
        # Try to extract description
        desc_elem = soup.find('meta', attrs={"name": "description"}) or soup.find(class_=re.compile(r'description', re.I))
        if desc_elem:
            result["description"] = desc_elem.get('content') or desc_elem.get_text()[:500]
        
        # Try to extract property type
        text = soup.get_text()
        prop_type_match = re.search(r'(single family|condo|townhouse|apartment|multi-family|duplex)', text, re.IGNORECASE)
        if prop_type_match:
            result["property_type"] = prop_type_match.group(1).lower()
        
        return result
        
    except Exception as e:
        logger.error(f"Data extraction error: {e}")
        return {
            "error": f"Failed to extract property data: {str(e)}",
            "source": source,
            "url": url,
            "extraction_method": "error"
        }


class SearchZillowListingsInput(BaseModel):
    """Input schema for searching Zillow listings via HasData API."""
    keyword: str = Field(..., description="Location keyword (e.g., 'New York, NY', 'San Francisco, CA')")
    listing_type: str = Field("forSale", description="Listing type: 'forSale' or 'forRent'")


@tool("search_zillow_listings", args_schema=SearchZillowListingsInput)
@cached(ttl=3600, prefix="zillow_listings")  # Cache for 1 hour
@retry_on_http_error(max_attempts=3)
def search_zillow_listings(keyword: str, listing_type: str = "forSale") -> dict:
    """
    Search Zillow listings using HasData API.
    Returns property listings for a given location.
    
    Uses HasData API for reliable Zillow data extraction.
    """
    try:
        result = _get_zillow_listings_hasdata(keyword, listing_type)
        
        if "error" in result:
            return result
        
        # Extract and structure the listings data
        data = result.get("data", {})
        listings = data.get("listings", []) if isinstance(data, dict) else []
        
        # If data is a list, use it directly
        if isinstance(data, list):
            listings = data
        
        structured_listings = []
        for listing in listings[:50]:  # Limit to 50 listings
            structured_listings.append({
                "address": listing.get("address") or listing.get("street_address"),
                "price": listing.get("price") or listing.get("list_price"),
                "bedrooms": listing.get("bedrooms") or listing.get("beds"),
                "bathrooms": listing.get("bathrooms") or listing.get("baths"),
                "square_feet": listing.get("square_feet") or listing.get("sqft"),
                "lot_size": listing.get("lot_size"),
                "year_built": listing.get("year_built"),
                "property_type": listing.get("property_type"),
                "listing_url": listing.get("url") or listing.get("listing_url"),
                "image_url": listing.get("image") or listing.get("photo_url"),
                "description": listing.get("description"),
                "coordinates": listing.get("coordinates") or {
                    "lat": listing.get("latitude"),
                    "lon": listing.get("longitude")
                } if listing.get("latitude") else None,
                "raw_data": listing  # Include raw data for reference
            })
        
        return {
            "keyword": keyword,
            "listing_type": listing_type,
            "listings": structured_listings,
            "total_count": len(structured_listings),
            "data_source": "HasData API (Zillow)",
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Zillow listings search error: {e}")
        return {
            "error": f"Failed to search Zillow listings: {str(e)}",
            "keyword": keyword,
            "suggestion": "Configure HASDATA_API_KEY for Zillow listings. Get key at https://api.hasdata.com/"
        }


class SearchRedfinListingsInput(BaseModel):
    """Input schema for searching Redfin listings via HasData API."""
    zipcode: str = Field(..., description="ZIP code (e.g., '33321', '10001')")
    listing_type: str = Field("forSale", description="Listing type: 'forSale' or 'forRent'")


@tool("search_redfin_listings", args_schema=SearchRedfinListingsInput)
@cached(ttl=3600, prefix="redfin_listings")  # Cache for 1 hour
@retry_on_http_error(max_attempts=3)
def search_redfin_listings(zipcode: str, listing_type: str = "forSale") -> dict:
    """
    Search Redfin listings using HasData API.
    Returns property listings for a given ZIP code.
    
    Uses HasData API for reliable Redfin data extraction.
    Note: Redfin API uses ZIP codes instead of city names.
    """
    try:
        result = _get_redfin_listings_hasdata(zipcode, listing_type)
        
        if "error" in result:
            return result
        
        # Extract and structure the listings data
        data = result.get("data", {})
        listings = data.get("listings", []) if isinstance(data, dict) else []
        
        # If data is a list, use it directly
        if isinstance(data, list):
            listings = data
        
        structured_listings = []
        for listing in listings[:50]:  # Limit to 50 listings
            structured_listings.append({
                "address": listing.get("address") or listing.get("street_address"),
                "price": listing.get("price") or listing.get("list_price"),
                "bedrooms": listing.get("bedrooms") or listing.get("beds"),
                "bathrooms": listing.get("bathrooms") or listing.get("baths"),
                "square_feet": listing.get("square_feet") or listing.get("sqft"),
                "lot_size": listing.get("lot_size"),
                "year_built": listing.get("year_built"),
                "property_type": listing.get("property_type"),
                "listing_url": listing.get("url") or listing.get("listing_url"),
                "image_url": listing.get("image") or listing.get("photo_url"),
                "description": listing.get("description"),
                "coordinates": listing.get("coordinates") or {
                    "lat": listing.get("latitude"),
                    "lon": listing.get("longitude")
                } if listing.get("latitude") else None,
                "raw_data": listing  # Include raw data for reference
            })
        
        return {
            "zipcode": zipcode,
            "listing_type": listing_type,
            "listings": structured_listings,
            "total_count": len(structured_listings),
            "data_source": "HasData API (Redfin)",
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Redfin listings search error: {e}")
        return {
            "error": f"Failed to search Redfin listings: {str(e)}",
            "zipcode": zipcode,
            "suggestion": "Configure HASDATA_API_KEY for Redfin listings. Get key at https://api.hasdata.com/"
        }
