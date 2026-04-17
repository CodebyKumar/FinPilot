# Pocket CFO Agents - Complete Documentation

## Architecture Overview

Your system now has **5 intelligent agents**:

### 1️⃣ **SMS Parser Agent**
- Extracts UPI/bank alerts from SMS
- Handles major Indian banks (ICICI, HDFC, SBI, Axis, Kotak)
- Extracts: amount, date, party, transaction type

### 2️⃣ **PDF Parser Agent** 
- Extracts transactions from bank statements
- Works with tabular PDFs
- Falls back to text extraction for complex layouts
- Handles multi-page documents

### 3️⃣ **GST Agent** ⭐ (Existing)
- 70+ deterministic merchant rules
- HSN/SAC code mapping
- ITC eligibility classification
- LLM fallback for unknown vendors

### 4️⃣ **Profit Agent v2** ⭐ (NEW)
**What it calculates:**
- Gross Profit = Revenue - Expenses
- Net Profit = Gross Profit + ITC Claimable
- Profit margin %
- Category-wise breakdown
- Spending trends (30-day analysis)

**Output:**
```json
{
  "overall": {
    "total_revenue": 50000,
    "total_expenses": 30000,
    "total_gst_paid": 3400,
    "total_itc_claimable": 2800,
    "net_profit": 20800,
    "profit_margin_percent": 41.6
  },
  "by_category": {
    "Office Supplies": {...},
    "Travel": {...}
  },
  "spending_trends": {
    "average_daily": 1000,
    "max_spend_day": "2026-04-15"
  }
}
```

### 5️⃣ **Tax Savings Agent** ⭐ (NEW)
**Identifies:**
- Missed ITC opportunities (₹ recovery potential)
- Expense categorization gaps
- Bulk buying optimization
- High-value recommendations

**Example Output:**
```json
{
  "summary": {
    "potential_savings_per_month": 2500,
    "potential_savings_per_year": 30000,
    "high_priority_items": 3
  },
  "quick_wins": [
    "Categorize ₹15,000 in uncategorized expenses to unlock GST credits",
    "Consolidate 12 purchases from Amazon - negotiate bulk discount"
  ]
}
```

### 6️⃣ **GSTR Report Agent** ⭐ (NEW)
**Generates:**
- **GSTR-1 Draft** - Outward supplies (what you sold)
- **GSTR-3B Draft** - Monthly return (GST collected - GST paid)
- **ITC Summary** - Detailed input tax credit analysis
- **Filing Checklist** - Pre-filing validation steps

**Example GSTR-3B Output:**
```json
{
  "section_1_outward_supplies": {
    "total_taxable_supplies": 50000,
    "gst_collected": 9000
  },
  "section_2_input_tax_credit": {
    "total_itc_available": 3400,
    "itc_claimed": 3000,
    "summary": "Out of ₹3,400 available ITC, you can claim ₹3,000"
  },
  "section_3_net_payable": {
    "net_gst_payable": 6000,
    "net_refund_available": 0
  }
}
```

---

## API Endpoints

### **Comprehensive CA Summary** ⭐
```bash
GET /ca-summary/{user_id}
```
Returns everything in one call:
- Financial overview
- Profit analysis  
- Expense breakdown
- Tax opportunities
- GST compliance status
- Action items

```json
{
  "summary": {
    "net_profit": 20000,
    "total_revenue": 50000,
    "total_expenses": 30000,
    "profit_margin_percent": 40,
    "potential_monthly_savings": 2500,
    "gst_payable": 6000,
    "refund_available": 500
  },
  "action_items": 3,
  "detailed_breakdown": {...}
}
```

### **Tax Savings** 
```bash
GET /tax-savings/{user_id}
```
- Missed ITC opportunities
- Expense gap analysis
- Consolidation suggestions

### **GST Reports**
```bash
GET /gst-report/{user_id}
```
- GSTR-1, GSTR-3B, ITC analysis
- Filing checklist
- Compliance warnings

### **Profits**
```bash
GET /profit/{user_id}
```
- Detailed profit analysis
- Category breakdown
- Spending trends

### **Expenses**
```bash
GET /expenses/{user_id}
```
- Anomaly detection
- Category aggregation
- Spending patterns

---

## Usage Example

### 1. Create User
```bash
curl -X POST http://localhost:8000/users/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pratik Gautam",
    "phone": "9876543210",
    "business_name": "Tech Startup"
  }'
```

### 2. Upload Bank Statement
```bash
curl -X POST http://localhost:8000/ingest/pdf \
  -F "user_id=xyz123" \
  -F "file=@statement.pdf"
```

### 3. Get CA Report
```bash
curl http://localhost:8000/ca-summary/xyz123 | prettify
```

Returns complete financial analysis → Save as PDF → Send to CA/Bank

---

## How It Actually Works

### Data Flow:
```
User's Bank Statement (PDF/SMS)
        ↓
    PDF Parser / SMS Parser
        ↓
Transaction Objects (normalized)
        ↓
GST Agent (classify each transaction)
        ↓
Store in MongoDB (with deduplication)
        ↓
Trigger Agents:
  - Profit Agent (calculate revenue-expenses)
  - Tax Savings Agent (find opportunities)
  - GSTR Agent (generate reports)
        ↓
Return JSON response → Dashboard / Email / PDF
```

### Deduplication:
- SHA256 hash of (amount + date + party)
- Prevents duplicate parsing on re-upload
- Unique per user

### Classification:
1. **Deterministic** (70+ merchant rules)
2. **LLM Fallback** (OpenAI GPT-4o-mini for unknowns)
3. **User Manual** (override/tag transactions)

---

## Production Checklist

- [ ] Set up MongoDB with user authentication
- [ ] Configure environment variables (.env)
- [ ] Set OpenAI API key for LLM fallback
- [ ] Add custom merchant database per industry
- [ ] Create frontend dashboard
- [ ] Add email notification system
- [ ] Set up PDF export for reports
- [ ] Add 2FA for user login
- [ ] Implement rate limiting on API
- [ ] Add audit logs for CA compliance

---

## Key Files

| File | Purpose |
|------|---------|
| `agents/profit_agent_v2.py` | Profit calculations & trends |
| `agents/tax_savings_agent.py` | Tax optimization recommendations |
| `agents/gstr_report_agent.py` | GST compliance reports |
| `parsers/pdf_parser.py` | ICICI/HDFC/SBI statement extraction |
| `parsers/sms_parser.py` | UPI/Bank SMS extraction |
| `api/main.py` | FastAPI server & endpoints |

---

## Next Enhancements

**Phase 2:**
- Real-time bank API integration
- Mobile app companion
- Multi-currency support
- Invoice OCR parsing

**Phase 3:**
- AI recommendations for cost cutting
- Competitor benchmark analysis
- Loan eligibility prediction
- Tax planning scenarios

**Phase 4:**
- Regulatory filing automation
- Auditor integration
- Investor reporting
- Financial forecasting

---

## Support

For support, check:
1. Logs: `logs/` directory
2. Database: MongoDB collections
3. API Errors: Check response status codes
4. Classification Failures: Review confidence scores

Report issues with:
- Transaction date
- Amount
- Party name
- PDF preview
- Expected vs actual classification

