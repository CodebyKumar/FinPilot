# AI CFO Backend Consolidation Plan

## 1. Why This Plan Exists
Current backend capabilities are scattered across multiple agents and endpoints. Some agents are useful, some are redundant, and some need upgrades. This plan consolidates everything into one clean backend architecture that can power profile-first tax workflows, bookkeeping, report generation, report analysis, deadline automation, and assistant chat.

Primary goal:
Build one reliable backend control plane so the frontend team can integrate cleanly without endpoint chaos.

Guiding principle:
Minimal endpoints, powerful reusable agents, persistent profile memory, async deadline intelligence.

## 2. Scope
- Work only inside backend.
- Reuse existing backend modules wherever possible.
- Do not over-fragment into too many micro-agents.
- Keep flow extensible for future modules.

## 3. Core Product Requirements

### 3.1 Profiler Section
Purpose:
Collect all mandatory user details required for income tax and compliance forms once, then reuse repeatedly.

Must do:
- Create and persist user profile.
- Support partial updates and full edits.
- Validate mandatory tax fields.
- Return structured profile data for report generator and report analysis.
- Prevent repetitive data entry across forms.

Mandatory profile blocks:
- Personal identity: full name, DOB, PAN, Aadhaar, contact details.
- Business identity: business name, entity type, GSTIN, address, industry.
- Financial identity: bank accounts, income sources, recurring deductions.
- Compliance preferences: filing frequency, reminder preferences, timezone.

Security rules:
- Encrypt sensitive IDs at rest.
- Mask sensitive IDs in API responses.
- Never log raw PAN/Aadhaar values.

### 3.2 Bookkeeping Agent
Purpose:
Maintain a continuously updated, auditable book of financial records.

Inputs:
- Bank statements (PDF now, CSV later).
- Manual entries.
- Invoice uploads for cash/off-bank transactions.

Must do:
- Parse and extract transactions.
- Classify and categorize transactions.
- Maintain ledger with dates and references.
- Merge invoice-backed cash entries.
- Provide periodic reminders to keep books updated.

Reminder behavior:
- Daily nudges for incomplete data.
- Weekly summaries.
- Monthly close reminders.

### 3.3 Report Generator Agent
Purpose:
Take a report template and produce a field-wise filled output using profile + bookkeeping data.

Inputs:
- Uploaded report template PDF or report type.
- Profile data.
- Ledger and invoice data.

Must do:
- Extract all fields from the report.
- Map fields to known profile/ledger values.
- Create missing-fields list for user completion.
- Return filled structured form output.

Output format requirement:
- Field-level objects with field ID (A1, A2, etc.), field name, value, and fill status.
- Output can be JSON-first in MVP; PDF output optional in later phase.

### 3.4 Report Analysis Agent
Purpose:
Verify generated or user-filled reports before final submission.

Inputs:
- Filled report (JSON or PDF).

Must do:
- Detect missing required fields.
- Detect inconsistencies and invalid values.
- Validate against rule checks.
- Return errors, warnings, and suggestions.

Use cases:
- Analyze user-uploaded filled report.
- Analyze generated report before final handoff.

### 3.5 Deadline and Calendar Agent (Async)
Purpose:
Continuously monitor deadlines and notify users proactively.

Must do:
- Maintain tax/compliance calendar.
- Track due dates and reminder windows.
- Trigger notifications for upcoming deadlines.
- Support Gmail notification channel.
- Optionally sync with user calendar.

Reminder logic:
- T-7, T-1, and due-day reminders.
- Skip reminder if report already marked submitted.
- Allow user to ignore/acknowledge if completed.

### 3.6 Assistant Section
Purpose:
Conversational AI for finance/tax/compliance guidance.

Must do:
- Answer user queries tied to business finance and tax context.
- Use profile + bookkeeping + report context when needed.
- Filter out irrelevant non-domain requests.

Domain scope:
- Tax.
- Finance.
- Compliance.

## 4. Architecture Decisions and Logic Fixes
1. Use execute-first API design. Keep one primary endpoint for task execution.
2. Keep existing endpoints only as compatibility wrappers where needed.
3. Keep Mongo-first for MVP because existing backend already uses Mongo.
4. Separate report generation and report analysis as distinct workflows.
5. Add real async task handling for deadline checks and long-running jobs.
6. Use existing agents/services first, then add only missing modules.

## 5. Existing Backend Components to Reuse
- `finpilot/agents/orchestrator_agent.py`
- `finpilot/agents/bookkeeping_agent.py`
- `finpilot/agents/expense_agent.py`
- `finpilot/agents/profit_agent.py`
- `finpilot/agents/gst_agent.py`
- `finpilot/agents/tax_savings_agent.py`
- `finpilot/agents/reconciliation_agent.py`
- `finpilot/services/ingestion.py`
- `finpilot/services/parsers/pdf_parser.py`
- `finpilot/services/calendar_engine.py`
- `finpilot/db/mongo.py`
- `finpilot/models/transaction.py`

## 6. Endpoint Strategy

### 6.1 Primary Module Endpoints
Profile:
- `POST /profile/create`
- `GET /profile/{user_id}`
- `PUT /profile/{user_id}`
- `DELETE /profile/{user_id}`

