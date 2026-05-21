---
# SKILL.md — Frontend Reference
name: frontend
description: Use as a repo knowledge skill for the Optimize Financial Review frontend — React + Vite + TypeScript app under frontend/. Covers the design system (Newsreader serif + IBM Plex + ember/moss/rust palette), routing, page screens, components, mock-data state, auth shell, and the design-fidelity rules that came from the Claude Design handoff.
---

# Optimize Financial Review · Frontend

## Purpose

Use this skill as system knowledge for the **review-side frontend** that sits next to the bounded pipeline backend ([[agents]]). The frontend is an internal operational UI for reviewers to inspect Agent-5 output, verify evidence, approve/reject signals, and monitor pipeline cost/health.

The visual design is a port of an HTML/CSS/JS prototype produced by Claude Design (claude.ai/design) under the working name **"Optimize Financial Review"**. The mark, type pairing (Newsreader + IBM Plex), and ember/moss/rust palette are **original** — they are intentionally distinct from optimize.ca's branding and can be swapped later by editing the `Logo` / `Wordmark` components and CSS custom properties in `frontend/src/styles/globals.css`.

Do not treat this surface as a marketing site. It is internal review tooling. Confidentiality rules from the backend apply: do not surface raw transcript content into anything that gets logged, exported, or analytics-tagged.

## Current State

The frontend lives entirely under `frontend/`. It is **fully wired to mock data** today — there is no live API client. The placeholder API/hooks scaffolding that previously lived under `src/api/`, `src/hooks/`, and `src/auth/permissions.ts` was removed during the design implementation; reintroduce a real API layer only when wiring to the backend.

Stack:

- React 18 + TypeScript (strict) + Vite 5.
- React Router v6 (`createBrowserRouter`).
- No state library — local component state plus two small React contexts (`AuthProvider`, `SignalsProvider`).
- No ESLint; `npm run lint` is `tsc --noEmit`.
- No CSS framework; one hand-written stylesheet at `src/styles/globals.css` using CSS custom properties and `oklch()` color.

Build status: `npm run lint` and `npm run build` both pass cleanly; production bundle is ~260 KB JS / 21 KB CSS gzipped to ~81 KB / 5 KB.

## File Layout

```
frontend/
├── index.html                          # Google Fonts preconnect + Newsreader/IBM Plex link
├── package.json                        # react, react-dom, react-router-dom, lucide-react
├── tsconfig.json                       # strict, jsx: react-jsx, moduleResolution: Node
├── vite.config.ts
└── src/
    ├── main.tsx                        # ReactDOM root, RouterProvider, imports globals.css
    ├── App.tsx                         # Wraps <Outlet/> in AuthProvider + SignalsProvider
    ├── vite-env.d.ts
    ├── styles/
    │   └── globals.css                 # ~830 lines — full design system, all class rules
    ├── data/
    │   ├── mockData.ts                 # Typed mock transcripts/turns/signals/pipelineSteps/activity
    │   └── SignalsStore.tsx            # Signals context + useSignals() hook
    ├── auth/
    │   └── AuthProvider.tsx            # In-memory AuthUser context + useAuth() hook
    ├── routes/
    │   └── router.tsx                  # Route tree (see below)
    ├── components/
    │   ├── AppShell.tsx                # Auth guard + Sidebar + <main>/<Outlet>
    │   ├── Sidebar.tsx                 # Nav items, user footer, sign-out
    │   ├── SignalCard.tsx              # Inline-editable signal card for transcript detail
    │   └── primitives.tsx              # Logo, Wordmark, TopBar, KPI, Section, Btn, Field,
    │                                   # Sparkline, BarRow, Money, Tok, StatusPill, ReviewPill,
    │                                   # EvidencePill, TypePill
    └── pages/
        ├── LoginPage.tsx               # Split-pane login + Pipeline status ticker
        ├── DashboardPage.tsx           # KPIs, 14-day cost spark, status bars, activity, queue
        ├── LibraryPage.tsx             # Transcripts table — search/filter/sort
        ├── TranscriptDetailPage.tsx    # Transcript turns ↔ Agent 5 signal cards w/ quote flash
        ├── SignalReviewPage.tsx        # Cross-transcript review — cards + table view
        ├── PipelineRunPage.tsx         # 5-step timeline + cost composition
        ├── UploadPage.tsx              # Drag-drop + simulated processing progress
        ├── ExportsPage.tsx             # Public final-schema export config + CSV/JSON/JSONL preview
        └── AnalyticsPage.tsx           # Cost/usage aggregate — per-step table + model mix
```

