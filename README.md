# Regulatory & Compliance Intelligence Hub

An enterprise AI platform for grounded, auditable regulatory compliance verification (e.g. GDPR, EU AI Act). The goal is to give compliance teams answers tied to official regulatory text, with traceable citations rather than unsupported claims.

> **Current status: Phase 1 – Core Infrastructure & System Connectivity.**
> Only the foundation exists today: a dashboard, an API, and a PostgreSQL/pgvector database, with a single diagnostic that proves all three are wired together. Document upload, clause parsing, Q&A and report export are *out of scope* for Phase 1 (see [requirement-docs/brd-1.md](requirement-docs/brd-1.md)).

## Architecture

```
┌──────────────────┐   HTTP/JSON   ┌──────────────────┐   asyncpg   ┌──────────────────────┐
│ Next.js frontend ├──────────────►│ FastAPI backend  ├────────────►│ PostgreSQL + pgvector│
│ :4001            │  CORS-limited │ :7001            │  pooled     │ (Neon, hosted)       │
└──────────────────┘               └──────────────────┘             └──────────────────────┘
```

The dashboard's **Test Full Stack Connection** button calls `GET /api/health`. The backend inserts a `health_checks` row containing a sample 3‑dimension vector, reads the latest row back, and returns the result. A successful response confirms DB read/write and pgvector support.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Next.js 15.0.3 (App Router), React 18.3.1, TypeScript 5.5.4, Tailwind CSS 3.4.13 |
| Backend | Python, FastAPI 0.115.0, Uvicorn 0.30.6, Pydantic / pydantic-settings 2.x |
| Database | PostgreSQL with the `pgvector` extension (hosted on Neon), SQLAlchemy 2.0 (async) + asyncpg, pgvector-python |
| Migrations | Alembic 1.13.2 (async env) |

Exact backend versions are pinned in [backend/requirements.txt](backend/requirements.txt); frontend versions in [frontend/package.json](frontend/package.json).

## Project Structure

```
.
├── README.md
├── requirement-docs/
│   └── brd-1.md                  # Phase 1 Business Requirements Document
├── backend/
│   ├── .env.example              # Template for backend/.env (not committed)
│   ├── Makefile                  # `make dev` – run API with auto-reload
│   ├── requirements.txt
│   ├── alembic.ini               # URL left blank; injected from settings at runtime
│   ├── alembic/
│   │   ├── env.py                # Async Alembic env, reads DATABASE_URL from app settings
│   │   └── versions/             # Migrations: health_checks + pgvector; documents/chunks; chunk_embeddings
│   └── app/
│       ├── main.py               # FastAPI app, CORS, `/` and `/api/health` routes
│       ├── core/config.py        # Settings (pydantic-settings, loads backend/.env)
│       ├── db/session.py         # Async engine (capped pool) + `get_db` dependency
│       └── models/
│           ├── system.py         # SQLAlchemy `Base` and `HealthCheck` model
│           └── regulatory.py     # `Document`, `Chunk`, `ChunkEmbedding` models
├── ingestion/                    # GDPR pipeline: parse -> chunk -> load -> embed -> search (see "Data pipeline")
│   ├── requirements.txt          # Own virtualenv (torch); lock file alongside
│   └── *.py
├── data/
│   ├── raw/gdpr/                 # Untouched EUR-Lex HTML + metadata.json (source of truth)
│   └── parsed/gdpr/              # Generated JSON: articles, recitals, chunks, validation reports
├── evaluation/                   # Question sets (dev, held-out, out-of-scope), recital reference, results (baseline preserved)
├── docs/adr/                     # Architecture decision records (0001 roadmap, 0002 retrieval pipeline)
└── frontend/
    ├── .env.local                # NEXT_PUBLIC_API_URL (non-secret, committed)
    ├── package.json
    ├── next.config.mjs
    ├── tailwind.config.ts / postcss.config.mjs / tsconfig.json
    └── app/
        ├── layout.tsx            # Root layout and metadata
        ├── page.tsx              # Dashboard with the diagnostic button and status badge
        └── globals.css
```

## Frontend

