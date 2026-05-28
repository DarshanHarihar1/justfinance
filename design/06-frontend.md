# Phase 6 — Frontend: Login, Upload, Review

> Goal: a TypeScript + Vite + React frontend with a deliberate, minimalist design system,
> covering the three "use it monthly" pages: Login, Upload, Review. Dashboard and
> Analytics are Phase 7. Settings is Phase 8.

## Prerequisites

- Phase 5 complete: backend endpoints work end-to-end.

## 6.1 Design language — minimalist & aesthetic

A small, opinionated vocabulary. The goal is something that looks like a refined
editor tool, not a SaaS dashboard.

### Principles

1. **Quiet by default.** No gradients, no shadows on resting state, no decorative icons.
   Color is a tool, not a texture.
2. **One accent.** A single accent color (a desaturated blue/teal). Category swatches are
   the only other source of color, used at low saturation in chart fills and category chips.
3. **Generous whitespace.** Page max-width 880–1080 px on desktop; vertical rhythm follows
   a 4 px grid; section gaps are 32 / 48 / 64 px.
4. **Typography over chrome.** Two type sizes for hierarchy in body content (`text-sm` for
   labels, `text-base` for content); numerics use a tabular-figure font feature.
5. **Tables, not cards, for lists of numbers.** Cards only for single-figure summaries.
6. **Motion is functional.** A 150 ms ease-out transition on hover/focus state changes.
   No page transitions, no entrance animations.

### Tokens

```css
/* src/styles/globals.css — Tailwind v4 theme via @theme */
@import "tailwindcss";

@theme {
  --color-bg:               #fafaf9;   /* warm off-white */
  --color-bg-elevated:      #ffffff;
  --color-bg-muted:         #f4f4f2;
  --color-border:           #e7e5e0;
  --color-border-strong:    #d6d3cb;
  --color-text:             #1a1a1a;
  --color-text-muted:       #6b6b67;
  --color-text-subtle:      #94948f;
  --color-accent:           #1f6f6a;   /* deep teal */
  --color-accent-soft:      #d8ebe9;
  --color-danger:           #b0413e;
  --color-warning:          #b58a1f;
  --color-success:          #4f7a3a;

  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;

  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 10px;
}

html { font-feature-settings: "tnum" 1, "cv11" 1; background: var(--color-bg); }
body { color: var(--color-text); font-family: var(--font-sans); }

/* Dark mode opt-in (Settings toggle in Phase 8). */
.dark {
  --color-bg:               #111110;
  --color-bg-elevated:      #1b1b1a;
  --color-bg-muted:         #19191808;
  --color-border:           #2a2a28;
  --color-border-strong:    #3a3a37;
  --color-text:             #ededea;
  --color-text-muted:       #a0a09b;
  --color-text-subtle:      #6c6c67;
  --color-accent:           #5aaea7;
  --color-accent-soft:      #1b3a37;
}
```

Tailwind v4 lets us reference these as `bg-[--color-bg]` or via aliases like
`bg-bg-elevated`. We don't add a Tailwind config for color — the `@theme` block is the config.

### Components (shadcn/ui scope)

We pull only what we need from shadcn into `src/components/ui/`. Initial set:

- `button` (variants: `primary`, `secondary`, `ghost`, `danger`)
- `input`
- `select`
- `dropdown-menu`
- `dialog`
- `toast` (sonner)
- `table`
- `skeleton`
- `tabs`

Anything else we build ourselves — fewer dependencies, more control.

### Iconography

`lucide-react`. Stroke width 1.5 throughout. 16 px in dense UI, 20 px in headers.

## 6.2 App structure

```
frontend/src/
├── main.tsx
├── App.tsx                          # router + QueryClient + global providers
├── routes.tsx                       # route table
│
├── lib/
│   ├── api.ts                       # typed fetch client
│   ├── auth.ts                      # login/logout/me + AuthGuard
│   ├── query.ts                     # QueryClient config
│   ├── currency.ts                  # formatINR(), formatDate(), etc.
│   └── cn.ts                        # className util (clsx + tailwind-merge)
│
├── components/
│   ├── ui/                          # shadcn-generated primitives
│   ├── layout/
│   │   ├── AppShell.tsx             # left rail + main content
│   │   ├── NavRail.tsx
│   │   └── PageHeader.tsx
│   ├── transactions/
│   │   ├── TransactionRow.tsx
│   │   ├── CategoryPicker.tsx
│   │   └── ReviewTable.tsx          # used on /review
│   └── upload/
│       ├── Dropzone.tsx
│       └── UploadStatus.tsx
│
├── pages/
│   ├── Login.tsx
│   ├── Upload.tsx
│   ├── Review.tsx
│   ├── Dashboard.tsx                # Phase 7
│   ├── Analytics.tsx                # Phase 7
│   └── Settings.tsx                 # Phase 8
│
├── types/
│   └── api.ts                       # mirrors the backend Pydantic schemas
│
└── styles/
    └── globals.css
```

## 6.3 Typed API client

A single file, fetch-based, returns typed promises. No SDK generation — the API surface
is small enough to maintain by hand.

