#!/usr/bin/env python3
"""
Generate LangGraph architecture visualization.

This script creates a visual representation of the LangGraph agent architecture
using LangGraph's built-in visualization capabilities and saves it as an image.
"""

import sys
import os
from pathlib import Path

# Add project root to path (so we can import backend.*)
# __file__ is: backend/scripts/visualize_architecture.py
# .parent is: backend/scripts
# .parent.parent is: backend
# .parent.parent.parent is: project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from backend.agents.main_agent import get_main_agent
    
    def visualize_langgraph_architecture():
        """Generate LangGraph architecture visualization."""
        print("=" * 60)
        print("LangGraph Architecture Visualization")
        print("=" * 60)
        print()
        
        # Get the agent (this will create it)
        print("Creating agent...")
        agent = get_main_agent()
        
        # Get the compiled graph
        # The agent is already a compiled graph (from create_deep_agent)
        # Following the pattern: graph = builder.compile(); graph.get_graph().draw_mermaid_png()
        compiled_graph = agent
        
        # Get the graph object from the compiled graph
        if hasattr(compiled_graph, 'get_graph'):
            graph = compiled_graph.get_graph()
            
            print("\n" + "=" * 60)
            print("LangGraph State Graph Structure")
            print("=" * 60)
            print()
            
            # Print ASCII representation
            if hasattr(graph, 'draw_ascii'):
                print("ASCII Representation:")
                print("-" * 60)
                try:
                    ascii_diagram = graph.draw_ascii()
                    print(ascii_diagram)
                    print()
                except Exception as e:
                    print(f"⚠️  Could not generate ASCII: {e}")
            
            # Generate Mermaid diagram
            if hasattr(graph, 'draw_mermaid'):
                print("Mermaid Diagram:")
                print("-" * 60)
                try:
                    mermaid_diagram = graph.draw_mermaid()
                    print(mermaid_diagram)
                    print()
                    
                    # Save Mermaid to file
                    output_file = project_root / "docs" / "langgraph_architecture.mmd"
                    output_file.parent.mkdir(exist_ok=True)
                    with open(output_file, "w") as f:
                        f.write(mermaid_diagram)
                    print(f"✅ Mermaid diagram saved to: {output_file}")
                except Exception as e:
                    print(f"⚠️  Could not generate Mermaid: {e}")
            
            # Save as PNG image using LangGraph's draw_mermaid_png() method
            # Following the exact pattern from the example:
            # graph = builder.compile()
            # with open("graph.png", "wb") as f:
            #     f.write(graph.get_graph().draw_mermaid_png())
            print("\n" + "=" * 60)
            print("Saving Architecture Image")
            print("=" * 60)
            try:
                # Create assets directory if it doesn't exist
                assets_dir = project_root / "assets"
                assets_dir.mkdir(exist_ok=True)
                
                # Use the exact pattern: compiled_graph.get_graph().draw_mermaid_png()
                image_path = assets_dir / "langgraph_architecture.png"
                
                with open(image_path, "wb") as f:
                    f.write(compiled_graph.get_graph().draw_mermaid_png())
                
                print(f"✅ Architecture image saved to: {image_path}")
                file_size = image_path.stat().st_size
                print(f"   File size: {file_size:,} bytes")
            except Exception as e:
                print(f"⚠️  Could not save PNG image: {e}")
                print("   Note: This requires additional dependencies (PIL/Pillow, pygraphviz, etc.)")
                print("   The Mermaid diagram is still available in docs/langgraph_architecture.mmd")
            
            # Print graph nodes and edges
            if hasattr(graph, 'nodes'):
                print("\n" + "=" * 60)
                print("Graph Nodes:")
                print("=" * 60)
                try:
                    for node_name in graph.nodes:
                        print(f"  • {node_name}")
                except Exception as e:
                    print(f"⚠️  Could not list nodes: {e}")
            
            if hasattr(graph, 'edges'):
                print("\n" + "=" * 60)
                print("Graph Edges:")
                print("=" * 60)
                try:
                    for edge in graph.edges:
                        print(f"  {edge}")
                except Exception as e:
                    print(f"⚠️  Could not list edges: {e}")
            
            print("\n" + "=" * 60)
            print("✅ Architecture visualization complete!")
            print("=" * 60)
            print("\nGenerated files:")
            print("  - docs/langgraph_architecture.mmd (Mermaid diagram)")
            image_path = project_root / "assets" / "langgraph_architecture.png"
            if image_path.exists():
                print(f"  - assets/langgraph_architecture.png (PNG image - {image_path.stat().st_size:,} bytes)")
            
        else:
            print("⚠️  Compiled graph does not have get_graph() method")
            print(f"Graph type: {type(compiled_graph)}")
            print(f"Available methods: {[m for m in dir(compiled_graph) if not m.startswith('_')]}")
            
    if __name__ == "__main__":
        visualize_langgraph_architecture()
        
except Exception as e:
    print(f"❌ Error generating visualization: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