## Design System

Defined entirely in `src/styles/globals.css` via CSS custom properties on `:root`. **Do not introduce a CSS-in-JS library, Tailwind, or a component framework** without explicit user direction — the design is built around hand-rolled `oklch()` tokens and class-based selectors.

Tokens (`--*`):

- **Color (ink/paper):** `--ink` (deep navy), `--ink-2`, `--slate`, `--slate-2`, `--hair` (hairline border), `--hair-2`, `--paper`, `--paper-2`.
- **Accent:** `--amber` (ember accent for "in flight"/warning), `--moss` (drivers, approved, success), `--rust` (blockers, rejected, failure).
- **Type:** `--serif` (Newsreader, used for display titles + signal quotes + signal categories + rank numerals), `--sans` (IBM Plex Sans, UI default), `--mono` (IBM Plex Mono, all numeric/code/IDs/timestamps).
- **Geometry:** `--radius` (10px), `--radius-sm` (6px), `--shadow-card`, `--density` (multiplier on body font-size).

Class conventions:

- **Layout primitives:** `.shell`, `.sidebar`, `.main`, `.topbar`, `.section`, `.card`, `.grid-2`, `.grid-2--asym`, `.toolbar`.
- **Typography utilities:** `.mono`, `.small`, `.slate`, `.strong`, `.eyebrow` (uppercase metadata label), `.lbl` (smaller eyebrow), `.link` (underlined inline button-as-link).
- **Pills & tags:** `.pill` + modifier (`.pill--moss`, `.pill--amber`, `.pill--rust`, `.pill--slate`, `.pill--ghost`) for status; `.tag` + modifier (`.tag--ink`, `.tag--ghost`, `.tag--moss`, `.tag--rust`) for evidence/type chips.
- **Buttons & inputs:** `.btn` (`.btn--ghost`, `.btn--full`), `.input` (`.input--search`, `.input--inline`, `.input--area`), `.select`, `.seg` / `.seg__opt` (segmented control), `.iconbtn`.
- **Signal card:** `.signal` + `.signal--driver` / `.signal--blocker` (left rail color) + `.signal--approved` / `.signal--rejected` (border + bg) + `.signal__rank-n` (huge serif numeral) + `.signal__quote` (italic Newsreader blockquote with left rule) + `.signal__actions` / `.sbtn` (`.sbtn--ok`, `.sbtn--bad`, `.sbtn--flag`).
- **Tables:** `.t` (`.t--lib` for the transcripts library row treatment), `.trow` (clickable rows), `.row-sum` (footer total).
- **Pipeline & misc:** `.pipe` / `.pipe__step` (numbered step row), `.kpis` / `.kpi`, `.barrow` (label/track/value row), `.callout` (`.callout--soft`), `.drop` / `.drop--on` (upload dropzone), `.ticker` (login pipeline activity), `.turn` / `.turn--adv` / `.turn--cli` / `.turn--quoted` / `.turn--flash` and `.quote` / `.quote--hl` (transcript viewer).

The `:root` variables are the **only** intended theming surface. The prototype's "Tweaks panel" (live accent/density swap) was intentionally not ported — it is a design-iteration helper, not a production feature. If theming is needed later, mutate `document.documentElement.style.setProperty("--amber", …)` etc., same as the prototype did.

A `@media (max-width: 1100px)` block collapses multi-column grids to single-column and hides the login right plate. There is no mobile-first treatment beyond that breakpoint; this is desktop tooling.

## Routing

Defined in `src/routes/router.tsx`. Single `App` shell wraps the entire tree with `AuthProvider` + `SignalsProvider`. Inside that, two layout branches:

