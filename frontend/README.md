# FinPilot Frontend - Next.js Implementation

A modern, production-ready Next.js frontend for the FinPilot AI CFO Assistant. Built according to the comprehensive Next.js Frontend Architecture Plan.

## 📋 Project Structure

```
frontend/
├── app/                           # Next.js App Router
│   ├── layout.tsx                 # Root layout with global styles
│   ├── page.tsx                   # Landing page
│   ├── loading.tsx                # Global loading state
│   ├── error.tsx                  # Global error boundary
│   ├── not-found.tsx              # 404 page
│   ├── (public)/                  # Public routes (landing, features)
│   ├── (auth)/                    # Authentication routes
│   │   ├── login/
│   │   ├── register/
│   │   └── forgot-password/
│   ├── (dashboard)/               # Protected dashboard routes
│   │   ├── layout.tsx             # Dashboard shell with sidebar/topbar
│   │   ├── dashboard/             # Main dashboard
│   │   ├── profile/               # Profile management
│   │   ├── bookkeeping/           # Statement and invoice management
│   │   ├── transactions/          # Transaction explorer
│   │   ├── reports/               # Report generation and analysis
│   │   ├── deadlines/             # Deadline tracking
│   │   ├── assistant/             # AI assistant chat
│   │   ├── jobs/                  # Background task tracking
│   │   └── settings/              # User settings
│   └── api/                       # API routes
│
├── components/                    # Reusable components
│   ├── layout/
│   │   ├── sidebar.tsx            # Navigation sidebar
│   │   ├── topbar.tsx             # Top navigation bar
│   │   └── page-shell.tsx         # Page wrapper with title/subtitle
│   ├── ui/
│   │   ├── button.tsx             # Button component
│   │   ├── input.tsx              # Input field
│   │   ├── textarea.tsx           # Text area
│   │   ├── card.tsx               # Card container
│   │   ├── badge.tsx              # Status badge
│   │   ├── modal.tsx              # Modal dialog
│   │   └── skeleton.tsx           # Loading skeleton
│   ├── dashboard/
│   │   ├── kpi-card.tsx
│   │   ├── action-card.tsx
│   │   └── insight-panel.tsx
│   ├── forms/                     # Form components
│   ├── tables/                    # Table components
│   └── chat/                      # Chat UI components
│
├── lib/                           # Utility functions
│   ├── api-client.ts              # Axios API client instance
│   ├── endpoints.ts               # API routes and task names
│   ├── query-client.ts            # React Query configuration
│   ├── validators.ts              # Zod validation schemas
│   ├── formatters.ts              # Format utilities
│   └── constants.ts               # App constants
│
├── hooks/                         # Custom React hooks
│   ├── use-auth.ts                # Authentication hook
│   ├── use-profile.ts             # Profile management
│   ├── use-bookkeeping.ts         # Bookkeeping operations
│   ├── use-reports.ts             # Report operations
│   ├── use-deadlines.ts           # Deadline management
│   ├── use-assistant.ts           # Assistant chat
│   └── use-jobs.ts                # Job tracking
│
├── types/                         # TypeScript type definitions
│   ├── profile.ts
│   ├── transaction.ts
│   ├── invoice.ts
│   ├── report.ts
│   ├── deadline.ts
│   ├── assistant.ts
│   └── job.ts
│
├── styles/
│   └── tokens.css                 # Design tokens and global styles
│
├── public/                        # Static assets
├── package.json                   # Dependencies
├── tsconfig.json                  # TypeScript configuration
├── next.config.js                 # Next.js configuration
├── tailwind.config.js             # Tailwind CSS configuration
├── postcss.config.js              # PostCSS configuration
├── .eslintrc.json                 # ESLint configuration
└── .gitignore                     # Git ignore rules
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ or Bun
- npm or yarn or bun package manager
- Backend API running on http://localhost:8000

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
# or
yarn install
# or
bun install

# Create .env.local file
cp .env.example .env.local

# Update API URL if needed (default: http://localhost:8000)
# NEXT_PUBLIC_API_URL=http://your-api-url:8000
```

### Development

```bash
# Run development server
npm run dev
# or
yarn dev
# or
bun dev

# Open http://localhost:3000 in your browser
```

### Build for Production

```bash
# Build the project
npm run build

# Start production server
npm start
```

### Type Checking

```bash
# Run TypeScript type checking
npm run type-check
```

### Linting

```bash
# Run ESLint
npm run lint
```

## 📚 Core Features

### Landing Page (`/`)
- Product overview and benefits
- Call-to-action buttons
- Feature showcase

### Authentication Routes
- **Login** (`/login`): User sign-in
- **Register** (`/register`): New account creation
- **Forgot Password** (`/forgot-password`): Password reset

### Dashboard (`/dashboard`)
- KPI cards (revenue, expenses, profit, tax liability)
- Recent transactions list
- Pending actions panel
- AI insights and recommendations