Bookkeeping:
- `POST /bookkeeping/upload-statement`
- `POST /bookkeeping/add-entry`
- `POST /bookkeeping/upload-invoice`
- `GET /bookkeeping/ledger/{user_id}`
- `PUT /bookkeeping/update-entry/{entry_id}`

Report:
- `POST /report/extract-fields`
- `POST /report/generate`
- `GET /report/status/{report_id}`
- `POST /report/analyze`
- `POST /report/validate`

Deadline:
- `POST /deadline/add`
- `GET /deadline/{user_id}`
- `DELETE /deadline/{deadline_id}`

Assistant:
- `POST /assistant/chat`

### 6.2 Supporting Endpoints
- `POST /ingest/pdf`
- `GET /health`

Compatibility policy:
- Existing legacy endpoints may remain during migration, but module endpoints are the primary contract.

## 7. Shared Workflow Registry

Profile tasks:
- `create_profile`
- `get_profile`
- `update_profile`
- `delete_profile`

Bookkeeping tasks:
- `bookkeeping_upload_statement`
- `bookkeeping_upload_invoice`
- `bookkeeping_add_entry`
- `bookkeeping_update_entry`
- `bookkeeping_get_ledger`

Report tasks:
- `report_extract_fields`
- `report_generate`
- `report_status`
- `report_analyze`
- `report_validate`

Deadline tasks:
- `deadline_add`
- `deadline_get`
- `deadline_delete`

Assistant tasks:
- `assistant_chat`

## 8. Data Model (Mongo Collections)
- `users`
- `profiles`
- `transactions`
- `invoices`
- `reports`
- `deadlines`
- `jobs`
- `notifications`

Key indexes:
- `transactions`: `user_id`, `date`
- `reports`: `user_id`, `status`, `created_at`
- `deadlines`: `user_id`, `due_date`, `status`
- `jobs`: `job_id`, `status`, `created_at`

## 9. Async and Automation Model
Phase-1 async jobs:
- statement parsing
- invoice parsing
- report generation
- deadline scanner
- notification dispatcher

Scheduler behavior:
- periodic deadline scan
- generate T-7, T-1, T-0 reminders
- suppress reminders for submitted reports
- persist notification attempts and status

## 10. Implementation Roadmap

### Phase 1
- Finalize this plan and use as backend source-of-truth.
- Add `/execute` router and task dispatcher service.
- Add unified request/response schemas.
- Implement initial tasks: profile CRUD, bookkeeping summary, assistant chat, deadline retrieval.

### Phase 2
- Add report field extraction and report generation pipeline.
- Add missing-fields workflow for user completion.
- Add report analysis and validation pipeline.

### Phase 3
- Add async jobs table/collection and `GET /jobs/{job_id}`.
- Add deadline worker and notification adapter.
- Add Gmail notification integration and optional calendar sync.

### Phase 4
- Prune redundant endpoints and keep compatibility wrappers only where needed.
- Add tests for contract, security masking, async behavior, and workflow correctness.

## 11. Definition of Done
- Module endpoints drive major backend workflows with shared service logic.
- Profile data is reusable and not repeatedly requested.
- Bookkeeping supports statement plus invoice plus manual entry flow.
- Report generator provides field-wise output and missing-fields list.
- Report analysis catches errors before submission.
- Deadline notifications run asynchronously and respect submitted status.
- Assistant responses stay within tax/finance/compliance scope.

## 12. Copy-Paste Prompt for Coding Agent
Use this prompt when delegating implementation to an agent:

"Read the complete backend codebase and refactor it into an execute-first architecture without breaking existing behavior. Reuse existing agents and services first, remove redundant endpoint logic, and keep one primary POST /execute control plane with task routing. Implement profiler, bookkeeping, report generation, report analysis, deadlines/calendar async automation, and assistant chat as cohesive modules backed by Mongo.

Profiler requirements: create/get/update/delete profile, mandatory tax fields validation, partial updates, encrypted sensitive IDs at rest, masked IDs in responses.

Bookkeeping requirements: bank statement ingestion, invoice ingestion for cash/off-bank cases, manual entries, categorized ledger, periodic reminders (daily/weekly/monthly).

Report generation requirements: accept report template input, extract fields, map profile+ledger data, produce missing-fields list, return structured field-wise output (A1/A2 style IDs, names, values, status).

Report analysis requirements: accept filled report JSON/PDF, detect missing fields, inconsistencies, and rule violations, return errors/warnings/suggestions.

Deadline module requirements: maintain deadlines/calendar, run async checks continuously, trigger reminders at T-7/T-1/T-0, support Gmail notifications, optionally sync calendar, skip reminders for already submitted reports.

Assistant requirements: domain-constrained to tax/finance/compliance, reject irrelevant topics.

Expose minimal supporting endpoints: GET /jobs/{job_id}, POST /ingest/pdf, GET /health. Keep old endpoints only as compatibility wrappers that call the same service layer.

Add tests for request contracts, async lifecycle, profile security masking, and end-to-end workflow correctness."
