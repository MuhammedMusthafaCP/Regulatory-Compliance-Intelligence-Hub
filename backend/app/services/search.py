"""Runs the evaluated GDPR retrieval pipeline (ingestion/) inside the API process.

The pipeline is synchronous and heavy (embedding model, cross-encoder, GPU), so:
  * the models and corpus load once, in the background, at startup;
  * every search runs on ONE dedicated worker thread (the model stays on one thread, the GPU is never
    used concurrently), with a bounded queue and a timeout so load cannot pile up silently.

The pipeline itself is imported lazily from the repository's `ingestion` package; if it (or its
dependencies from requirements-search.txt) is missing, the service reports "unavailable" instead of failing.
"""
import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger("app.search")

# Where the `ingestion` package may live: the repository root when running from a checkout
# (backend/app/services/search.py -> parents[3]), or the app directory inside the Docker image (parents[2]).
SEARCH_PATHS = [Path(__file__).resolve().parents[3], Path(__file__).resolve().parents[2]]


class SearchError(Exception):
    """A failure with a stable error code and HTTP status for the API layer to report."""

    def __init__(self, code: str, message: str, status_code: int, retry_after: int | None = None):
        super().__init__(message)
        self.code, self.message, self.status_code, self.retry_after = code, message, status_code, retry_after


def load_pipeline():
    """Default loader: build the retriever from the repository's ingestion package."""
    os.environ.setdefault("HF_HUB_OFFLINE", "1")   # pinned models are cached by the ingestion scripts
    for root in SEARCH_PATHS:
        if (root / "ingestion").is_dir() and str(root) not in sys.path:
            sys.path.insert(0, str(root))
    from ingestion.embedding import load_model
    from ingestion.pipeline import retrieve_evidence
    from ingestion.retrieval import Corpus, Retriever

    retriever = Retriever(Corpus.from_db(variants=("A",)), load_model(), cache=False)
    retrieve_evidence(retriever, "warm-up question")   # first call compiles GPU kernels; don't make a user pay for it
    return retriever


def run_pipeline(retriever, question: str) -> dict:
    from ingestion.pipeline import retrieve_evidence

    return retrieve_evidence(retriever, question)


class SearchService:
    def __init__(self, loader=load_pipeline, runner=run_pipeline, *, max_queue: int = 8, timeout: float = 60.0):
        self.state = "loading"
        self._loader, self._runner = loader, runner
        self._max_queue, self._timeout = max_queue, timeout
        self._engine = None
        self._pending = 0
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="search")

    @classmethod
    def disabled(cls) -> "SearchService":
        service = cls()
        service.state = "unavailable"
        return service

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    async def start(self) -> None:
        """Load the engine on the worker thread. Never raises: the outcome is recorded in `state`."""
        try:
            self._engine = await asyncio.get_running_loop().run_in_executor(self._pool, self._loader)
            self.state = "ready"
            logger.info("search engine ready")
        except ImportError:
            self.state = "unavailable"
            logger.warning("search engine unavailable: ingestion package or requirements-search.txt not installed")
        except Exception:  # noqa: BLE001
            self.state = "failed"
            logger.exception("search engine failed to start")

    async def search(self, question: str) -> dict:
        if self.state == "loading":
            raise SearchError("search_loading", "The search engine is starting up. Please try again in a few seconds.", 503, retry_after=5)
        if self.state != "ready":
            raise SearchError("search_unavailable", "Search is not available on this server.", 503)
        if self._pending >= self._max_queue:
            raise SearchError("search_busy", "The search engine is busy. Please try again shortly.", 429, retry_after=5)

        self._pending += 1
        future = asyncio.get_running_loop().run_in_executor(self._pool, self._runner, self._engine, question)
        future.add_done_callback(self._finished)
        try:
            # shield: if we give up waiting, the worker still finishes and the queue count stays accurate
            return await asyncio.wait_for(asyncio.shield(future), self._timeout)
        except asyncio.TimeoutError as exc:
            raise SearchError("search_timeout", "The search took too long. Please try again.", 504) from exc

    def _finished(self, future: asyncio.Future) -> None:
        self._pending -= 1
        if not future.cancelled():
            future.exception()   # mark retrieved so an abandoned failure is not logged as "never retrieved"

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