```typescript
// src/lib/api.ts
import type { ParsedSummary, TransactionOut, CategoryOut,
              BulkCategorize, StatementOut, MappingOut } from "../types/api";

const BASE = import.meta.env.VITE_API_URL;

export class ApiError extends Error {
  constructor(public status: number, public body: unknown) {
    super(`API ${status}`);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Accept": "application/json",
      ...(init.body && !(init.body instanceof FormData) ? {"Content-Type": "application/json"} : {}),
      ...(init.headers ?? {}),
    },
  });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

export const api = {
  auth: {
    login:  (password: string) => request<void>("/api/auth/login",  { method: "POST", body: JSON.stringify({password}) }),
    logout: () =>                request<void>("/api/auth/logout", { method: "POST" }),
    me:     () =>                request<{authenticated: true}>("/api/auth/me"),
  },
  statements: {
    upload: (file: File) => {
      const fd = new FormData(); fd.append("file", file);
      return request<ParsedSummary>("/api/statements/upload", { method: "POST", body: fd });
    },
    list:   () =>          request<StatementOut[]>("/api/statements"),
    get:    (id: number) => request<StatementOut>(`/api/statements/${id}`),
    review: (id: number) => request<TransactionOut[]>(`/api/statements/${id}/review`),
    delete: (id: number) => request<void>(`/api/statements/${id}`, { method: "DELETE" }),
  },
  transactions: {
    list: (params: Record<string, string | number | boolean | undefined>) => {
      const q = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => v != null && q.set(k, String(v)));
      return request<{items: TransactionOut[]; total: number}>(`/api/transactions?${q}`);
    },
    categorize: (body: BulkCategorize) =>
      request<void>("/api/transactions/categorize", { method: "POST", body: JSON.stringify(body) }),
    patch: (id: number, body: Partial<TransactionOut> & { remember?: boolean }) =>
      request<TransactionOut>(`/api/transactions/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  },
  categories: {
    list: () => request<CategoryOut[]>("/api/categories"),
    // etc.
  },
  mappings: {
    list: () => request<MappingOut[]>("/api/mappings"),
    // etc.
  },
  // analytics: Phase 7
};
```

### TanStack Query setup

```typescript
// src/lib/query.ts
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, err) => {
        if (err instanceof ApiError && err.status === 401) return false;
        return failureCount < 2;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});
