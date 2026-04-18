# Next.js Frontend Architecture Plan for FinPilot AI CFO

## 1. Purpose

This document translates the current FastAPI backend into a clean Next.js frontend plan.
It covers:

- recommended frontend file structure
- page-by-page UI details
- backend endpoint mapping
- shared components and data flow
- how the UI should support the AI CFO workflow

The goal is to replace the current static HTML frontend with a modular Next.js app that is easy to extend, easier to maintain, and aligned with the backend’s agent-driven design.

---

## 2. Backend Structure Summary

The backend currently centers around these live modules:

### Core entry points

- `backend/main.py`
  - FastAPI application entry point
  - CORS setup
  - router registration
  - MongoDB initialization
  - voice agent mounting

### API routers

- `backend/finpilot/api/routers/users.py`
  - create/update user profile
  - profile summary retrieval
  - transaction listing

- `backend/finpilot/api/routers/ingest.py`
  - bank statement PDF upload and transaction extraction

- `backend/finpilot/api/routers/agents.py`
  - orchestration endpoint
  - dashboard insight endpoints
  - expense, profit, GST, bookkeeping, reconciliation, tax-savings views
  - action card generation

- `backend/finpilot/api/routers/calendar.py`
  - auto compliance calendar generation
  - compliance event retrieval

### Supporting layers

- `backend/finpilot/agents/`
  - business intelligence and analysis agents
- `backend/finpilot/services/`
  - ingestion and calendar engines
  - voice agent (STT, TTS, chat) in `voice_agent.py`
- `backend/finpilot/db/mongo.py`
  - MongoDB persistence layer
- `backend/finpilot/config.py`
  - environment-driven configuration

### What the frontend must support

The UI should expose these product capabilities:

- profile management
- bookkeeping and transaction review
- invoice and statement upload
- report generation and field completion
- report analysis and validation
- deadline tracking and reminders
- AI assistant chat
- dashboard insights and action cards

---

## 3. Recommended Frontend Stack

- **Framework:** Next.js App Router
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **State:** React Query or SWR for server data, lightweight local state for forms
- **Forms:** React Hook Form + Zod
- **Charts:** Recharts or ECharts
- **Tables:** TanStack Table
- **Calendar:** FullCalendar or React Big Calendar
- **Chat UI:** streaming message panel with markdown rendering

### UI direction

Use a polished finance-dashboard look:

- left sidebar navigation
- top summary bar
- KPI cards
- dense data tables
- action panels for AI suggestions
- clean form sections for profile and report filling
- strong empty/loading/error states

The current HTML frontend is already oriented around a dark, agent-testing dashboard. The Next.js version should keep that power-user feel but make it structured and production-ready.

---

## 4. Proposed Next.js File Structure

