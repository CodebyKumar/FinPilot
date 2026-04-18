#!/usr/bin/env python3
"""
ITR-1 HTML Template Renderer
Reads JSON data and generates a filled PDF-ready HTML document
"""

import json
import sys
from pathlib import Path


def render_template(template_path: str, data_path: str, output_path: str) -> str:
    """
    Render ITR-1 HTML template with JSON data.
    
    Args:
        template_path: Path to ITR-1-2026-Template.html
        data_path: Path to JSON data file
        output_path: Path to save rendered HTML
    
    Returns:
        Path to generated HTML file
    """
    
    # Read template
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Read JSON data
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Replace all {{placeholder}} with actual values
    for key, value in data.items():
        placeholder = f"{{{{{key}}}}}"
        # Ensure value is converted to string, handle None and empty values
        str_value = str(value) if value is not None else ""
        html_content = html_content.replace(placeholder, str_value)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_path


def main():
    """Main entry point"""
    
    # Default paths
    template = Path(__file__).parent / "ITR-1-2026-Template.html"
    data_file = Path(__file__).parent / "ITR-1-sample-data.json"
    output = Path(__file__).parent / "ITR-1-2026-RENDERED.html"
    
    # Allow CLI override
    if len(sys.argv) > 1:
        data_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output = Path(sys.argv[2])
    
    # Validate inputs
    if not template.exists():
        print(f"Error: Template not found at {template}")
        return 1
    
    if not data_file.exists():
        print(f"Error: Data file not found at {data_file}")
        return 1
    
    # Render
    try:
        result = render_template(str(template), str(data_file), str(output))
        print(f"✓ ITR-1 rendered successfully")
        print(f"  Template: {template}")
        print(f"  Data: {data_file}")
        print(f"  Output: {result}")
        return 0
    except Exception as e:
        print(f"Error rendering template: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
