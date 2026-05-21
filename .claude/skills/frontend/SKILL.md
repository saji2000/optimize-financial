---
# SKILL.md — Frontend Reference
name: frontend
description: "Use as repo knowledge for the Optimize Financial Review frontend: React + Vite + TypeScript app under frontend/, hybrid API/mock data mode, VITE_API_BASE/VITE_DATA_MODE, review UI routing, typed data mappers, upload flow, SignalsProvider/DataProvider state, design system, and frontend build/smoke checks."
---

# Optimize Financial Review Frontend

## Purpose

Use this skill for frontend work under `D:\development\optimize-financial\frontend`.

The frontend is an internal reviewer tool for inspecting Agent-5 final signals, reviewing evidence in prepared transcript turns, monitoring pipeline status/cost, uploading transcripts, and previewing public exports. It is not a marketing site.

Confidentiality rules apply: do not render raw transcript text outside the transcript viewer, do not log transcript text, and do not include transcript content in analytics/export views beyond the public final signal fields.

## Current State

The app now uses a frontend-first hybrid data layer:

- App auth is real, not demo-only: `src/pages/LoginPage.tsx` submits username/password to the backend, and signed-in users receive a bearer token.
- The only configured local user is `curtis`. The plaintext password is intentionally not stored in frontend code or documented in repo guidance; the backend verifies it with a salted PBKDF2-SHA256 hash.
- Non-authenticated users cannot see logged-in pages. `AppShell` checks `AuthProvider.user` before mounting `DataProvider` and `SignalsProvider`.
- Backend remains the factual source for uploaded transcripts, prepared turns, final Agent-5 signals, and pipeline status.
- Local demo enrichment preserves polished advisor/client/duration/review metadata for presentation.
- API-backed transcript and pipeline cost/token/call/retry values come from backend `llm_usage_events` aggregates, not demo enrichment.
- No backend schema changes were introduced for enrichment/review metadata.

Default local mode:

- `VITE_API_BASE` defaults to `http://localhost:8000`.
- `VITE_DATA_MODE` defaults to `hybrid`.
- `mock`: original mock-only polished demo.
- `api`: backend-only with minimal fallback display values.
- `hybrid`: backend data plus local demo enrichment; fallback to mock rows if the backend is unreachable.

Stack:

- React 18 + TypeScript strict + Vite 5.
- React Router v6 with `createBrowserRouter`.
- No React Query or global state library.
- Contexts: `AuthProvider`, `DataProvider`, `SignalsProvider`. `AuthProvider` wraps all routes; `DataProvider` and `SignalsProvider` mount only inside the authenticated `AppShell`.
- No ESLint; `npm run lint` is `tsc --noEmit`.
- One stylesheet: `src/styles/globals.css`.

## Important Files

- `src/App.tsx`: wraps routes in `AuthProvider`.
- `src/components/AppShell.tsx`: redirects unsigned users to `/login`, then mounts `DataProvider` and `SignalsProvider` for authenticated app pages.
- `src/auth/AuthProvider.tsx`: persists the bearer token and user in local storage, validates existing sessions with `GET /auth/me`, and clears state on `401`.
- `src/api/client.ts`: API base/data mode constants, auth/session storage key, bearer-token fetch helpers, and upload/list helpers.
- `src/api/types.ts`: backend DTO types, including auth DTOs.
- `src/api/mappers.ts`: backend DTO to frontend view-model mapping.
- `src/data/DataProvider.tsx`: hybrid data context and hooks.
- `src/data/SignalsStore.tsx`: optimistic local review status/flag state.
- `src/data/demoEnrichment.ts`: local demo advisor/client/duration/cost metadata.
- `src/data/mockData.ts`: canonical frontend view-model types and mock fallback rows.
- `src/pages/UploadPage.tsx`: multipart upload and polling.
- `src/pages/TranscriptDetailPage.tsx`: prepared turns plus transcript-scoped final signals.
- `src/pages/SignalReviewPage.tsx`: cross-transcript signal review.
- `src/pages/ExportsPage.tsx`: public final-schema preview.
- `src/pages/AnalyticsPage.tsx`: estimated API cost and token usage from backend usage fields when available.

