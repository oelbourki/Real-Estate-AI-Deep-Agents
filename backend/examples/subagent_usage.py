"""
Example usage of subagents in the Real Estate AI Deep Agents.

This file demonstrates how the main agent delegates tasks to subagents.
"""

# Example 1: Property Research Subagent
PROPERTY_RESEARCH_EXAMPLE = """
User: "Find 3 bedroom houses for sale in San Francisco, CA under $2M"

Main Agent will delegate to property-research subagent:
- Uses realty_us_search_buy tool
- Filters by location, bedrooms, price
- Returns property listings
"""

# Example 2: Location Analysis Subagent
LOCATION_ANALYSIS_EXAMPLE = """
User: "What amenities are near 123 Main St, San Francisco, CA?"

Main Agent will delegate to location-analysis subagent:
- Uses geocode_address to get coordinates
- Uses find_nearby_amenities to search for restaurants, schools, parks, etc.
- Returns comprehensive amenity report
"""

# Example 3: Financial Analysis Subagent
FINANCIAL_ANALYSIS_EXAMPLE = """
User: "Calculate ROI for a $500k property with $3000/month rent, 20% down, 6.5% interest"

Main Agent will delegate to financial-analysis subagent:
- Uses calculate_roi tool
- Returns ROI %, cash flow, cap rate, expense breakdown
"""

# Example 4: Multi-Subagent Workflow
MULTI_SUBAGENT_EXAMPLE = """
User: "Find houses in SF, analyze their locations, and calculate ROI assuming $4000/month rent"

Main Agent workflow:
1. Plan tasks using write_todos
2. Delegate to property-research: Find properties
3. Delegate to location-analysis: Analyze each property's location
4. Delegate to financial-analysis: Calculate ROI for each property
5. Synthesize results and present comprehensive analysis
"""

# Example 5: Route Calculation
ROUTE_EXAMPLE = """
User: "What's the route from 123 Main St to Golden Gate Bridge?"

Main Agent will delegate to location-analysis subagent:
- Uses geocode_address for both locations
- Uses osm_route to calculate route
- Returns distance, duration, and route geometry
"""

if __name__ == "__main__":
    print("Subagent Usage Examples")
    print("=" * 50)
    print("\n1. Property Research:")
    print(PROPERTY_RESEARCH_EXAMPLE)
    print("\n2. Location Analysis:")
    print(LOCATION_ANALYSIS_EXAMPLE)
    print("\n3. Financial Analysis:")
    print(FINANCIAL_ANALYSIS_EXAMPLE)
    print("\n4. Multi-Subagent Workflow:")
    print(MULTI_SUBAGENT_EXAMPLE)
    print("\n5. Route Calculation:")
    print(ROUTE_EXAMPLE)