### Profile Management (`/profile`)
- Personal information form
- Tax information (PAN, GSTIN, etc.)
- Bank details (masked/secure)
- Address management

### Bookkeeping (`/bookkeeping`)
- Bank statement upload
- Invoice upload
- Automatic transaction parsing
- Sync status tracking

### Transaction Explorer (`/transactions`)
- Searchable transaction list
- Date range filtering
- Category filtering
- Confidence scoring for auto-categorized items

### Reports (`/reports`)
- Report template selection (ITR2, ITR3, ITR4, GSTR1, GSTR3B)
- Field extraction and mapping
- Missing field detection
- Report analysis and validation

### Deadlines (`/deadlines`)
- Calendar view of compliance deadlines
- Reminder configuration
- Status tracking (pending, submitted, overdue)
- Auto-generated deadline suggestions

### AI Assistant (`/assistant`)
- Domain-scoped chat interface
- Context-aware responses
- Finance/tax/compliance queries
- Quick action suggestions

### Background Jobs (`/jobs`)
- Job status tracking
- Progress indicators
- Error/warning details
- Retry capabilities

### Settings (`/settings`)
- Notification preferences
- Theme configuration
- Security settings
- Account management

## 🔌 Backend Integration

The frontend communicates with the backend via a unified `/execute` endpoint:

### Execute Request Contract
```typescript
interface ExecuteRequest {
  task_name: string;           // Name of the task to execute
  user_id: string;             // User identifier
  payload: Record<string, any>; // Task-specific payload
  mode: 'sync' | 'async';      // Execution mode
  idempotency_key?: string;    // Optional for deduplication
}
```

### Execute Response Contract
```typescript
interface ExecuteResponse {
  status: 'success' | 'accepted' | 'error';
  task_name: string;
  user_id: string;
  data?: any;                  // Task result
  errors?: string[];           // Error messages
  warnings?: string[];         // Warning messages
  correlation_id: string;      // Request tracking
  job_id?: string;             // For async tasks
}
```

### API Client Usage

```typescript
import { apiClient } from '@/lib/api-client';
import { TASKS } from '@/lib/endpoints';

// Execute a task
const response = await apiClient.execute({
  task_name: TASKS.PROFILE.GET,
  user_id: 'user-123',
  payload: { profile_id: 'profile-456' },
  mode: 'sync',
});

// Upload PDF
const result = await apiClient.uploadPDF(file, userId);

// Check job status
const job = await apiClient.getJobStatus(jobId);
```

## 🎨 Design System

### Colors (CSS Variables)
- `--bg`: #0D0F12 (Primary background)
- `--bg2`: #111318 (Secondary background)
- `--bg3`: #16191F (Tertiary background)
- `--border`: #1E2230 (Border color)
- `--amber`: #F59E0B (Warning/Attention)
- `--emerald`: #10B981 (Success/Positive)
- `--rose`: #F43F5E (Error/Danger)
- `--indigo`: #6366F1 (Primary accent)
- `--sky`: #38BDF8 (Info)
- `--text`: #E4E7EC (Primary text)
- `--muted`: #6B7280 (Secondary text)

### Typography
- **Display Font**: Syne (headers)
- **Body Font**: DM Sans (content)
- **Monospace Font**: DM Mono (code)

### Component Variants

**Button**: primary | secondary | danger | success
**Badge**: default | success | warning | error | info

## 📦 Key Dependencies

- **Next.js**: Full-stack React framework
- **React Query**: Server state management
- **React Hook Form**: Form state management
- **Zod**: Schema validation
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client
- **Recharts**: Chart library
- **TanStack Table**: Table component
- **FullCalendar**: Calendar widget

## 🔐 Security Considerations

1. **Sensitive Data Masking**: PAN, Aadhaar, and account numbers are masked in UI
2. **HTTPS**: Always use HTTPS in production
3. **Authentication**: Implement JWT or session-based auth
4. **CSRF Protection**: Use same-site cookies
5. **Rate Limiting**: Implement on backend API
6. **Input Validation**: All forms validated with Zod

## 📝 Environment Variables

Create `.env.local` file:

```
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Feature flags
NEXT_PUBLIC_ENABLE_VOICE_CHAT=true
NEXT_PUBLIC_ENABLE_PDF_UPLOAD=true
```

## 🤝 Contributing

1. Create feature branches from `main`
2. Follow TypeScript strict mode
3. Write components with JSDoc comments
4. Test responsive design
5. Commit with clear messages

## 📞 Support

For issues or questions:
- Check the Backend Status Report for API compatibility
- Review type definitions in `/types`
- Check existing hooks in `/hooks` for patterns
- Refer to the Next.js Frontend Architecture Plan

## 📄 License

Part of FinPilot AI CFO Assistant project.

---

**Last Updated**: April 2024
**Frontend Version**: 0.1.0
**Status**: Foundation Phase Complete - Ready for Feature Development