```txt
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   ├── loading.tsx
│   ├── error.tsx
│   ├── not-found.tsx
│   ├── (public)/
│   │   ├── page.tsx
│   │   ├── features/page.tsx
│   │   └── pricing/page.tsx
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── forgot-password/page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── profile/page.tsx
│   │   ├── bookkeeping/page.tsx
│   │   ├── reports/
│   │   │   ├── generate/page.tsx
│   │   │   ├── analyze/page.tsx
│   │   │   └── [reportId]/page.tsx
│   │   ├── deadlines/page.tsx
│   │   ├── assistant/page.tsx
│   │   ├── transactions/page.tsx
│   │   └── settings/page.tsx
│   └── api/
│       └── health/route.ts
├── components/
│   ├── layout/
│   │   ├── sidebar.tsx
│   │   ├── topbar.tsx
│   │   ├── page-shell.tsx
│   │   └── section-header.tsx
│   ├── dashboard/
│   │   ├── kpi-card.tsx
│   │   ├── action-card.tsx
│   │   ├── insight-panel.tsx
│   │   └── status-pill.tsx
│   ├── forms/
│   │   ├── profile-form.tsx
│   │   ├── statement-upload.tsx
│   │   ├── invoice-upload.tsx
│   │   ├── report-field-mapper.tsx
│   │   └── deadline-form.tsx
│   ├── tables/
│   │   ├── transactions-table.tsx
│   │   ├── ledger-table.tsx
│   │   └── report-issues-table.tsx
│   ├── chat/
│   │   ├── chat-window.tsx
│   │   ├── chat-input.tsx
│   │   └── chat-message.tsx
│   ├── calendar/
│   │   ├── deadline-calendar.tsx
│   │   └── deadline-chip.tsx
│   └── ui/
│       ├── button.tsx
│       ├── input.tsx
│       ├── textarea.tsx
│       ├── select.tsx
│       ├── modal.tsx
│       ├── drawer.tsx
│       ├── tabs.tsx
│       ├── badge.tsx
│       ├── card.tsx
│       ├── table.tsx
│       ├── toast.tsx
│       └── skeleton.tsx
├── lib/
│   ├── api-client.ts
│   ├── endpoints.ts
│   ├── query-client.ts
│   ├── formatters.ts
│   ├── validators.ts
│   └── constants.ts
├── hooks/
│   ├── use-auth.ts
│   ├── use-profile.ts
│   ├── use-bookkeeping.ts
│   ├── use-reports.ts
│   ├── use-deadlines.ts
│   └── use-assistant.ts
├── types/
│   ├── profile.ts
│   ├── transaction.ts
│   ├── invoice.ts
│   ├── report.ts
│   ├── deadline.ts
│   └── assistant.ts
├── styles/
│   └── tokens.css
├── public/
│   ├── logos/
│   ├── icons/
│   └── illustrations/
└── middleware.ts
```

---

## 5. Route and Page Map

### 5.1 Landing Page

- **Route:** `/`
- **File:** `app/page.tsx`

#### UI purpose

Introduce FinPilot as an AI CFO assistant for SMBs.

#### UI sections

- hero banner
- short product pitch
- 3 to 6 capability cards
- workflow preview
- trust/security notes
- CTA buttons for login and dashboard access

#### UI behavior

- show a polished public marketing page
- explain the product in simple business language
- guide users into the auth flow or demo dashboard

#### Backend dependency

- no heavy backend dependency required
- optional health ping to `/health`

---

### 5.2 Authentication Pages

#### Login

- **Route:** `/login`
- **File:** `app/(auth)/login/page.tsx`

##### UI sections

- email field
- password field
- remember me toggle
- login button
- forgot password link
- optional social sign-in buttons if introduced later

##### Behavior

- validate email and password
- show inline errors
- redirect to dashboard after success
- preserve session state

#### Register

- **Route:** `/register`
- **File:** `app/(auth)/register/page.tsx`

##### UI sections

- name
- email
- password
- confirm password
- business name
- business type selector
- submit button

##### Behavior

- collect a minimal profile on signup
- prefill the profile module after account creation
- optionally route users into profile completion

#### Forgot Password

- **Route:** `/forgot-password`
- **File:** `app/(auth)/forgot-password/page.tsx`

##### UI sections

- email field
- send reset link button
- confirmation message

##### Behavior

- single-step reset request
- generic success response to avoid account enumeration

---

### 5.3 Dashboard Home

- **Route:** `/dashboard`
- **File:** `app/(dashboard)/dashboard/page.tsx`

#### UI purpose

This is the operational command center for the CFO assistant.

#### UI sections

- KPI cards for revenue, expenses, profit, tax savings, pending deadlines
- “AI actions” panel from backend recommendations
- recent transactions list
- latest reports status
- compliance timeline teaser
- assistant quick prompt box

#### Behavior

- show a summary of the user’s financial health
- highlight urgent action cards first
- support drill-down to bookkeeping, reports, and deadlines

#### Backend endpoints used

- `GET /insights/{user_id}`
- `GET /actions/{user_id}`
- `GET /bookkeeping/{user_id}`
- `GET /profit/{user_id}`
- `GET /expenses/{user_id}`
- `GET /tax-savings/{user_id}`
- `GET /reconciliation/{user_id}`

