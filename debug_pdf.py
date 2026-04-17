"""Debug script to analyze PDF structure"""
import pdfplumber
import json

pdf_path = r"C:\Users\gauta\Downloads\OpTransactionHistory17-04-2026.pdf-18-12-37.pdf"

print(f"📄 Analyzing: {pdf_path}\n")

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}\n")
        
        for page_idx, page in enumerate(pdf.pages[:1]):  # First page only
            print(f"\n{'='*80}")
            print(f"PAGE {page_idx + 1}")
            print(f"{'='*80}")
            
            # Extract text
            text = page.extract_text()
            print(f"\n📝 FULL TEXT:\n{text}\n")
            
            # Extract tables
            tables = page.extract_tables()
            print(f"\n📊 TABLES FOUND: {len(tables)}")
            
            if tables:
                for table_idx, table in enumerate(tables):
                    print(f"\n  Table {table_idx + 1}: {len(table)} rows, {len(table[0]) if table else 0} cols")
                    
                    # Show all rows
                    print(f"\n  ALL ROWS:")
                    for row_idx, row in enumerate(table):
                        print(f"    Row {row_idx}: {row}")
            else:
                print("  ❌ No tables detected by pdfplumber")

except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
