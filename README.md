# Advisor Signal Extraction

Monorepo for extracting representative-facing drivers and blockers from advisor call transcripts.

## Project Layout

```text
backend/   Python API, pipeline, agents, workers, database logic
frontend/  React + TypeScript representative-facing UI
shared/    Generated JSON schemas and OpenAPI contracts
infra/     Docker, Nginx, Postgres setup
data/      Local sample transcripts and sample outputs
```

## Architecture Boundaries

1. API routes do not call OpenAI or pipeline agents directly.
2. API routes enqueue worker tasks.
3. Workers call the pipeline orchestrator.
4. The pipeline orchestrator calls bounded agents.
5. Agents call the shared LLM client.
6. Only validated/finalized signals are exposed to representatives by default.
7. `shared/` contains generated schemas and contracts only, not runtime code.

The intended backend flow is:

```text
Upload transcript
        |
        v
Create transcript row in PostgreSQL
        |
        v
API enqueues worker task
        |
        v
Worker calls PipelineOrchestrator
        |
        v
Transcript preparation agent
        |
        v
Signal extraction agent
        |
        v
Consolidation/ranking agent
        |
        v
Evidence validation agent
        |
        v
Final formatting agent
        |
        v
Write candidates + finalized signals to PostgreSQL
        |
        v
Frontend displays representative-facing results
```

## Local Development

Copy `.env.example` to `.env`, fill in local values, then run services with Docker Compose or start the backend and frontend directly.

```bash
cp .env.example .env
docker compose up --build
```

## Data Safety

Use `data/sample_transcripts/` and `data/sample_outputs/` for local testing only. Do not commit real confidential transcripts.