- **Architecture:** Single Next.js App Router page ([frontend/app/page.tsx](frontend/app/page.tsx)), a client component. It holds the diagnostic state (`idle` / `loading` / `success` / `error`), calls `${NEXT_PUBLIC_API_URL}/api/health` with `fetch`, and renders the JSON result. While loading, it shows a "database may be waking up" message and disables the button to prevent duplicate submissions.
- **Styling:** Tailwind CSS (dark slate theme). Tailwind scans `app/**` and `components/**`.
- **Dev server port:** `4001` (set in the `dev` script). The backend's default CORS origin matches this.

Commands (run from `frontend/`):

| Command | Purpose |
| --- | --- |
| `npm install` | Install dependencies |
| `npm run dev` | Dev server at http://localhost:4001 |
| `npm run build` | Production build |
| `npm run start` | Serve the production build (Next.js default port 3000 unless `-p` is passed) |

## Backend

- **Architecture:** FastAPI app in [backend/app/main.py](backend/app/main.py). Configuration comes from environment variables via pydantic-settings. DB access uses an async SQLAlchemy engine and a per-request session from the `get_db` dependency.
- **Connection limits:** The pool is deliberately small (`DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=5`) because Neon's free tier has limited compute and connections. `pool_pre_ping` is enabled so connections dropped while the database was idle are recovered.
- **CORS:** Only `FRONTEND_ORIGIN` is allowed.

### API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Liveness: `{"service": ..., "status": "online"}` |
| `GET` | `/api/health` | Writes a `health_checks` row (with a sample vector), reads the latest row back. Returns `200` with `api_status`, `database_status`, `write_verified`, `read_verified`, `vector_support_verified`, `latest_record`, `checked_at`; returns `503` with a `detail` message if the DB step fails. |

FastAPI's interactive docs are served at http://localhost:7001/docs.

> Note: `/api/health` **writes a row on every call**, so the `health_checks` table grows with each diagnostic. The `/api` prefix comes from `API_V1_PREFIX`.

### Database

Tables ([backend/app/models/](backend/app/models/)):

| Table | Purpose |
| --- | --- |
| `health_checks` | Written by `/api/health` on every call (`id`, `status`, `test_vector vector(3)`, `created_at`) |
| `documents` | One row per regulation (GDPR): CELEX id, source URL, retrieval date, source SHA-256, chunk size limit used |
| `chunks` | One row per retrieval unit (670 for GDPR): `chunk_id`, `citation` (e.g. "Article 9(2)(a)"), chapter/section/article/paragraph/point, `type` (article or recital), `text`, source anchor + URL, `cross_refs` (JSONB), `text_sha256` |
| `chunk_embeddings` | One `vector(384)` per (chunk, model, model revision, variant). Model name and pinned revision are stored with every vector. No vector index yet: search is exact |

The first migration runs `CREATE EXTENSION IF NOT EXISTS vector`, so the database user needs permission to create that extension (or it must already be enabled).

Commands (run from `backend/`, with the virtualenv active unless noted):

