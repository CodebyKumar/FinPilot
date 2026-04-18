# Report Integration Guide for Frontend

This guide explains how to wire the Next.js frontend to the backend report APIs for both:

- Comprehensive Report
- Financial Report

The goal is to keep the frontend clean, avoid conflicts, and use the backend as the source of truth.

## 1. What Already Exists

### Comprehensive Report
This is the broader report flow already available in the backend and should be used for report generation, analysis, validation, and preview screens.

Recommended backend routes:

- `POST /report/extract-fields`
- `POST /report/extract-fields-file`
- `POST /report/generate`
- `POST /report/generate-file`
- `GET /report/status/{report_id}`
- `GET /report/view/{report_id}`
- `GET /report/prefill/{user_id}`
- `POST /report/analyze`
- `POST /report/analyze-file`
- `POST /report/validate`

Frontend page:

- `frontend/app/(dashboard)/reports/page.tsx`

### Financial Report
This is the CA-style income-tax style financial report that should be generated after bookkeeping data is available.

Recommended backend routes:

- `POST /reports/financial/generate/{user_id}`
- `GET /reports/financial/download/{user_id}?format=html`

Frontend page:

- `frontend/app/(dashboard)/bookkeeping/page.tsx`
- optionally also `frontend/app/(dashboard)/reports/page.tsx` if you want manual access from the Reports page

## 2. Recommended UX Flow

### Flow A: Bookkeeping to Financial Report
Best flow for business users:

1. User uploads statement in Bookkeeping.
2. Bookkeeping summary loads.
3. Frontend calls `POST /reports/financial/generate/{user_id}` automatically.
4. Frontend shows a success state like:
   - Financial Report prepared
5. User can click:
   - Generate Financial Report
   - Download Financial Report

This keeps the report generation close to the source transaction data.

### Flow B: Dedicated Reports Hub
Use the Reports page for the comprehensive report lifecycle:

1. User selects report type.
2. User uploads a file or uses prefill data.
3. Frontend calls extract/generate/analyze/validate routes.
4. User previews report and downloads or submits later.

## 3. Frontend Files to Update

### Bookkeeping Page
File:
- `frontend/app/(dashboard)/bookkeeping/page.tsx`

Add:
- A button or action card for Financial Report
- An auto-trigger after bookkeeping success
- A download action for the generated financial report

Suggested behavior:
- After `apiClient.getBookkeepingLedger(userId)` succeeds, trigger financial report generation.
- Show a small panel with:
  - Generate Financial Report
  - Download Financial Report

### Reports Page
File:
- `frontend/app/(dashboard)/reports/page.tsx`

Use this page for the comprehensive report flow:
- Generate report
- Extract fields
- Validate report
- Analyze report
- Preview report

Do not mix the financial report here unless you want a shortcut action.

## 4. Suggested API Client Methods

If the frontend codebase uses `apiClient`, add methods for the financial report if they are not already present.

Example methods:

- `generateFinancialReport(userId: string)`
- `downloadFinancialReport(userId: string)`

Comprehensive report methods likely already exist or can follow the existing naming pattern:

- `extractReportFields(...)`
- `generateReport(...)`
- `analyzeReport(...)`
- `validateReport(...)`
- `getReportStatus(...)`
- `getReportView(...)`
- `getReportPrefill(...)`

## 5. UI Placement Recommendation

### Bookkeeping Page
Place the financial report actions near the bookkeeping summary section:
- After summary cards
- Near the raw response block
- Or as a separate action card titled `Financial Report`

### Reports Page
Keep the comprehensive report controls in the report action panel and preview grid.

## 6. Data Contract Notes

### Financial Report
The financial report backend currently expects transaction data already stored for a user.
If there are no transactions, the backend returns an error.

Important:
- Financial report values are computed from parsed transactions
- Bank statement upload must happen first
- The download endpoint returns HTML that can later be printed to PDF

### Comprehensive Report
The comprehensive report is report-driven, not just statement-driven.
It can use file input, extracted fields, validation, and preview data.

## 7. Safe Integration Pattern

To avoid merge conflicts and reduce churn:

- Update only the relevant Next.js page file
- Avoid editing the old standalone `index.html`
- Keep API calls inside the page component or a shared client module
- Prefer small UI additions instead of large refactors

## 8. Minimal Implementation Checklist

### For Financial Report
- Add a button in Bookkeeping page: `Generate Financial Report`
- Add a button: `Download Financial Report`
- On successful bookkeeping load, auto-call financial report generation
- Show returned status in the UI

### For Comprehensive Report
- Keep the current Reports page as the main entry point
- Ensure report generate/analyze/validate actions use the existing endpoints
- Keep file upload and preview flow intact

## 9. Expected Backend Endpoints Summary

### Comprehensive Report
- `POST /report/extract-fields`
- `POST /report/extract-fields-file`
- `POST /report/generate`
- `POST /report/generate-file`
- `GET /report/status/{report_id}`
- `GET /report/view/{report_id}`
- `GET /report/prefill/{user_id}`
- `POST /report/analyze`
- `POST /report/analyze-file`
- `POST /report/validate`

### Financial Report
- `POST /reports/financial/generate/{user_id}`
- `GET /reports/financial/download/{user_id}?format=html`

## 10. Final Recommendation

If you want the cleanest product structure:

- Use `Reports` page for the comprehensive report
- Use `Bookkeeping` page for the financial report
- Auto-generate the financial report after bookkeeping success
- Keep the download action visible in both pages if needed

This keeps responsibilities separated and avoids frontend conflicts.