```

A global `onError` handler in the QueryClient redirects to `/login` on 401 and toasts other errors.

## 6.4 Auth guard & routes

```typescript
// src/routes.tsx
export const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  {
    element: <AuthGuard><AppShell><Outlet /></AppShell></AuthGuard>,
    children: [
      { path: "/",          element: <Navigate to="/upload" replace /> },
      { path: "/upload",    element: <Upload /> },
      { path: "/review/:statementId", element: <Review /> },
      { path: "/dashboard", element: <Dashboard /> },
      { path: "/analytics", element: <Analytics /> },
      { path: "/settings",  element: <Settings /> },
    ],
  },
]);
```

`AuthGuard` runs a `GET /api/auth/me` query on mount. While loading: a centered skeleton.
On 401: `<Navigate to="/login" replace />`. On success: renders children.

## 6.5 Login page

Minimal centered card. Single password field. Enter to submit.

```
┌──────────────────────────────────────────┐
│                                          │
│           Finance                         │
│                                          │
│   ┌────────────────────────────────┐     │
│   │  Password                      │     │
│   └────────────────────────────────┘     │
│                                          │
│            [   Continue   ]              │
│                                          │
└──────────────────────────────────────────┘
```

- The form posts `password` and on success navigates to `/upload`.
- On 401 → inline error text `Incorrect password.`
- On 429 → inline error text `Too many attempts. Try again in a few minutes.`
- No "forgot password" link; this is a personal app.

## 6.6 AppShell layout

Left rail (icon-only on narrow viewports, icon+label ≥ md):

```
┌───┬──────────────────────────────────────────┐
│ ⬆ │  <PageHeader title="Upload">             │
│ ★ │                                          │
│ ◑ │   <main>                                 │
│ ⚙ │                                          │
│   │                                          │
│ ⏻ │                                          │
└───┴──────────────────────────────────────────┘
```

Icons (lucide):

- Upload → `Upload`
- Review → `ListTodo`  (only shows a dot badge if any txn has `needs_review`)
- Dashboard → `LayoutDashboard`
- Analytics → `LineChart`
- Settings → `Settings`
- Logout at bottom → `LogOut`

The badge is fed by a small `useReviewCount()` hook that polls
`GET /api/transactions?needs_review=true&page_size=1` every 60s while the app is in the foreground.

## 6.7 Upload page

Single-screen, file-drop + status panel. No multi-step wizard.

```
┌──────────────────────────────────────────────────────┐
│ Upload statement                                     │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │                                                │  │
│  │    Drop your PhonePe statement PDF here        │  │
│  │             or click to browse                 │  │
│  │                                                │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Most recent uploads                                  │
│  ──────────────────                                   │
│  Apr 28 – May 28, 2026     116 txns   2 min ago      │
│  Mar 28 – Apr 27, 2026     104 txns   1 mo ago       │
└──────────────────────────────────────────────────────┘
```

Flow when a file is selected:

1. The dropzone collapses to a compact bar.
2. A status block shows:
   - "Parsing PDF…" (immediately)
   - "Categorizing 38 transactions…" (after upload returns; the count comes from `new_count - needs_review_count` decision tree)
   - "Done — 4 transactions need your input"  →  `[Review now]` primary button
   - or  "Done — all transactions categorized"  →  `[View dashboard]`
3. On error (non-PhonePe PDF, 422, etc.):
   - "We couldn't parse this. It looks like it might not be a PhonePe Transaction Statement." with a `Try another file` link.
4. On network 502/504 (Render cold start):
   - "Waking up the backend… this takes about a minute the first time."
   - Auto-retry once after 60s before surfacing an error.

The file is validated client-side: must be `application/pdf` and ≤ 10 MB.

## 6.8 Review page

The most important UX in the app. Goal: blast through 4–20 transactions in <60 seconds.

```
┌────────────────────────────────────────────────────────────────┐
│ ‹ Back to upload                       4 transactions to review │
│                                                                │
│ Date     Description                  Amount        Category   │
│ ─────────────────────────────────────────────────────────────  │
│ Apr 30   ******8216                  ₹70,000   [Transfers ▼]  │
│           Transfer to own account                              │
│ May 02   Paid (anonymous)             ₹2,260   [Select…   ▼]  │
│           OMO2605021…                                          │
│ May 18   ANURAG KANDULNA              ₹266      [Select…   ▼]  │
│           Received                                             │
│ May 18   Kaustubh Lande               ₹266      [Select…   ▼]  │
│           Received                                             │
│                                                                │
│ ☑ Remember these mappings                  [ Save all ]        │
└────────────────────────────────────────────────────────────────┘
```

Behaviors:

- The `Select…` dropdown is a search-as-you-type combobox. Recently-used categories at the top.
- Keyboard navigation: `↑/↓` between rows, `Tab` into the picker, `1–9` keys jump to the first 9 categories.
- "Remember these mappings" is on by default — exactly per the original plan.
- On `Save all`, we call `POST /api/transactions/categorize` with the full set, then navigate back to the upload page with a toast: `4 transactions categorized.`
- Cascading magic: when the same `merchant_normalized` appears on multiple rows (e.g., several `******1492` entries), labeling one of them auto-fills the rest in the table. (Frontend-side echo of the backend cascade in §5.5.)
- If the user has self-transfers in the review list, those rows pre-fill `Transfers` and are visually muted (gray) — the user can still change them but the default is correct.

The review table fetches data via:

```
GET /api/statements/:statementId/review
```

Optimistic UI: on `Save all`, the rows immediately disappear and the parent badge count drops. If the call fails, we restore and toast an error.

## 6.9 Loading, empty, error states

For every fetching surface:

| State | UI |
|-------|----|
| Loading | Skeleton rows matching the final layout. Never spinners on full screens. |
| Empty (e.g., no uploads yet) | Centered, single-sentence "Upload your first statement to get started." with the primary action button. |
| Error | Compact card with the message + a `[Retry]` button. No raw error JSON. |

## 6.10 Number / date / currency formatting

- All currency: `formatINR(d: Decimal) → "₹1,23,456"` using `Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })`. Two-decimal precision is used only on the transaction detail / Review screen where exact ₹.paise matters.
- Dates: `formatDate(d: Date | string)` → `"May 28"` for current year, `"May 28, 2025"` for prior years.
- Time: `formatTime(t: string)` → `"7:30 PM"`.

These are the only formatting helpers; components must use them — no inline `toLocaleString`.

## 6.11 Definition of done

- [ ] `pnpm dev` boots; `/login` renders.
- [ ] Logging in lands on `/upload`.
- [ ] Uploading the sample PDF shows the status flow → ends on Review or "all categorized" copy.
- [ ] Review page lists transactions; manual categorization with `Remember` saves to backend and visible toast confirms.
- [ ] Logging out clears the cookie and redirects to `/login`.
- [ ] Lighthouse mobile score ≥ 90 on Performance and Accessibility.
- [ ] Tab-order through the Review table is sensible; `1–9` shortcuts work for category selection.
- [ ] No third-party CSS — the only stylesheet is `globals.css` plus per-component utility classes.
- [ ] No `console.log` in production build.

## 6.12 Risks / open questions

- **Cookie cross-site.** In prod, both apps are on different domains. Backend must set `SameSite=None; Secure` on the cookie; frontend always sends `credentials: "include"`. Verified once at deploy time.
- **Cold-start UX.** The first request after 15 min idle takes ~60s. The Upload page's pre-flight `GET /healthz` (fired on mount) primes the backend so the actual upload feels fast.
- **Inline emoji in category icons.** Some Android browsers render these inconsistently. Acceptable — we can swap to lucide icons + CSS background colors in a future polish pass.
- **Tailwind v4** is recent; if it's broken in CI, downgrade to v3 (`tailwind.config.ts` + plugin-only config). The token names above carry over unchanged.