- `/login` — `LoginPage`, no shell chrome.
- Everything else — `AppShell` (sidebar + main), guarded by `useAuth().user`; unauthenticated visitors are redirected to `/login`.

| Route                     | Page                  | Notes                                                  |
| ------------------------- | --------------------- | ------------------------------------------------------ |
| `/login`                  | `LoginPage`           | Split pane. Demo flow + role toggle. Redirects to `/dashboard` on submit. |
| `/`                       | →                     | `<Navigate to="/dashboard" replace/>`                  |
| `/dashboard`              | `DashboardPage`       | KPIs, 14-day spark, status bars, activity, today's queue. |
| `/transcripts`            | `LibraryPage`         | Filterable/sortable list; click row → detail.          |
| `/transcripts/:id`        | `TranscriptDetailPage`| Transcript turns ↔ signal cards w/ click-to-flash.     |
| `/review`                 | `SignalReviewPage`    | Cross-transcript review; cards + table toggle.         |
| `/pipeline` `/pipeline/:id` | `PipelineRunPage`   | 5-step timeline + cost composition.                    |
| `/upload`                 | `UploadPage`          | Drag-drop with simulated progress.                     |
| `/analytics`              | `AnalyticsPage`       | Per-step cost table + model mix.                       |
| `/exports`                | `ExportsPage`         | Final-schema export config + preview.                  |
| `*`                       | →                     | Fallback → `/dashboard`.                               |

Navigation between pages is `useNavigate()` (programmatic) plus `<NavLink>` in `Sidebar.tsx`. The sidebar's active state comes from `NavLink`'s `({isActive}) => …` callback, not from any custom route-matching logic.

## State

Two contexts only. Nothing in localStorage, no global store, no React Query.

- **`AuthProvider`** (`src/auth/AuthProvider.tsx`) — holds an in-memory `AuthUser { name, role, email } | null`. `signIn(user)` and `signOut()` mutate it. `useAuth()` is the consumer hook. Refreshing the tab signs the user out — this is intentional for the prototype; persistence belongs to a real auth backend.
- **`SignalsProvider`** (`src/data/SignalsStore.tsx`) — seeds from `mockData.signals` and exposes `signals`, `setSignals`, `updateSignal(id, patch)`. Both `TranscriptDetailPage` and `SignalReviewPage` read/write the same array, so approving a signal on one surface is reflected on the other.

All other data (transcripts, transcript turns, pipeline steps, activity) is read directly from `src/data/mockData.ts` — these arrays are immutable for the lifetime of the app.

## Mock Data

`src/data/mockData.ts` is the single source for everything the UI renders. Exported types match the public-facing pipeline schema described in [[agents]] (see the "Final Formatting" section):

- `Transcript` — id, name, status, drivers/blockers counts, cost/tokens/calls/retries, review state, advisor, client.
- `TranscriptTurn` — `t` (timestamp string `HH:MM:SS`), `who` (`Advisor` | `Client`), `name`, `text` (verbatim).
- `Signal` — `type` (`driver` | `blocker`), `rank` (1–N within type), `category`, `quote` (verbatim advisor quote), `timestamp`, `evidence` (`explicit` | `implied`), `rationale`, `status` (`pending` | `approved` | `rejected`), optional `flag`.
- `PipelineStep` — step number, name, model, prompt version, retries, latency, tokens in/out, cost.
- `ActivityEntry` — id, who, when, action, n.

**Showcase transcript:** `TR-2041` (Hartman-Greer · Q2 Review) is the only transcript that has full turn data and a populated signals array. Other transcript IDs have summary metadata only — opening their detail page will still render the `TR-2041` turn list and signal cards. When wiring real data, replace the static `signals` import in `SignalsStore` and load turns + signals by `transcript_id`.

The 8 seeded signals map 1:1 to `TR-2041`'s turns by timestamp, so the `TranscriptDetailPage` flash-highlight works out of the box: clicking a signal's `⤴ 00:01:48` button scrolls the transcript pane to that turn and flashes the quote.

## Components

### Primitives (`src/components/primitives.tsx`)

