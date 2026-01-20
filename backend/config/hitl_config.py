"""Human-in-the-Loop (HITL) configuration."""
from typing import Dict, Any
from langchain.agents.middleware import InterruptOnConfig

# Define which tools require human approval
HITL_CONFIG: Dict[str, bool | InterruptOnConfig] = {
    # Web scraping operations (costly, rate-limited)
    "scrape_property_page": {
        "allowed_decisions": ["approve", "edit", "reject"],
        "message": "This will scrape a property page. Approve to continue."
    },
    
    # Large API calls (cost control)
    "realty_us_search_buy": False,  # Allow without approval
    "realty_us_search_rent": False,  # Allow without approval
    
    # Report generation (resource intensive)
    # Note: Report generation uses filesystem tools, which are handled by DeepAgents middleware
    # We can add interrupt_on for write_file if needed
    
    # Market research (may be costly)
    "search_market_trends": False,  # Allow without approval for now
    
    # Financial calculations (safe, no approval needed)
    "calculate_roi": False,
    "estimate_mortgage": False,
    "calculate_property_tax": False,
}

def get_hitl_config() -> Dict[str, bool | InterruptOnConfig]:
    """Get HITL configuration for agent."""
    return HITL_CONFIG