#### Recommended widgets

- profit trend chart
- expense category donut chart
- ITC/tax savings highlight card
- submission readiness badge

---

### 5.4 Profile Page

- **Route:** `/profile`
- **File:** `app/(dashboard)/profile/page.tsx`

#### UI purpose

Store and edit reusable identity and business data once, then reuse it across reports.

#### UI sections

- personal info card
- business info card
- tax identity card
- bank account card
- save and edit controls
- profile completeness indicator

#### Behavior

- allow partial updates
- validate tax-related fields
- show what data is missing for reporting
- present read-only summary plus editable form sections

#### Backend endpoints used

- `POST /users/create`
- `GET /users/{user_id}/profile`
- `POST /users/{user_id}/profile`

#### UI detail notes

- use a multi-section form rather than one long page
- show completion percentage so users know what still needs input
- surface warnings for missing required tax fields

---

### 5.5 Bookkeeping Page

- **Route:** `/bookkeeping`
- **File:** `app/(dashboard)/bookkeeping/page.tsx`

#### UI purpose

Manage statements, invoices, manual entries, and the ledger.

#### UI sections

- statement upload card
- invoice upload card
- manual entry form
- transactions ledger table
- category filters
- reminders / sync status panel
- parsing progress and results section

#### Behavior

- upload a bank statement PDF
- show parsed transactions after processing
- allow users to correct or recategorize entries
- support invoice reconciliation against missing ledger items
- display update reminders for daily/weekly/monthly bookkeeping

#### Backend endpoints used

- `POST /ingest/pdf`
- `GET /transactions/{user_id}`
- future-facing bookkeeping endpoints from the architecture plan:
  - `POST /bookkeeping/upload-statement`
  - `POST /bookkeeping/add-entry`
  - `POST /bookkeeping/upload-invoice`
  - `GET /bookkeeping/ledger/{user_id}`
  - `PUT /bookkeeping/update-entry/{entry_id}`

#### UI detail notes

- show upload progress and extracted transaction count
- include confidence badges for auto-categorized items
- let users bulk edit categories
- provide “mark as cash transaction” or “manual adjustment” actions

---

### 5.6 Transaction Explorer Page

- **Route:** `/transactions`
- **File:** `app/(dashboard)/transactions/page.tsx`

#### UI purpose

Provide a dense searchable view of all parsed and manually entered transactions.

#### UI sections

- search bar
- date range filter
- category filter
- confidence filter
- sortable transactions table
- transaction detail drawer

#### Behavior

- search and inspect raw records
- support quick edits and review workflows
- expose transaction metadata for agent diagnostics

#### Backend endpoints used

- `GET /transactions/{user_id}`

---

### 5.7 Report Generator Page

- **Route:** `/reports/generate`
- **File:** `app/(dashboard)/reports/generate/page.tsx`

#### UI purpose

Transform profile and ledger data into a structured form or report draft.

#### UI sections

- report template selector
- file upload area for source forms/PDFs
- field-mapping preview
- “required fields” list
- missing input request panel
- generate draft button

#### Behavior

- extract field definitions from the target report
- map profile values into the report structure
- show unresolved or missing fields clearly
- create a draft output that can be reviewed before submission

#### Backend endpoints used

- future-facing architecture endpoints:
  - `POST /report/generate`
  - `POST /report/extract-fields`
  - `GET /report/status/{report_id}`
- profile and bookkeeping data sources:
  - `GET /users/{user_id}/profile`
  - `GET /bookkeeping/{user_id}`
  - `GET /transactions/{user_id}`

#### UI detail notes

- show a field-by-field checklist
- color code each field as filled, missing, or needs review
- allow users to jump directly to profile fields that are incomplete

---

### 5.8 Report Analysis Page

- **Route:** `/reports/analyze`
- **File:** `app/(dashboard)/reports/analyze/page.tsx`

#### UI purpose

Validate filled reports before submission.

#### UI sections

- report upload or draft selection panel
- analysis summary banner
- error table
- warning table
- suggestions panel
- validation status indicator

