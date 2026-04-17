# Pocket CFO Agent — Project Plan
**Team NPC (Not Paid Coders) | Siddaganga Institute of Technology**
**Track: FinTech | Hackfest 2026**

---

## What Are We Building?

An AI-powered personal CA (Chartered Accountant) for Indian SMBs. It automatically ingests financial data from UPI, bills, and bank statements — then tells the business owner exactly what to do, not just what happened.

Think of it this way: Tally is a filing cabinet. We are the CA who reads everything and calls you saying *"bhai ₹45k pending hai, aaj hi collect kar."*

---

## The Problem

India has 63M+ GST-registered small businesses. Most of them:
- Do bookkeeping manually in Excel or notebooks
- Miss ITC (Input Tax Credit) claims worth lakhs
- Get penalties for wrong/late GST filing
- Have zero idea if they're actually profitable after GST
- Can't afford a real CA every month

No existing tool (Tally, Vyapar, Zoho) is autonomous — they all wait for the owner to enter data.

---

## Our Solution — The 5 Layers

### Layer 1 — Data Ingestion (get data without user typing)
| Source | How |
|--------|-----|
| UPI / SMS | spaCy + Regex parser reads SMS automatically |
| Bank PDF | pdfplumber extracts all transactions |
| Invoice photo | Google Vision API + Tesseract OCR |
| Telegram bill | Telegram Bot API + OCR |
| Voice (Hindi) | OpenAI Whisper transcription |

### Layer 2 — Normalization (clean and deduplicate)
- Deduplicate using hash of amount + date + party (Redis cache)
- Entity resolution — map "Swiggy", "SWIGGY IND", "Swiggy India" to same vendor
- BERT classifier pre-tags expense category
- All stored in PostgreSQL as immutable double-entry ledger

### Layer 3 — AI Agents (the brain — 6 agents via LangGraph)
| Agent | What It Does |
|-------|-------------|
| GST Compliance Agent | HSN/SAC lookup, ITC eligibility, GSTR-1 + GSTR-3B draft generation |
| Expense Intelligence Agent | Multi-class expense classifier, anomaly detection |
| Profit Reality Agent | Revenue minus COGS minus Fixed minus GST = real profit per product |
| Cashflow Prediction Agent | ARIMA + Prophet, 7/15/30-day liquidity forecast |
| Tax Planning Agent | Advance tax estimate, deduction timing suggestions |
| Reconciliation Agent | Bank vs UPI vs Invoice 3-way match, flags mismatches |

### Layer 4 — Synthesis (prioritize and surface)
- Priority scorer: Red (act today) / Amber (watch) / Green (opportunity)
- Alert deduplication — merge overlapping agent alerts
- REST API gateway serializes outputs to JSON

### Layer 5 — Decision-First UI (no dashboards, only actions)
- Mobile (React Native): action cards home screen
- Web (Next.js): drill-down views and reports
- No charts for the sake of charts — every screen answers "what should I do?"

---

## Special Power Features

### GST Error Simulation
Dry-run your filing before actually submitting to the GST portal. Catches:
- Wrong HSN codes
- Blocked ITC claims
- GSTR-1 vs GSTR-3B mismatches
Saves the user from penalties before they happen.

### What-If Engine
User asks: "What if I raise my price by 5%?" or "What if I delay this purchase 30 days?"
→ App instantly shows profit and cashflow impact.

### Business Risk Score (0–100)
Composite score based on:
- Cashflow stability
- GST compliance streak
- Expense volatility
Useful for loan applications — gives a real number to show a bank.

### Voice Entry
User says: *"Kal ₹2000 ka payment aaya Ramesh se"*
→ App creates a structured ledger entry in seconds.

---

## Tech Stack

| Area | Technology |
|------|-----------|
| Mobile frontend | React Native |
| Web frontend | Next.js |
| Backend API | Node.js (Express) |
| AI microservices | Python |
| Agent orchestration | LangGraph (multi-agent, shared DAG state) |
| OCR | Google Vision API + Tesseract |
| Voice / NLP | OpenAI Whisper (Hindi + English) |
| GST Logic | Custom deterministic rules engine (HSN/SAC lookup, slab classification) |
| ML — expense | Fine-tuned BERT classifier |
| ML — cashflow | Facebook Prophet + ARIMA |
| Database | PostgreSQL (immutable double-entry ledger) |
| Cache | Redis (deduplication) |
| Integrations | Telegram Bot API, UPI SMS parser, GST Portal API |

