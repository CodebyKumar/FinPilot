#!/usr/bin/env python3
"""
Comprehensive Financial Report Template Renderer
Converts JSON data into formatted HTML and Text reports
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def render_template(template_path: str, data_path: str, output_path: str) -> str:
    """
    Read template, load JSON data, replace placeholders, write output
    
    Args:
        template_path: Path to template file (.html or .txt)
        data_path: Path to JSON data file
        output_path: Path to output file
    
    Returns:
        Path to generated output file
    """
    # Read template
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Load JSON data
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Replace all placeholders
    for key, value in data.items():
        placeholder = f"{{{{{key}}}}}"
        str_value = str(value) if value is not None else ""
        template_content = template_content.replace(placeholder, str_value)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template_content)
    
    return output_path


def main():
    """
    CLI interface for template rendering
    
    Usage:
        python render_reports.py [data.json] [template.html] [output.html]
        python render_reports.py [data.json] [template.txt] [output.txt]
    """
    
    # Default paths
    base_dir = Path(__file__).parent
    default_data = base_dir / "ITR-1-mock-data.json"
    default_html_template = base_dir / "FINANCIAL-REPORT-TEMPLATE.html"
    default_txt_template = base_dir / "FINANCIAL-REPORT-TEMPLATE.txt"
    default_html_output = base_dir / f"FINANCIAL-REPORT-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    default_txt_output = base_dir / f"FINANCIAL-REPORT-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
    
    # Parse arguments
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = str(default_data)
    
    if len(sys.argv) > 2:
        template_file = sys.argv[2]
    else:
        # Render both templates by default
        print("📋 Financial Report Template Renderer")
        print("=" * 60)
        
        # Render HTML
        if default_html_template.exists():
            try:
                html_output = render_template(
                    str(default_html_template),
                    data_file,
                    str(default_html_output)
                )
                print(f"✓ HTML Report generated: {html_output}")
            except Exception as e:
                print(f"✗ HTML Report failed: {e}")
        
        # Render TXT
        if default_txt_template.exists():
            try:
                txt_output = render_template(
                    str(default_txt_template),
                    data_file,
                    str(default_txt_output)
                )
                print(f"✓ Text Report generated: {txt_output}")
            except Exception as e:
                print(f"✗ Text Report failed: {e}")
        
        print("=" * 60)
        return
    
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    else:
        # Auto-detect output format from template
        if template_file.endswith('.html'):
            output_file = str(default_html_output)
        elif template_file.endswith('.txt'):
            output_file = str(default_txt_output)
        else:
            output_file = template_file.replace('.', '-rendered.')
    
    # Render template
    try:
        result = render_template(template_file, data_file, output_file)
        print(f"✓ Report rendered successfully!")
        print(f"  Template: {template_file}")
        print(f"  Data: {data_file}")
        print(f"  Output: {result}")
    except FileNotFoundError as e:
        print(f"✗ File not found: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ JSON parse error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Rendering failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