## Data Flow

`AuthProvider` handles sign-in and session validation:

- `POST /auth/login`
- `GET /auth/me`
- Stores `{ accessToken, user }` in local storage under `optimize_auth_session`.
- Clears the stored session and current user when API helpers receive `401`.

`DataProvider` loads backend data in `api`/`hybrid` modes only after `AppShell` confirms a signed-in user:

- `GET /transcripts`
- `GET /transcripts/{id}`
- `GET /transcripts/{id}/turns`
- `GET /signals`
- `GET /pipeline-runs`

Usage fields:

- `GET /transcripts` and `GET /transcripts/{id}` include `usage`.
- `GET /pipeline-runs` and `GET /pipeline-runs/{id}` include `usage` and `usage_by_step`.
- `usage.estimated_total_cost_usd` is an estimated API/LLM cost calculated by the backend pricing table from recorded OpenAI token counts; it is not invoice truth.

`UploadPage` posts `.txt` files to:

- `POST /transcripts` as multipart `file` plus optional `title`.

API helpers automatically attach `Authorization: Bearer <token>` when a stored token exists. Do not bypass `src/api/client.ts` for authenticated backend calls unless there is a clear reason.

`SignalsProvider` initializes from `DataProvider.apiSignals`, keeps local optimistic review status/flag changes, and exposes:

- `signals`
- `setSignals`
- `updateSignal(id, patch)`
- `signalsForTranscript(transcriptId)`

Review status is local-only in this pass. Do not imply backend review persistence until a dedicated endpoint/table exists.

## Mapping Rules

Backend to frontend:

- `TranscriptSummaryRead` / `TranscriptDetailRead` -> `Transcript`.
- `Transcript.cost`, `tokensIn`, `tokensOut`, `calls`, and `retries` come from `dto.usage` in API/hybrid backend mode.
- `SignalRead.transcript_id` -> `Signal.transcriptId`.
- `SignalRead.item_type` -> `Signal.type`.
- `SignalRead.advisor_quote` -> `Signal.quote`.
- `SignalRead.evidence_strength` -> `Signal.evidence`.
- Backend transcript turns -> `TranscriptTurn`.
- Pipeline step rows for `/pipeline/:id` come from `PipelineRunRead.usage_by_step` when available.

Turn display:

- Preserve backend timestamps and text.
- Display `speaker_role === "advisor"` as `Advisor`.
- Display other roles as client/rep-style text without changing stored text.

Fallback metadata:

- Known/demo transcript IDs use `demoEnrichment`.
- Unknown completed transcripts get deterministic fallback values such as `Advisor TBD`, `Prospective firm`, `pending`, and synthetic duration values.
- Do not use `demoEnrichment` for cost, token, call, or retry values when backend DTO usage is available.
- Mock mode and hybrid backend-unreachable fallback may continue to use demo cost/token values from `mockData`.
- When backend usage has no events, show zero cost/tokens with neutral copy such as `No usage recorded yet`, not synthetic fallback numbers.
- Export-ready is true only when a transcript is completed and has final signals.

Cost and usage copy:

- Label backend-derived values as `Estimated LLM cost` or `Estimated API cost`.
- Avoid wording such as billed spend, invoice cost, or exact billing total.
- Explain or imply that estimates are from recorded LLM usage events and backend pricing, not OpenAI invoice reconciliation.

Transcript highlighting:

- Quote matching remains exact substring matching.
- If an exact quote is not found in a turn, still render the signal card and do not force-highlight transcript text.

## Routes

- `/login`: username/password login. Redirects to `/dashboard` when a valid session already exists.
- `/dashboard`: KPIs, status bars, activity, queue.
- `/transcripts`: searchable/sortable transcript library.
- `/transcripts/:id`: transcript turns and transcript-scoped final signals.
- `/review`: cross-transcript signal review; "open in context" uses `Signal.transcriptId`.
- `/pipeline` and `/pipeline/:id`: pipeline run timeline using `usage_by_step` for cost/tokens/models/prompts in API-backed mode.
- `/upload`: upload `.txt` files and poll backend status in `api`/`hybrid`.
- `/analytics`: estimated cost/token usage presentation from backend usage fields when API data is loaded.
- `/exports`: public final-schema preview only.

