---
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

- Backend remains the factual source for uploaded transcripts, prepared turns, final Agent-5 signals, and pipeline status.
- Local demo enrichment preserves polished advisor/client/duration/review/cost metadata for presentation.
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
- Contexts: `AuthProvider`, `DataProvider`, `SignalsProvider`.
- No ESLint; `npm run lint` is `tsc --noEmit`.
- One stylesheet: `src/styles/globals.css`.

## Important Files

- `src/App.tsx`: wraps routes in `AuthProvider`, `DataProvider`, and `SignalsProvider`.
- `src/api/client.ts`: API base/data mode constants and fetch helpers.
- `src/api/types.ts`: backend DTO types.
- `src/api/mappers.ts`: backend DTO to frontend view-model mapping.
- `src/data/DataProvider.tsx`: hybrid data context and hooks.
- `src/data/SignalsStore.tsx`: optimistic local review status/flag state.
- `src/data/demoEnrichment.ts`: local demo advisor/client/duration/cost metadata.
- `src/data/mockData.ts`: canonical frontend view-model types and mock fallback rows.
- `src/pages/UploadPage.tsx`: multipart upload and polling.
- `src/pages/TranscriptDetailPage.tsx`: prepared turns plus transcript-scoped final signals.
- `src/pages/SignalReviewPage.tsx`: cross-transcript signal review.
- `src/pages/ExportsPage.tsx`: public final-schema preview.

## Data Flow

`DataProvider` loads backend data in `api`/`hybrid` modes:

- `GET /transcripts`
- `GET /transcripts/{id}`
- `GET /transcripts/{id}/turns`
- `GET /signals`
- `GET /pipeline-runs`

`UploadPage` posts `.txt` files to:

- `POST /transcripts` as multipart `file` plus optional `title`.

`SignalsProvider` initializes from `DataProvider.apiSignals`, keeps local optimistic review status/flag changes, and exposes:

- `signals`
- `setSignals`
- `updateSignal(id, patch)`
- `signalsForTranscript(transcriptId)`

Review status is local-only in this pass. Do not imply backend review persistence until a dedicated endpoint/table exists.

## Mapping Rules

Backend to frontend:

- `TranscriptSummaryRead` / `TranscriptDetailRead` -> `Transcript`.
- `SignalRead.transcript_id` -> `Signal.transcriptId`.
- `SignalRead.item_type` -> `Signal.type`.
- `SignalRead.advisor_quote` -> `Signal.quote`.
- `SignalRead.evidence_strength` -> `Signal.evidence`.
- Backend transcript turns -> `TranscriptTurn`.

Turn display:

- Preserve backend timestamps and text.
- Display `speaker_role === "advisor"` as `Advisor`.
- Display other roles as client/rep-style text without changing stored text.

Fallback metadata:

- Known/demo transcript IDs use `demoEnrichment`.
- Unknown completed transcripts get deterministic fallback values such as `Advisor TBD`, `Prospective firm`, `pending`, and synthetic duration/cost values.
- Export-ready is true only when a transcript is completed and has final signals.

Transcript highlighting:

- Quote matching remains exact substring matching.
- If an exact quote is not found in a turn, still render the signal card and do not force-highlight transcript text.

## Routes

- `/login`: demo login.
- `/dashboard`: KPIs, status bars, activity, queue.
- `/transcripts`: searchable/sortable transcript library.
- `/transcripts/:id`: transcript turns and transcript-scoped final signals.
- `/review`: cross-transcript signal review; "open in context" uses `Signal.transcriptId`.
- `/pipeline` and `/pipeline/:id`: pipeline/cost timeline using backend status plus demo step cost placeholders.
- `/upload`: upload `.txt` files and poll backend status in `api`/`hybrid`.
- `/analytics`: hybrid cost/usage presentation until backend aggregation exists.
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
2. Check `http://localhost:8000/transcripts`.
3. Confirm the backend database has rows; import artifacts if needed.
4. Check browser network/CORS errors.
5. Confirm `VITE_API_BASE` points to the running backend.

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
- Use `DataProvider`/`SignalsProvider` hooks for page data; avoid direct page-level mock array imports.
- Keep `Signal.transcriptId` populated for any signal data.
- Keep raw transcript text inside `TranscriptDetailPage` only.
- Run `npm run lint` and `npm run build`.
- For visible UI changes, start the app and click through the affected route.