All visual atoms live here. None of them read context — they are pure props-in / JSX-out. When reaching for a primitive:

- `Logo` / `Wordmark` — the original O-glyph mark and wordmark. Edit these (plus `--ink` / `--paper` in CSS) to swap branding.
- `TopBar({title, subtitle, right})` — page header with serif title; every page uses this.
- `Section({eyebrow, title, right, children})` — content block with eyebrow + serif H2.
- `KPI({label, value, sub, accent})` — KPI card with serif numeral; pass `accent` as a CSS var (e.g. `"var(--amber)"`) to color the value.
- `Btn({kind, full, …})` — `kind: "primary" | "ghost"`. Defaults to primary (filled `--ink`).
- `Field({label})` — wraps any input with an uppercase eyebrow-style label.
- `Sparkline({points, color, w, h})` — pure SVG line + area-fill. No dependency.
- `BarRow({label, value, max, color})` — three-column row used in status breakdowns and cost composition.
- `Money({value, big})` — formats to `$X.XXXX` in mono.
- `Tok({value})` — formats to locale-grouped integer in mono.
- `StatusPill({status})` — `completed | running | queued | failed`.
- `ReviewPill({state})` — `pending | approved | rejected | —`.
- `EvidencePill({kind})` — `explicit` (ink) or `implied` (ghost).
- `TypePill({type})` — `driver` (moss) or `blocker` (rust).

### Sidebar (`src/components/Sidebar.tsx`)

Nav items live in a local `const items` array — add a route by adding an entry there *and* a `<Route>` in `router.tsx`. The sign-out button calls `useAuth().signOut()` then `navigate("/login")`.

### AppShell (`src/components/AppShell.tsx`)

Two-line auth guard plus the `.shell` grid. If the auth model changes (e.g. role-based redirects, loading states), this is the single place to add them.

### SignalCard (`src/components/SignalCard.tsx`)

Editable signal card used only on `TranscriptDetailPage`. Click the category to inline-edit, click the rationale paragraph to inline-edit, click the quote or the `⤴ timestamp` button to fire the parent's `onJump` (which flashes the transcript turn). The approve/reject/follow-up/edit-category buttons mutate via `onUpdate`.

`SignalReviewPage` does **not** use `SignalCard` — it renders its own inline card markup because it shows a non-editable category and adds an "open in context" link instead of jump-to-quote. If you find yourself duplicating signal-card markup yet again, consider extracting a shared `BaseSignalCard` then layering editing/jumping behaviors on top.

## Page Behaviors

A few behaviors that aren't obvious from the file names:

- **`DashboardPage`** — the 14-day cost trend is `Math.random()`-walked in a `useMemo([])`, so it changes once per session, not per render. Replace with real timeseries from the backend later.
- **`LibraryPage`** — the toolbar's three selects + search filter are all `useState` strings combined inside one `useMemo(rows, [q, status, review, sort])`. Sort options are `date` (default, by `uploaded` desc), `cost`, `drivers`.
- **`TranscriptDetailPage`** — `turnRefs` is a `useRef<Record<ts, HTMLDivElement | null>>`. `jumpTo(ts, signalId)` sets `parentElement.scrollTop = el.offsetTop - 80` and clears the flash after 1.8 seconds. `renderTurnText` finds the first signal whose `quote` is a substring of the turn `text` and wraps it in a `<mark className="quote">`. **Quote matching is exact substring** — if backend quote text drifts from transcript text by even one character, the highlight stops working.
- **`SignalReviewPage`** — segmented control toggles between card grid and a flat table. The "open in context" button hard-codes `/transcripts/TR-2041` because that's the only transcript with detail data; un-hardcode this once signals carry their own `transcript_id` into review.
- **`PipelineRunPage`** — the retry callout only appears under step 2 because the mock data has retries on step 2. When wiring real data, every step that has retries should show the callout.
- **`UploadPage`** — the progress is `setTimeout`-driven fakery (`[22, 38, 55, 68, 80, 92, 100]` percentages at 500 ms each). Replace with real `POST /api/transcripts` + polling once the backend ingestion endpoint exists.
- **`ExportsPage`** — preview rows come from the first 4 entries of `signals` (mock state). The "Download.{fmt}" button is non-functional. The included-fields list mirrors the **public final schema** documented in [[agents]] (`transcript_id`, `item_type`, `rank`, `category`, `advisor_quote`, `timestamp`, `evidence_strength`, `rationale`) — keep it in sync if the backend public schema changes.
- **`AnalyticsPage`** — model mix percentages are hardcoded. Wire to the `llm_usage_events` aggregation endpoint once it exists.

