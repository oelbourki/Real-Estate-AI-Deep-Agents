#!/usr/bin/env python3
"""
Generate comprehensive LangGraph architecture visualization with all subagents.

This script creates a complete visual representation showing:
- Main Orchestrator Agent
- All 6 Subagents
- All Tools
- External APIs
- Data flow
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from backend.agents.main_agent import get_main_agent
    from backend.agents.subagents import get_subagents

    def create_comprehensive_mermaid_diagram():
        """Create a comprehensive Mermaid diagram showing all subagents."""
        # Build Mermaid diagram (subagent list is fixed in diagram below)
        mermaid = """---
config:
  flowchart:
    curve: linear
    padding: 20
---
graph TB
    Start([User Query]) --> UI{User Interface}
    UI -->|HTTP/WebSocket| API[FastAPI Backend<br/>LangGraph Platform API]
    
    API --> MainAgent[Main Orchestrator Agent<br/>DeepAgents + LangGraph StateGraph]
    
    MainAgent --> Decision{Query Analysis}
    
    Decision -->|Simple Query| DirectTools[Direct Tools]
    Decision -->|Complex Query| SubagentRouter[Subagent Router]
    
    DirectTools --> Tool1[realty_us_search_buy]
    DirectTools --> Tool2[realty_us_search_rent]
    
    SubagentRouter --> SubAgent1[Property Research Agent]
    SubagentRouter --> SubAgent2[Location Analysis Agent]
    SubagentRouter --> SubAgent3[Financial Analysis Agent]
    SubagentRouter --> SubAgent4[Data Extraction Agent]
    SubagentRouter --> SubAgent5[Market Trends Agent]
    SubagentRouter --> SubAgent6[Report Generator Agent]
    
    SubAgent1 --> Tool1
    SubAgent1 --> Tool2
    
    SubAgent2 --> Tool3[geocode_address]
    SubAgent2 --> Tool4[osm_poi_search]
    SubAgent2 --> Tool5[osm_route]
    SubAgent2 --> Tool6[find_nearby_amenities]
    
    SubAgent3 --> Tool7[calculate_roi]
    SubAgent3 --> Tool8[estimate_mortgage]
    SubAgent3 --> Tool9[calculate_property_tax]
    SubAgent3 --> Tool10[compare_properties]
    
    SubAgent4 --> Tool11[scrape_property_page]
    SubAgent4 --> Tool12[extract_property_data]
    
    SubAgent5 --> Tool13[search_market_trends]
    SubAgent5 --> Tool14[get_price_history]
    SubAgent5 --> Tool15[compare_markets]
    
    SubAgent6 --> FileSystem[Filesystem Backend<br/>Report Generation]
    
    Tool1 --> API1[RealtyUS API<br/>via RapidAPI]
    Tool2 --> API1
    Tool3 --> API2[OpenStreetMap<br/>Nominatim]
    Tool4 --> API2
    Tool5 --> API3[OpenRouteService<br/>Route Calculation]
    Tool6 --> API2
    Tool11 --> API4[Web Scraping<br/>Zillow/Realtor/Redfin]
    Tool12 --> API4
    
    MainAgent --> StateGraph[LangGraph StateGraph]
    StateGraph --> Memory[MemorySaver<br/>Conversation Memory]
    StateGraph --> Storage[Composite Backend<br/>Filesystem Storage]
    StateGraph --> LLM[LLM Provider<br/>OpenRouter/Ollama/OpenAI/etc]
    
    MainAgent --> Response[Response Synthesis]
    Response --> UI
    
    %% Styling
    style MainAgent fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff
    style StateGraph fill:#7B68EE,stroke:#5A4FCF,stroke-width:2px,color:#fff
    style SubagentRouter fill:#50C878,stroke:#2E8B57,stroke-width:2px,color:#fff
    style DirectTools fill:#FF6B6B,stroke:#CC5555,stroke-width:2px,color:#fff
    style LLM fill:#FFA500,stroke:#CC8500,stroke-width:2px,color:#fff
    style SubAgent1 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style SubAgent2 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style SubAgent3 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style SubAgent4 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style SubAgent5 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style SubAgent6 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style API1 fill:#FFF3E0,stroke:#FF9800,stroke-width:2px
    style API2 fill:#FFF3E0,stroke:#FF9800,stroke-width:2px
    style API3 fill:#FFF3E0,stroke:#FF9800,stroke-width:2px
    style API4 fill:#FFF3E0,stroke:#FF9800,stroke-width:2px
