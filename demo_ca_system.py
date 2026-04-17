"""
Demo: Complete CA Agent System
Shows all capabilities of the Pocket CFO AI agent.
"""

import os
import sys

# Add pocket-cfo-parser to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pocket-cfo-parser'))

from pocket_cfo_parser.parsers.pdf_parser import parse_pdf
from pocket_cfo_parser.agents.profit_agent_v2 import get_profit_summary
from pocket_cfo_parser.agents.tax_savings_agent import get_tax_insights
from pocket_cfo_parser.agents.gstr_report_agent import generate_gst_compliance_report
from pocket_cfo_parser.agents.expense_agent import categorize_expenses, detect_anomalies
import json

# Parse your PDF
print("=" * 80)
print("POCKET CFO AI - COMPLETE CHARTERED ACCOUNTANT SYSTEM")
print("=" * 80)

pdf_path = r"C:\Users\gauta\Downloads\OpTransactionHistory17-04-2026.pdf-18-12-37.pdf"
transactions = parse_pdf(pdf_path)

print(f"\n✓ Parsed {len(transactions)} transactions from your bank statement\n")

# 1. PROFIT ANALYSIS
print("=" * 80)
print("1. PROFIT & FINANCIAL ANALYSIS")
print("=" * 80)
profit = get_profit_summary(transactions)
print(json.dumps(profit, indent=2, default=str))

# 2. TAX SAVINGS OPPORTUNITIES
print("\n" + "=" * 80)
print("2. TAX SAVINGS & OPTIMIZATION")
print("=" * 80)
tax_insights = get_tax_insights(transactions)
print(json.dumps(tax_insights, indent=2, default=str))

# 3. GST COMPLIANCE REPORTS
print("\n" + "=" * 80)
print("3. GST COMPLIANCE REPORTS")
print("=" * 80)
gst_reports = generate_gst_compliance_report(transactions)
print(json.dumps(gst_reports, indent=2, default=str))

# 4. EXPENSE ANALYSIS
print("\n" + "=" * 80)
print("4. EXPENSE ANALYSIS & ANOMALIES")
print("=" * 80)
categories = categorize_expenses(transactions)
print(json.dumps(categories, indent=2, default=str))

print("\n" + "=" * 80)
print("✓ Complete CA analysis generated!")
print("=" * 80)