## Design System

Use the existing class system in `src/styles/globals.css`. Do not add Tailwind, CSS-in-JS, or a component framework without explicit direction.

Key primitives live in `src/components/primitives.tsx`:

- `TopBar`, `Section`, `KPI`, `Btn`, `Field`
- `Sparkline`, `BarRow`, `Money`, `Tok`
- `StatusPill`, `ReviewPill`, `EvidencePill`, `TypePill`

Keep the internal-tool feel: dense, scannable, restrained, and operational. Reuse existing classes before inventing new CSS.

## Backend Integration Notes

FastAPI local CORS is enabled in `backend/app/main.py` for Vite dev origins on `localhost`/`127.0.0.1` ports `5170-5179`.

If the frontend loads but shows mock/empty data:

1. Check `http://localhost:8000/health`.
2. Sign in first; `/transcripts`, `/signals`, `/pipeline-runs`, `/review`, and `/exports` require bearer authentication.
3. Check `GET /auth/me` and confirm the stored token is valid.
4. Check `http://localhost:8000/transcripts` with the bearer token.
5. Confirm the backend database has rows; import artifacts if needed.
6. Check browser network/CORS errors.
7. Confirm `VITE_API_BASE` points to the running backend.

If login fails with "Unable to sign in":

1. Confirm the backend running at `VITE_API_BASE` includes the current `/auth/login` route; an older backend on port `8000` will fail.
2. Confirm CORS allows the current Vite port.
3. Confirm the username is `curtis` and use the owner-provided local password.

If API-backed rows show zero cost/tokens:

1. Check `GET /transcripts` and confirm each row has `usage.calls > 0`.
2. If usage is zero, inspect Postgres and confirm `llm_usage_events.transcript_id` matches the displayed `transcripts.id`.
3. For pipeline step costs, confirm `pipeline_runs` exist and `llm_usage_events.pipeline_run_id` matches the run id.
4. Remember artifact import hydrates transcripts, turns, and final signals, but not LLM usage events.
5. Local smoke scripts record usage only when run with `--record-usage`; the API upload/worker path is the best way to create matching transcript and run usage.

If the backend is empty, hybrid mode may show a quiet UI or mock fallback. Populate local data with:

```powershell
cd D:\development\optimize-financial\backend
python scripts\import_agent_artifacts.py --base-path ..\data\outputs\agents-outputs
```

## Export Rules

Export preview must preserve the public final schema only:

- `transcript_id`
- `item_type`
- `rank`
- `category`
- `advisor_quote`
- `timestamp`
- `evidence_strength`
- `rationale`

Do not include candidate/ranked/rejected metadata, prompt names, source chunks, validation notes, token usage, or raw transcript text in exports.
Export pages may show estimated aggregate API cost as UI metadata, but exported files must preserve the public final signal schema only.

## Commands

Run from `frontend/`:

```powershell
npm install
npm run dev -- --host 0.0.0.0
npm run lint
npm run build
```

Full stack from repo root:

```powershell
docker compose up -d --build postgres redis
docker compose run --rm backend python -m alembic upgrade head
docker compose build backend
docker compose build frontend
docker compose up -d backend worker frontend
```

Open `http://localhost:5173`.

## Checklist

Before changing frontend behavior:

- Read `src/styles/globals.css` and reuse existing classes.
- Check `src/components/primitives.tsx` before adding new atoms.
- Keep `DataProvider` and `SignalsProvider` inside the authenticated shell so signed-out users cannot mount logged-in data views.
- Use API helpers from `src/api/client.ts` so bearer tokens and `401` session clearing stay centralized.
- Use `DataProvider`/`SignalsProvider` hooks for page data; avoid direct page-level mock array imports.
- Keep `Signal.transcriptId` populated for any signal data.
- Keep raw transcript text inside `TranscriptDetailPage` only.
- Run `npm run lint` and `npm run build`.
- For visible UI changes, start the app and click through the affected route.