| Command | Purpose |
| --- | --- |
| `pip install -r requirements.txt` | Install dependencies |
| `alembic upgrade head` | Apply migrations |
| `alembic downgrade -1` | Roll back the last migration |
| `alembic revision --autogenerate -m "message"` | Create a migration from model changes (import new models in `alembic/env.py` so they're registered) |
| `make dev` | Run the API with reload on port 7001. **Requires the virtualenv at `backend/.venv`**, since the Makefile calls `.venv/bin/uvicorn`. |

## Data pipeline (GDPR)

Retrieval-first roadmap: [docs/adr/0001-retrieval-and-fine-tuning-roadmap.md](docs/adr/0001-retrieval-and-fine-tuning-roadmap.md). Each stage is deterministic and re-runnable from the raw EUR-Lex HTML in `data/raw/gdpr/` (see its README for fetch rules: EUR-Lex robots.txt asks for a 10 s crawl delay, and plain `curl` is blocked by a WAF, so a real browser is needed).

| Stage | Command (from the repo root) | Output |
| --- | --- | --- |
| Parse + validate | `python3 -B -m ingestion.parse_gdpr` | `data/parsed/gdpr/{articles,recitals,structure,footnotes}.json`, `parse_report.json` (99 articles, 173 recitals, coverage check; exits non-zero on failure) |
| Chunk | `python3 -B -m ingestion.chunk_gdpr` (`--max-words 350` default) | `chunks.json`, `chunk_report.json` (670 chunks; every source word lands in exactly one chunk) |
| Load into Postgres | `backend/.venv/bin/python -m ingestion.load_gdpr` (`--dry-run` to validate only) | `documents` + `chunks` rows (idempotent upsert; run `alembic upgrade head` first) |
| Embed | `ingestion/.venv/bin/python -m ingestion.embed_chunks` (`--dry-run` for no DB) | `chunk_embeddings` rows, variant `A` = chunk text unchanged, `BAAI/bge-small-en-v1.5` pinned to a commit hash. Only missing/changed chunks are embedded |
| Search | `ingestion/.venv/bin/python -m ingestion.search_chunks "your question"` (`--json`; `--baseline` for the original dense search) | Evaluated pipeline ([ADR 0002](docs/adr/0002-retrieval-pipeline-and-abstention.md)): operative articles, separate recital context, and an evidence status (`supported` / `weak_evidence` / `no_basis`) |
| Evaluate | `ingestion/.venv/bin/python -m ingestion.experiments release --heldout` | Baseline vs chosen pipeline on the dev and held-out question sets in `evaluation/` |

Search and evaluation also download two more free Hugging Face models on first use (a reranker, ~0.7 GB) and run it on the Apple GPU when available (`RERANK_DEVICE=cpu` to override; about 10x slower). Set `HF_HUB_OFFLINE=1` once the models are cached to avoid network stalls. One-time setup for the embedding stage: `/opt/homebrew/bin/python3.12 -m venv ingestion/.venv && ingestion/.venv/bin/pip install -r ingestion/requirements.txt` (first run downloads ~130 MB of model weights). The parse and chunk stages use only the standard library.

Chunking rules: Article 4 gets one chunk per definition; a paragraph up to 350 words is one chunk (lead-in, points and trailing text together); longer paragraphs split into one chunk per point with the lead-in prepended; each recital is one chunk. Text is stored exactly as published (curly quotes kept; only whitespace is normalised). Data source licence: EUR-Lex legal text is reusable under Commission Decision 2011/833/EU, attribution "© European Union"; only the Official Journal version is authentic.

## Environment Configuration

Never commit real credentials. `backend/.env` is git-ignored.

**Backend** – copy [backend/.env.example](backend/.env.example) to `backend/.env`:

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | – | Async SQLAlchemy URL, e.g. `postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>?ssl=require` |
| `FRONTEND_ORIGIN` | No | `http://localhost:4001` | Origin allowed by CORS |
| `PROJECT_NAME` | No | `Regulatory & Compliance Intelligence Hub` | App title |
| `API_V1_PREFIX` | No | `/api` | Prefix for API routes |
| `DB_POOL_SIZE` | No | `5` | Base connection pool size |
| `DB_MAX_OVERFLOW` | No | `5` | Extra connections beyond the pool |

The backend reads `.env` relative to the working directory, so run backend commands from `backend/`.

**Frontend** – [frontend/.env.local](frontend/.env.local) is committed and holds only a public value:

| Variable | Default | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:7001` | Backend base URL (exposed to the browser) |

## Local Development Setup

**Prerequisites:** Node.js and npm (Node 20 is known to work), Python 3 with `venv`, and a PostgreSQL database with the `pgvector` extension available. The project is set up for a Neon PostgreSQL instance, but any pgvector-enabled Postgres reachable from your machine should work with the right `DATABASE_URL`. The Python version expected by the pinned dependencies isn't documented in the repo; if installation fails on a very new Python, try an earlier 3.x release.

1. **Clone the repo and enter it.**

2. **Backend**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env        # then edit .env and set DATABASE_URL
   alembic upgrade head
   make dev                    # API on http://localhost:7001
   ```

3. **Frontend** (in a second terminal)
   ```bash
   cd frontend
   npm install
   npm run dev                 # UI on http://localhost:4001
   ```

4. **Verify:** open http://localhost:4001 and click **Test Full Stack Connection**. The badge should switch to *Operational* and show the JSON payload. You can also test the API directly: `curl http://localhost:7001/api/health`.

## Run with Docker (auto-rebuild on change)

Requires Docker with Compose 2.22+ and a filled-in `backend/.env`. Run from the repo root:

```bash
make up         # build + run backend (:7001) and frontend (:4001) with file watching
make migrate    # alembic upgrade head inside the backend container
make logs | ps | down | rebuild
```

Everything lives in the root [Makefile](Makefile) and [docker/](docker/) (compose file plus one Dockerfile per service). `develop.watch` in [docker/docker-compose.yml](docker/docker-compose.yml): source edits are synced and hot-reloaded (uvicorn `--reload`, `next dev`); config files restart the process; changes to `requirements.txt`, `package*.json`, a Dockerfile or `backend/.env` rebuild the image and recreate the container. Dependency layers are cached. The database is external (Neon), so there is no DB container. Host ports 7001/4001 must be free.

## Testing

**Ingestion and retrieval pipeline** (`ingestion/tests/`, pytest, no network needed for the default run):

| Command (repo root) | What it runs |
| --- | --- |
| `ingestion/.venv/bin/python -m pytest` | ~50 fast tests: the parser against the real raw EUR-Lex file (counts, structure, determinism, committed outputs not stale), the chunker (coverage, citations, splitting rules, cross-reference extraction), and retrieval logic with fakes (article/recital separation, glossary, reranking, evidence statuses, display band) |
| `RUN_INTEGRATION=1 HF_HUB_OFFLINE=1 ingestion/.venv/bin/python -m pytest` | Adds end-to-end checks against the real database, models and reranker (corpus counts, golden questions, out-of-scope refusals). Needs `backend/.env` and the cached models. One known failure is tracked as a strict `xfail`: [docs/issues/0001](docs/issues/0001-article-6-1-missing-for-legal-bases-questions.md) |

Install the test dependency with `ingestion/.venv/bin/pip install -r ingestion/requirements-dev.txt`. Retrieval *quality* is measured separately by the evaluation sets (see [ADR 0002](docs/adr/0002-retrieval-pipeline-and-abstention.md)).

**Backend and frontend:** there is no automated test suite yet (no backend or frontend tests, and no linter configuration). `npm run lint` is defined in `package.json` but ESLint is not installed or configured, so it isn't usable as-is. For now, the end-to-end check is the diagnostic described in step 4 above. For a quick type check of the frontend, run `npx tsc --noEmit` from `frontend/`.

## Build and Deployment

- **Frontend build:** `cd frontend && npm run build`, then `npm run start`.
- **Backend:** no Dockerfile or production server config exists in the repo. For a non-reload run, use `uvicorn app.main:app --host 0.0.0.0 --port 7001` from `backend/`.
- **Database:** apply schema changes with `alembic upgrade head` against the target database before starting a new backend version.
- **Deployment target:** no CI/CD or hosting configuration is committed. When deploying, set the backend env vars above, set `FRONTEND_ORIGIN` to the deployed frontend URL, and set `NEXT_PUBLIC_API_URL` to the deployed backend URL **at frontend build time** (it is inlined into the client bundle).

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| Backend fails at startup with a validation error for `DATABASE_URL` | `backend/.env` is missing or you're not running from `backend/`. |
| `make dev` → `.venv/bin/uvicorn: No such file or directory` | Create the virtualenv at `backend/.venv` and install requirements (see setup step 2). |
| Dashboard shows an error or "Unable to reach the processing engine" | Backend isn't running, `NEXT_PUBLIC_API_URL` is wrong, or the database is waking up from idle (Neon free tier scales to zero when idle). Retry after a few seconds. |
| Browser console shows a CORS error | The frontend isn't served from `FRONTEND_ORIGIN`. Use port 4001 or update `FRONTEND_ORIGIN`. Restart the backend after changing `.env`. |
| `/api/health` returns `503` | Read the `detail` field. Common causes: migrations not applied (`alembic upgrade head`), wrong credentials, or the `vector` extension is missing. |
| `alembic upgrade head` fails on `CREATE EXTENSION vector` | The DB user lacks permission, or pgvector isn't available on the server. |
| "too many connections" errors | The free tier has a connection limit; use the direct (non-pooler) Neon URL. Keep `DB_POOL_SIZE + DB_MAX_OVERFLOW` low and close other clients. |
| Changed `NEXT_PUBLIC_API_URL` but nothing changed | Restart `npm run dev` (or rebuild); the value is read at build/start time. |

## Further Reading

- [requirement-docs/brd-1.md](requirement-docs/brd-1.md) – Phase 1 business requirements, functional requirements, and acceptance criteria.