#### Behavior

- detect missing fields
- identify inconsistent values
- suggest corrections
- surface tax-rule validation issues
- present a ready/not-ready submission state

#### Backend endpoints used

- `POST /report/analyze`
- `POST /report/validate`

#### UI detail notes

- separate hard errors from soft warnings
- make suggestions actionable with one-click fixes where possible
- show whether the report can be submitted safely

---

### 5.9 Report Detail Page

- **Route:** `/reports/[reportId]`
- **File:** `app/(dashboard)/reports/[reportId]/page.tsx`

#### UI purpose

Display one report’s current state, extracted fields, validation status, and action history.

#### UI sections

- report header
- submission status timeline
- field completion matrix
- analysis results panel
- change history
- download/export actions

#### Behavior

- useful for reviewed reports or saved drafts
- allow users to revisit completed work without re-uploading everything

---

### 5.10 Deadlines Page

- **Route:** `/deadlines`
- **File:** `app/(dashboard)/deadlines/page.tsx`

#### UI purpose

Track compliance deadlines and notifications in a calendar-first layout.

#### UI sections

- calendar view
- upcoming deadlines list
- reminder configuration panel
- status chips for submitted / pending / overdue
- add deadline form

#### Behavior

- visualize T-7, T-1, and deadline-day reminders
- avoid duplicate reminders for already submitted tasks
- support calendar sync later if enabled

#### Backend endpoints used

- `POST /calendar/auto/{user_id}`
- `GET /calendar/events/{user_id}`
- architecture-plan endpoints:
  - `POST /deadline/add`
  - `GET /deadline/{user_id}`
  - `DELETE /deadline/{id}`

#### UI detail notes

- default to month view with a side list of critical items
- highlight upcoming deadlines in amber/red
- make the reminder interval configurable

---

### 5.11 Assistant Page

- **Route:** `/assistant`
- **File:** `app/(dashboard)/assistant/page.tsx`

#### UI purpose

Provide the user-facing conversational AI experience for tax, finance, and compliance.

#### UI sections

- chat message stream
- prompt suggestions
- context chips such as tax, GST, ledger, report, deadline
- file/context attachment area
- response citations or explanation blocks

#### Behavior

- focus queries on tax/finance/compliance only
- support natural language queries about profits, expenses, GST, and reports
- optionally link responses to dashboard insights or report actions

#### Backend endpoints used

- `POST /orchestrate/{user_id}`
- future-facing architecture endpoint:
  - `POST /assistant/chat`

#### UI detail notes

- show loading indicators while the agent is reasoning
- keep the conversation scoped to CFO work
- support follow-up prompts like “show me the category” or “fix this report field”

---

### 5.12 Settings Page

- **Route:** `/settings`
- **File:** `app/(dashboard)/settings/page.tsx`

#### UI purpose

Configure user preferences, reminders, and application behavior.

#### UI sections

- profile preferences
- reminder frequency settings
- notification delivery settings
- theme preferences
- API/environment status panel for admins

#### Behavior

- allow configurable reminder rules
- support future pluggable report formats
- store app-level preferences cleanly

---

## 6. Shared Layout Design

### Root layout

- **File:** `app/layout.tsx`
- loads global fonts, metadata, and theme providers
- includes top-level error boundaries and toast handling

### Dashboard layout

- **File:** `app/(dashboard)/layout.tsx`
- renders sidebar + topbar + content area
- protects authenticated routes
- keeps navigation consistent across operational pages

### Public layout

- keeps marketing/auth pages visually separated from the app shell

---

## 7. Shared Components

### Layout components

- `sidebar.tsx`
- `topbar.tsx`
- `page-shell.tsx`
- `section-header.tsx`

### Finance dashboard components

- `kpi-card.tsx`
- `action-card.tsx`
- `insight-panel.tsx`
- `status-pill.tsx`

### Data-entry components

- `profile-form.tsx`
- `statement-upload.tsx`
- `invoice-upload.tsx`
- `report-field-mapper.tsx`
- `deadline-form.tsx`