---

## Build Order (What to Build First)

> Always build the demo flow first. Get that working and clean before adding more features.

### Phase 1 — MVP Demo (build this first)
- [ ] UPI SMS parser → extract amount, merchant, date, category
- [ ] GST classification agent → ITC detection, HSN lookup
- [ ] Decision-first home screen → 3 live action cards (Red / Amber / Green)
- [ ] GST Error Simulation → dry run before filing

### Phase 2 — Core Product
- [ ] Bank PDF ingestion (pdfplumber)
- [ ] Invoice OCR (Google Vision + Tesseract)
- [ ] Expense Intelligence Agent
- [ ] Profit Reality Agent
- [ ] PostgreSQL double-entry ledger
- [ ] GSTR-1 and GSTR-3B auto-draft generation
- [ ] Reconciliation Agent (bank vs UPI vs invoice 3-way match)

### Phase 3 — Intelligence Layer
- [ ] Cashflow Prediction Agent (Prophet model, 30-day forecast)
- [ ] Tax Planning Agent (advance tax estimate)
- [ ] What-If Engine
- [ ] Business Risk Score (0–100)
- [ ] Alert deduplication and priority scoring

### Phase 4 — Indian SMB Experience
- [ ] Hindi voice input (OpenAI Whisper)
- [ ] Telegram bill ingestion bot
- [ ] Entity resolution (alias mapping across sources)
- [ ] Next.js web dashboard with drill-down reports
- [ ] BERT expense classifier fine-tuning

---

## Use Cases (Real Scenarios)

1. **Kirana shop owner** says *"Kal ₹5,000 ka maal aaya"* → auto-logged, classified, reflected in cashflow instantly

2. **Freelancer** scans a vendor invoice → GST liability calculated, GSTR-1 entry created automatically

3. **Trader** gets alert: *"₹45,000 pending from 3 clients for 30+ days — collect now"*

4. **Any SMB** runs GST Error Simulation before filing → catches wrong HSN codes, blocked ITC → avoids penalty

5. **Small manufacturer** discovers one product is loss-making after real GST + cost deduction

---

## Market Opportunity

- 63M GST-registered SMBs in India
- ₹1.5 lakh crore lost annually to compliance errors and GST penalties
- 80% of SMBs still on manual bookkeeping or basic apps

---

## Monetisation Plan

| Model | Details |
|-------|---------|
| SaaS — Direct | ₹499–₹1,499/month per business |
| B2B2B — CA Firms | CA firms pay per client managed on the platform |

---

## What Makes Us Different

| Feature | Tally / Vyapar / Zoho | Pocket CFO Agent |
|---------|----------------------|-----------------|
| Data entry | Manual | Automatic (SMS, OCR, Voice) |
| Output | Reports of what happened | Actions to take right now |
| GST filing | User does it | Auto-drafted + error checked |
| Cashflow | Shows current balance | Predicts 30 days ahead |
| Language | English only | Hindi voice supported |
| Input channels | App only | SMS, Telegram, Voice, Photo |

---

## Demo Script (for Hackathon)

1. Show a raw UPI SMS → app parses it live into a ledger entry
2. Show the Decision Home Screen — 3 action cards with real numbers
3. Trigger the GST Error Simulation — show it catching a wrong HSN code
4. Show the ITC detection — "you missed ₹3,200 in claimable credit"

Keep it under 3 minutes. One real flow, done cleanly, beats 10 half-working features.

---

## Key Risks to Watch

| Risk | Mitigation |
|------|-----------|
| GST rules are complex and change | Use deterministic rules engine, not LLM for GST logic |
| OCR accuracy on bad photos | Fallback to manual confirmation for low-confidence reads |
| SMS parsing varies by bank | Build parsers for top 5 banks first (SBI, HDFC, ICICI, Axis, Kotak) |
| LangGraph agent coordination | Keep agents stateless where possible, shared state only for final synthesis |
| Scope creep | Phase 1 only until demo is airtight |