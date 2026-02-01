#!/usr/bin/env python3
"""
Convert Mermaid diagram to PNG image.

This script converts a Mermaid diagram file to PNG using available tools.
Tries multiple methods: mermaid-cli, playwright, or provides instructions.
"""

import sys
import subprocess
from pathlib import Path


def convert_mermaid_to_png(mermaid_file: Path, output_png: Path):
    """Convert Mermaid file to PNG using available tools."""

    if not mermaid_file.exists():
        print(f"❌ Mermaid file not found: {mermaid_file}")
        return False

    print("=" * 60)
    print("Converting Mermaid Diagram to PNG")
    print("=" * 60)
    print(f"Input:  {mermaid_file}")
    print(f"Output: {output_png}")
    print()

    # Method 1: Try mermaid-cli (mmdc) - most common and recommended
    print("Method 1: Trying mermaid-cli (mmdc)...")
    try:
        result = subprocess.run(
            [
                "mmdc",
                "-i",
                str(mermaid_file),
                "-o",
                str(output_png),
                "-w",
                "2000",
                "-H",
                "1500",
                "-b",
                "white",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and output_png.exists():
            print("✅ Successfully converted using mermaid-cli (mmdc)")
            print(f"   Output: {output_png}")
            print(f"   File size: {output_png.stat().st_size:,} bytes")
            return True
        else:
            if result.stderr:
                print(f"   Error: {result.stderr}")
    except FileNotFoundError:
        print("   ⚠️  mermaid-cli (mmdc) not found")
    except subprocess.TimeoutExpired:
        print("   ⚠️  mermaid-cli timed out")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

    # Method 2: Try using playwright (if available)
    print("\nMethod 2: Trying Playwright...")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Read Mermaid content
            mermaid_content = mermaid_file.read_text()

            # Extract just the graph part (remove frontmatter if present)
            if mermaid_content.startswith("---"):
                # Skip frontmatter
                parts = mermaid_content.split("---", 2)
                if len(parts) >= 3:
                    mermaid_diagram = parts[2].strip()
                else:
                    mermaid_diagram = mermaid_content
            else:
                mermaid_diagram = mermaid_content

            # Create HTML with Mermaid
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: white;
        }}
        .mermaid {{
            background: white;
        }}
    </style>
</head>
<body>
    <div class="mermaid">
{mermaid_diagram}
    </div>
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true
            }}
        }});
    </script>
</body>
</html>"""

            page.set_content(html)
            page.wait_for_timeout(3000)  # Wait for Mermaid to render

            # Take screenshot
            output_png.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(output_png), full_page=True, type="png")
            browser.close()

            if output_png.exists():
                print("✅ Successfully converted using Playwright")
                print(f"   Output: {output_png}")
                print(f"   File size: {output_png.stat().st_size:,} bytes")
                return True
    except ImportError:
        print("   ⚠️  Playwright not installed")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

    # Method 3: Try using selenium (if available)
    print("\nMethod 3: Trying Selenium...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=2000,1500")

        driver = webdriver.Chrome(options=chrome_options)

        # Read Mermaid content
        mermaid_content = mermaid_file.read_text()

        # Extract just the graph part
        if mermaid_content.startswith("---"):
            parts = mermaid_content.split("---", 2)
            if len(parts) >= 3:
                mermaid_diagram = parts[2].strip()
            else:
                mermaid_diagram = mermaid_content
        else:
            mermaid_diagram = mermaid_content

        # Create HTML with Mermaid
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            background: white;
        }}
    </style>
</head>
<body>
    <div class="mermaid">
{mermaid_diagram}
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>"""

        driver.get("data:text/html;charset=utf-8," + html)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "mermaid"))
        )
        driver.implicitly_wait(3)

        # Take screenshot
        output_png.parent.mkdir(parents=True, exist_ok=True)
        driver.save_screenshot(str(output_png))
        driver.quit()

        if output_png.exists():
            print("✅ Successfully converted using Selenium")
            print(f"   Output: {output_png}")
            print(f"   File size: {output_png.stat().st_size:,} bytes")
            return True
    except ImportError:
        print("   ⚠️  Selenium not installed")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")

    # If all methods failed, provide instructions
    print("\n" + "=" * 60)
    print("❌ Could not convert Mermaid to PNG automatically")
    print("=" * 60)
    print("\n💡 Installation options:")
    print("\n1. Install mermaid-cli (Recommended):")
    print("   npm install -g @mermaid-js/mermaid-cli")
    print(
        "   Then run: mmdc -i docs/complete_architecture.mmd -o assets/complete_architecture.png"
    )
    print("\n2. Install Playwright:")
    print("   pip install playwright")
    print("   playwright install chromium")
    print("   Then run this script again")
    print("\n3. Use online tool:")
    print("   - Copy content from docs/complete_architecture.mmd")
    print("   - Paste at https://mermaid.live/")
    print("   - Export as PNG")
    print("\n4. Use Selenium (requires ChromeDriver):")
    print("   pip install selenium")
    print("   Then run this script again")

    return False


if __name__ == "__main__":
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    mermaid_file = project_root / "docs" / "complete_architecture.mmd"
    output_png = project_root / "assets" / "complete_architecture.png"

    success = convert_mermaid_to_png(mermaid_file, output_png)
    sys.exit(0 if success else 1)
