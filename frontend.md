# Pocket CFO Frontend Requirements

## 1. Tech Stack
- Framework: Next.js (App Router)
- Language: JavaScript / React
- Styling: Tailwind CSS
- Authentication: NextAuth.js (Credentials Provider with bcryptjs)
- Database: MongoDB (Mongoose for bridging auth/users via `models/User.js`)
- Icons: Lucide React
- Fonts: Syne (Headings), DM Sans (Body)

## 2. Design System
- **Theme**: Dark Fintech
- **Base Background**: `#0D0F12`
- **Card Backgrounds**: `#111318`
- **Accents**: Amber (`#F59E0B`), Emerald (Profit/Success), Rose/Red (Loss/Urgent), Indigo (ITC/Taxes)
- **Patterns**: Background grid patterns `bg-[linear-gradient(to_right,#80808012_1px,transparent_1px)...]`

## 3. Core Pages & Routes

### Public Routes
- **`/`**: Root redirect logic based on session.
- **`/login`**: Split-panel design. Left brand panel, right auth form. Integrates `signIn('credentials')` and demo load functionality.
- **`/register`**: Split-panel design. Fields for Full Name, Email, Business Name, Phone, Password.

### Protected Routing
- A secure wrapper mapping `/dashboard` and its children strictly to authenticated sessions, exposing `backend_user_id`.

### Dashboard Ecosystem (`/dashboard`)
1. **Core Command Center (`/dashboard`)**:
   - Metrics: Revenue, Expenses, Net Profit, ITC Claimable.
   - Action Hub: Renders urgent/watch/opportunity alert cards.
   - **Quick SMS Ingest Panel**: Bottom fixed drawer to paste raw bank SMS text and post to the FastApi backend (`/ingest/sms`).

2. **Ledger Transactions (`/dashboard/transactions`)**:
   - Tabular grid fetching `/transactions/{user_id}`.
   - Live Search by party name.
   - Multi-filter (All, Credit, Debit).
   - Dynamic Confidence badges based on prediction thresholds.

3. **Financial Intelligence (`/dashboard/insights`)**:
   - Fetches from `/insights/{user_id}`.
   - Visual spending categorizations (pie/progress bars mapping max operational expenditure).
   - Comprehensive ITC Recovery analytical tables.
   
4. **GST & Tax console (`/dashboard/gst`)** *(Previously scaffolded pending strict bounds)*:
   - Evaluates automated discovery of recoverable structural taxes mapping to HSN bounds.

## 4. Shared Components
- **Sidebar Navigation**: Desktop and mobile integrated mapping paths to insights, transactions, and core layout.
- **ClientSessionProvider**: Global NextAuth hydration wrapper over the root `layout.js`.

## 5. Environment Variables mapped (`.env.local`)
- `MONGODB_URI`
- `NEXTAUTH_SECRET`
- `NEXTAUTH_URL`
- Thread limiting bindings for local environment stability (`NEXT_PRIVATE_WORKER_THREADS_LIMIT=1`)