### Data display components

- `transactions-table.tsx`
- `ledger-table.tsx`
- `report-issues-table.tsx`
- `deadline-calendar.tsx`

### Assistant components

- `chat-window.tsx`
- `chat-input.tsx`
- `chat-message.tsx`

### UI primitives

- button, input, textarea, select
- modal, drawer, tabs, badge, card
- table, toast, skeleton

---

## 8. Data Flow From UI to Backend

The frontend should follow this pattern:

1. User opens a page such as Profile, Bookkeeping, or Assistant.
2. Page fetches backend data through a typed API client.
3. Data is normalized into page state or React Query cache.
4. User submits a form or triggers an action.
5. Frontend validates the payload with Zod.
6. Request is sent to FastAPI endpoint.
7. Backend agent/service executes the business logic.
8. UI updates the page state and shows success, warnings, or errors.

This keeps the frontend thin while preserving agent-driven backend behavior.

---

## 9. Backend-to-Frontend Endpoint Mapping

| Frontend Area | Backend Endpoint |
| --- | --- |
| Dashboard summary | `GET /insights/{user_id}` |
| Action cards | `GET /actions/{user_id}` |
| Profile view/edit | `POST /users/create`, `GET /users/{user_id}/profile`, `POST /users/{user_id}/profile` |
| Transaction history | `GET /transactions/{user_id}` |
| PDF statement upload | `POST /ingest/pdf` |
| Bookkeeping summary | `GET /bookkeeping/{user_id}` |
| Expenses diagnostics | `GET /expenses/{user_id}` |
| Profit analysis | `GET /profit/{user_id}` |
| GST analysis | `GET /gst/{user_id}` |
| Reconciliation | `GET /reconciliation/{user_id}` |
| Tax savings | `GET /tax-savings/{user_id}` |
| Orchestration chat | `POST /orchestrate/{user_id}` |
| Calendar generation | `POST /calendar/auto/{user_id}` |
| Calendar events | `GET /calendar/events/{user_id}` |
| STT (text from audio) | `POST /stt/transcribe` |
| STT streaming (real-time) | `WS /stt/stream` |
| TTS (audio from text) | `POST /tts/generate` |
| TTS streaming (real-time) | `WS /tts/stream` |
| Chat completions | `POST /chat/completions` |
| Voice agent (text + audio) | `POST /agent/respond` |
| Text translation | `POST /text/translate` |
| Health check | `GET /health` |

---

## 10. Page UI Guidelines

### Visual system

- use cards with subtle borders and elevation
- keep a strong contrast hierarchy for finance data
- reserve red for risk and amber for attention
- use green for savings and positive performance
- show dense but readable tables for transaction-heavy views

### Interaction rules

- every upload must show progress and result feedback
- every action should have an explicit loading state
- every AI response should be scannable, not a wall of text
- every missing required field should be visible where the user is working

### Empty states

- no profile yet → prompt to create one
- no transactions yet → prompt to upload a statement
- no deadlines yet → prompt to auto-generate calendar items
- no report yet → prompt to start the report generator

---

## 11. Recommended MVP Page Order

If building this incrementally, implement in this sequence:

1. landing page
2. auth pages
3. dashboard home
4. profile page
5. bookkeeping page
6. transactions page
7. report generator page
8. report analysis page
9. deadlines page
10. assistant page
11. settings page

This order gets the core finance workflow working first and leaves the assistant and automation polish for later.

---

## 12. Final Recommendation

The backend already supports the right building blocks for an AI CFO product:

- user profile persistence
- transaction ingestion
- orchestration intelligence
- bookkeeping analytics
- report support
- compliance calendar generation

The best frontend implementation is a Next.js app with:

- a dashboard shell
- route-based pages for each CFO workflow
- reusable form and table components
- a single typed API client for FastAPI
- strong AI workflow states for loading, missing data, and validation

This gives you a production-friendly frontend that matches the agent-driven backend without becoming overly fragmented.