"""
        return mermaid

    def visualize_complete_architecture():
        """Generate complete architecture visualization with subagents."""
        print("=" * 60)
        print("Complete LangGraph Architecture Visualization")
        print("Including All Subagents and Tools")
        print("=" * 60)
        print()

        # Get subagents info
        subagents = get_subagents()
        print(f"Found {len(subagents)} subagents:")
        for i, subagent in enumerate(subagents, 1):
            tools_count = len(subagent.get("tools", []))
            print(f"  {i}. {subagent['name']} ({tools_count} tools)")
        print()

        # Create comprehensive Mermaid diagram
        mermaid_diagram = create_comprehensive_mermaid_diagram()

        # Save Mermaid diagram
        output_file = project_root / "docs" / "complete_architecture.mmd"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            f.write(mermaid_diagram)
        print(f"✅ Complete architecture diagram saved to: {output_file}")

        # Also get the actual LangGraph visualization
        print("\n" + "=" * 60)
        print("LangGraph Internal Structure")
        print("=" * 60)
        print()

        print("Creating agent to get LangGraph structure...")
        agent = get_main_agent()
        compiled_graph = agent

        if hasattr(compiled_graph, "get_graph"):
            graph = compiled_graph.get_graph()

            # Get LangGraph's own visualization
            if hasattr(graph, "draw_mermaid"):
                try:
                    langgraph_mermaid = graph.draw_mermaid()
                    langgraph_file = project_root / "docs" / "langgraph_internal.mmd"
                    with open(langgraph_file, "w") as f:
                        f.write(langgraph_mermaid)
                    print(f"✅ LangGraph internal structure saved to: {langgraph_file}")
                except Exception as e:
                    print(f"⚠️  Could not generate LangGraph internal diagram: {e}")

            # Save PNG image
            print("\n" + "=" * 60)
            print("Saving Architecture Images")
            print("=" * 60)
            try:
                assets_dir = project_root / "assets"
                assets_dir.mkdir(exist_ok=True)

                # Save LangGraph's internal structure as PNG
                image_path = assets_dir / "langgraph_architecture.png"
                with open(image_path, "wb") as f:
                    f.write(compiled_graph.get_graph().draw_mermaid_png())
                print(f"✅ LangGraph internal structure image: {image_path}")

            except Exception as e:
                print(f"⚠️  Could not save PNG image: {e}")

        # Try to convert Mermaid to PNG
        print("\n" + "=" * 60)
        print("Converting Complete Architecture to PNG")
        print("=" * 60)
        complete_png = project_root / "assets" / "complete_architecture.png"

        # Import and use the conversion script
        try:
            # Add scripts directory to path for import
            scripts_dir = Path(__file__).parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))

            from mermaid_to_png import convert_mermaid_to_png

            if convert_mermaid_to_png(output_file, complete_png):
                print(f"\n✅ Complete architecture PNG saved to: {complete_png}")
            else:
                print("\n⚠️  Automatic conversion failed. Run manually:")
                print("   python backend/scripts/mermaid_to_png.py")
        except Exception as e:
            print(f"⚠️  Could not convert to PNG automatically: {e}")
            print("   Run manually: python backend/scripts/mermaid_to_png.py")

        print("\n" + "=" * 60)
        print("✅ Complete architecture visualization generated!")
        print("=" * 60)
        print("\nGenerated files:")
        print(
            "  - docs/complete_architecture.mmd (Complete diagram with all subagents)"
        )
        print("  - docs/langgraph_internal.mmd (LangGraph internal structure)")
        print("  - assets/langgraph_architecture.png (LangGraph internal PNG)")
        complete_png = project_root / "assets" / "complete_architecture.png"
        if complete_png.exists():
            print(
                f"  - assets/complete_architecture.png (Complete architecture PNG - {complete_png.stat().st_size:,} bytes)"
            )
        print("\n💡 The complete_architecture.mmd shows:")
        print("   • Main Orchestrator Agent")
        print("   • All 6 Subagents with their tools")
        print("   • External APIs")
        print("   • Data flow and connections")
        print("\n💡 To convert Mermaid to PNG:")
        print("   python backend/scripts/mermaid_to_png.py")

    if __name__ == "__main__":
        visualize_complete_architecture()

except Exception as e:
    print(f"❌ Error generating visualization: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
