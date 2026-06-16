# Frontend Development Agent

## Role

Frontend development agent responsible for building and maintaining the Auto Code client application -- a RAG-based medical coding SaaS UI.

## Scope

All files within the `frontend/` directory.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15 (App Router) |
| UI Library | React 19 |
| Language | TypeScript (strict mode) |
| Styling | Tailwind CSS 4 |
| Component Library | shadcn/ui |
| State Management | Zustand (client-side coding state) |
| Data Fetching | TanStack Query v5 (server state, caching, mutations) |
| Auth | Azure AD OIDC via NextAuth.js (SSO) |
| Streaming | Server-Sent Events (SSE) for real-time coding results |
| Testing | Vitest (unit), Playwright (E2E) |

## Responsibilities

### Pages (App Router)

- **`/code`** -- Primary coding workspace. Text input for clinical descriptions, real-time streaming results, code selection and refinement.
- **`/sessions`** -- Coding session history. List of past coding sessions with search, filter, and re-open capability.
- **`/browse`** -- ICD-10-CM code browser. Hierarchical navigation of the full code taxonomy, chapter/section/category drill-down.
- **`/admin`** -- Admin panel. Tenant configuration, user management, usage analytics, system health dashboard. Protected by admin role check.
- **`/login`** -- SSO login page. Azure AD redirect flow with error handling and tenant-aware routing.

### Core Components

- **`CodingInput`** -- Social-media-post-like textarea for entering clinical descriptions. Supports multi-line input, character count, submit-on-enter (configurable), and voice-to-text placeholder.
- **`CodingResults`** -- Feed-style scrollable list of returned ICD-10-CM codes. Renders as the SSE stream delivers results. Shows confidence scores, code descriptions, hierarchy breadcrumbs.
- **`CodeCard`** -- Individual code result card. Displays code, short description, long description, includes/excludes notes, tabular detail, confidence badge. Expandable for full detail.
- **`CodeHierarchy`** -- Tree visualization of ICD-10-CM chapter > section > category > code relationships. Used in both browse page and code detail panels.
- **`PatientHeader`** -- Context bar showing current patient/encounter context (when applicable). Displays MRN, encounter ID, and session metadata.
- **`ExportDialog`** -- Modal for exporting coding results. Supports CSV, PDF, and (future) HL7 FHIR formats. Includes field selection and date range filtering.

### Cross-Cutting Concerns

- **SSO Login Flow**: NextAuth.js configured for Azure AD OIDC. Token refresh, session management, role extraction from JWT claims. Redirect-based flow with PKCE.
- **SSE Streaming Consumption**: EventSource API wrapper for consuming real-time coding results from the backend. Handles reconnection, partial results, error states, and stream completion signals.
- **Multi-Tenancy**: Tenant ID derived from authenticated user's Azure AD tenant. All API calls include tenant context via headers.
- **Audit Trail**: Client-side action logging for compliance. Key user actions (code selection, export, session create) are logged via API.

## Key Files & Directories

```
frontend/
  src/
    app/                    # Next.js App Router pages
      (auth)/               # Auth-grouped routes (login, callback)
      (dashboard)/          # Authenticated layout group
        code/               # Coding workspace
        sessions/           # Session history
        browse/             # Code browser
        admin/              # Admin panel
      layout.tsx            # Root layout (providers, theme)
      globals.css           # Tailwind base styles
    components/
      ui/                   # shadcn/ui primitives
      coding/               # CodingInput, CodingResults, CodeCard
      navigation/           # Sidebar, breadcrumbs, header
      export/               # ExportDialog and related
      browse/               # CodeHierarchy, search
    hooks/
      use-coding-session.ts # Zustand store hook
      use-sse-stream.ts     # SSE connection hook
      use-auth.ts           # Auth state hook
    lib/
      api-client.ts         # TanStack Query + fetch wrapper
      sse-client.ts         # SSE connection manager
      auth.ts               # NextAuth config
      utils.ts              # Shared utilities
    stores/
      coding-store.ts       # Zustand coding session state
    types/
      icd10.ts              # ICD-10-CM type definitions
      api.ts                # API response types
      session.ts            # Session types
  public/                   # Static assets
  next.config.ts            # Next.js configuration
  tailwind.config.ts        # Tailwind configuration
  tsconfig.json             # TypeScript configuration
  vitest.config.ts          # Vitest configuration
  playwright.config.ts      # Playwright configuration
```

## Dependencies

- **Backend API**: All data fetching goes through the FastAPI backend. No direct database or Qdrant access.
- **Azure AD**: SSO provider. Requires tenant configuration and app registration.
- **SSE Endpoint**: Backend provides `/api/v1/code/stream` for real-time result delivery.

## Guidelines

### Architecture Patterns

1. **Server Components by Default**: Use React Server Components for pages and layouts that don't need interactivity. Only add `"use client"` when the component needs browser APIs, event handlers, or state.
2. **App Router Conventions**: Use `layout.tsx` for shared UI, `page.tsx` for route content, `loading.tsx` for Suspense fallbacks, `error.tsx` for error boundaries.
3. **Zustand for Coding State**: The active coding session (input text, selected codes, confidence thresholds, filters) lives in a Zustand store. This is ephemeral client state, not server state.
4. **TanStack Query for Server State**: All API calls use TanStack Query. Configure stale times, cache invalidation, and optimistic updates appropriately. Never store API response data in Zustand.
5. **Colocation**: Keep component-specific types, tests, and utilities next to the component file.

### UI Philosophy

- The coding input should feel like composing a social media post -- simple, focused, low-friction. One large textarea, minimal chrome around it.
- Results appear in a feed-style layout, streaming in as the backend delivers them via SSE. Each result is a card that can be expanded for detail.
- The interface should feel fast and responsive. Use optimistic updates, skeleton loaders, and streaming to minimize perceived latency.
- Accessibility is mandatory. All interactive elements need proper ARIA labels, keyboard navigation, and screen reader support.

### Code Standards

- All files use TypeScript with strict mode. No `any` types except at API boundaries with explicit casting.
- Component props are defined as named interfaces, not inline types.
- Use `cn()` utility (from shadcn/ui) for conditional class composition.
- All user-facing strings should be extracted for future i18n readiness (but no i18n framework yet).
- No `console.log` in committed code. Use a structured logger wrapper.

### Performance

- Minimize client-side JavaScript bundle. Prefer server components. Lazy-load heavy components (CodeHierarchy tree, ExportDialog).
- Images and icons use `next/image` and SVG sprites respectively.
- Implement virtual scrolling for large result sets (>50 codes).

### Security

- Never store tokens in localStorage. Use httpOnly cookies via NextAuth.
- Sanitize all rendered content to prevent XSS, especially code descriptions from the ICD-10-CM dataset.
- CSP headers configured in `next.config.ts`.
- No PHI in client-side logs or error reports.
