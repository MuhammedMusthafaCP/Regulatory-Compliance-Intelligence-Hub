# ADR 0003: Serving the retrieval pipeline from the API

- **Status:** Accepted
- **Date:** 2026-10-27
- **Builds on:** [ADR 0002](0002-retrieval-pipeline-and-abstention.md)

## Context

The evaluated pipeline lives in `ingestion/` and needs torch, two Hugging Face models and (for speed) the Apple GPU. A search takes about 2 s on the GPU and, estimated from earlier CPU reranking speed, roughly 20 s on CPU. The FastAPI backend is a small async app, its Docker image is deliberately lean, and the Neon connection pool is capped.

## Decisions

1. **Reuse, don't copy.** The backend imports `ingestion.pipeline`; the retrieval logic exists once. The loader adds the repository root to `sys.path` when the `ingestion` directory is present.
2. **Optional dependencies.** torch and friends live in `backend/requirements-search.txt`, not `requirements.txt`. Without them (for example in the Docker image) the service reports `unavailable` instead of failing, and the API stays up.
3. **Load once, in the background.** Models and the corpus load at startup without blocking it; `GET /api/search/status` and `503 search_loading` (with `Retry-After`) tell clients when it is ready. Models are loaded offline from the local cache (`HF_HUB_OFFLINE=1`), so serving needs no network and runs the pinned revisions.
4. **One worker thread.** All inference, including loading, runs on a single dedicated thread: the model stays on one thread, the GPU is never used concurrently, and requests are served in order. The queue is bounded (`SEARCH_MAX_QUEUE`, default 8; beyond it `429`) and each search has a timeout (default 60 s, `504`). Measured: 12 simultaneous requests gave 8 successes served about 1.5 s apart and 4 `429`s.
5. **Serving mode caches nothing.** `Retriever(cache=False)` skips the on-disk score cache and the in-memory query and score caches that the experiments use, so a long-running process cannot grow without bound.
6. **Thin API layer.** Router (validation and error mapping), Pydantic schemas, and a service (execution policy) are separate; the service takes an injectable loader and runner, which is what makes the concurrency and failure behaviour unit-testable without models.
7. **Errors are structured and generic.** Known failures map to stable codes in `{"detail": {"code", "message"}}`; anything unexpected becomes `500 search_failed` with a generic message and the stack trace only in the server log.
8. **Frontend contract.** The page validates every response with Zod and renders only EUR-Lex source links (parsed URL, https, exact host).

## Consequences and limits

- **Docker cannot serve search today.** Making it work needs the heavy dependencies in the image plus enough CPU for roughly 20 s per search (estimated), or a separate retrieval service with GPU access. That is a deployment decision to take when hosting is chosen; the service interface (`load_pipeline` / `run_pipeline`) is the seam where a remote call could replace the in-process one.
- **Throughput is one search at a time** (about 0.5 per second on the GPU). That is fine for a few users; more needs batching or more workers, which the GPU path would have to be re-checked for.
- **Startup is slow after every code reload** in `--reload` development, because the models reload.
- **No authentication or rate limiting per user yet**; the queue limit protects the engine, not fairness between users.