## Wiring to the Backend

Today the frontend is mock-only. To connect to the FastAPI backend described in [[agents]]:

1. Add a thin client module (suggest `src/api/client.ts` returning a fetch wrapper with the backend base URL from `import.meta.env.VITE_API_BASE`).
2. Replace the `mockData` imports in each page with `useQuery`-style hooks (React Query is not currently a dependency; add it before pulling it in).
3. Map the backend final-formatter artifact envelope (`{transcript_id, agent_name, pipeline_step, created_at, output_schema, output}`) into the `Signal` shape — `output_schema = "FinalSignal[]"` is the public-safe payload.
4. Keep `SignalsProvider` as the local optimistic-update layer; the approve/reject actions there should fire a `PATCH /signals/:id/review` and roll back on failure.
5. Auth — replace `AuthProvider`'s in-memory state with whatever the backend uses (session cookie, JWT, etc.). The `useAuth` interface should stay the same so consumers don't change.

Hard rules from [[agents]] that the frontend must respect:

- Never log, render, or analytics-tag raw transcript content outside the dedicated transcript viewer pane.
- Never expose candidate / ranked / rejected signals to non-reviewer roles — Agent 5 final output is the only public surface. Today the frontend has no role-gating; add it when wiring real auth.
- The export schema is fixed at 8 fields. Do not introduce earlier-agent metadata (segment scores, intermediate ranks, prompt names) into any export flow.

## Conventions

- **TypeScript strict** — never use `any`. Use the typed mock-data exports as the canonical shape; if you need a new shape, add it to `mockData.ts` (or a sibling types file once real APIs land).
- **No new emojis or comments unless asked** — the existing UI uses a small set of glyph icons (`▦ ≡ ◔ ⌾ ↥ ◐ ↗ ⤴ ✓ ✕ ⚑`) baked into the design. Keep them; don't introduce a real icon library when adding a nav item or button (`lucide-react` is installed as a dependency carried over from the prior placeholder, but is unused — feel free to drop it next time `package.json` is touched).
- **Don't add files Just In Case** — page components should call primitives directly. Resist creating per-page CSS files or per-page hook files until duplication actually shows up.
- **Density / responsive** — assume ≥ 1100 px desktop. The single existing media query is intentional; do not introduce a mobile breakpoint without a product reason.
- **No comments in code** explaining what something does. Identifiers carry their meaning. Only write a comment when the *why* is non-obvious.

## Commands

Run from `frontend/`:

```powershell
npm install                 # if node_modules missing
npm run dev -- --host 0.0.0.0
npm run lint                # tsc --noEmit (no ESLint)
npm run build               # tsc && vite build  → dist/
```

`make dev` from the repo root brings up postgres, redis, backend, worker, and frontend via Docker Compose; the frontend service mounts the Vite dev server.

## Implementation Checklist

Before changing the frontend UI:

- Read `frontend/src/styles/globals.css` — the design system class names are the contract; reuse them before inventing new ones.
- Check `frontend/src/components/primitives.tsx` for an existing atom before writing a new component.
- If the change touches signal review behavior, decide whether it belongs on `TranscriptDetailPage` (context-aware, editable, transcript-anchored) or `SignalReviewPage` (cross-transcript, filter-driven, table-or-cards). Don't duplicate.
- If the change touches data shape, update `frontend/src/data/mockData.ts` types first, then propagate.
- Run `npm run lint && npm run build` before reporting done — TypeScript strict catches most issues.
- For visible UI changes, also run the dev server and click through the affected route. `npm run lint` verifies types, not feature correctness.
