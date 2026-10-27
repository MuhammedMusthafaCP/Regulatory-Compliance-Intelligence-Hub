"""SearchService behaviour: loading states, serialisation, queue limit, timeout. Fake loader/runner only."""
import asyncio
import sys
import threading
import time

import pytest

from app.services.search import SearchError, SearchService


def run(coro):
    return asyncio.run(coro)


def make(loader=lambda: "engine", runner=lambda engine, q: {"answer": q, "engine": engine}, **kw):
    return SearchService(loader, runner, **kw)


def test_search_before_the_engine_is_ready_is_a_retryable_503():
    svc = make()
    with pytest.raises(SearchError) as e:
        run(svc.search("q"))
    assert (e.value.code, e.value.status_code, e.value.retry_after) == ("search_loading", 503, 5)


def test_start_makes_the_service_ready_and_search_runs_the_runner():
    async def go():
        svc = make()
        await svc.start()
        return svc.state, await svc.search("hello")
    state, result = run(go())
    assert state == "ready" and result == {"answer": "hello", "engine": "engine"}


def test_missing_dependencies_mark_the_service_unavailable_not_failed():
    def loader():
        raise ImportError("No module named 'torch'")
    async def go():
        svc = make(loader=loader)
        await svc.start()
        with pytest.raises(SearchError) as e:
            await svc.search("q")
        return svc.state, e.value.code
    assert run(go()) == ("unavailable", "search_unavailable")


def test_loader_crash_is_recorded_and_start_never_raises():
    def loader():
        raise RuntimeError("database unreachable")
    async def go():
        svc = make(loader=loader)
        await svc.start()
        return svc.state
    assert run(go()) == "failed"


def test_disabled_service_is_unavailable():
    svc = SearchService.disabled()
    with pytest.raises(SearchError) as e:
        run(svc.search("q"))
    assert svc.state == "unavailable" and e.value.code == "search_unavailable"


def test_searches_run_one_at_a_time_on_one_worker_thread():
    active, peak, threads = 0, 0, set()
    lock = threading.Lock()

    def runner(engine, q):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            threads.add(threading.get_ident())
        time.sleep(0.05)
        with lock:
            active -= 1
        return {"q": q}

    async def go():
        svc = make(runner=runner)
        await svc.start()
        return await asyncio.gather(*(svc.search(f"q{i}") for i in range(4)))
    results = run(go())
    assert [r["q"] for r in results] == ["q0", "q1", "q2", "q3"]
    assert peak == 1


def test_queue_limit_rejects_with_429_and_recovers():
    release = threading.Event()

    def runner(engine, q):
        release.wait(2)
        return {"q": q}

    async def go():
        svc = make(runner=runner, max_queue=2)
        await svc.start()
        first, second = asyncio.create_task(svc.search("a")), asyncio.create_task(svc.search("b"))
        await asyncio.sleep(0.05)
        with pytest.raises(SearchError) as e:
            await svc.search("c")
        release.set()
        await asyncio.gather(first, second)
        again = await svc.search("d")      # capacity is back once the queue drains
        return e.value, again
    err, again = run(go())
    assert (err.code, err.status_code, err.retry_after) == ("search_busy", 429, 5) and again == {"q": "d"}


def test_timeout_returns_504_and_the_slot_is_released_when_the_worker_finishes():
    def runner(engine, q):
        time.sleep(0.3)
        return {"q": q}

    async def go():
        svc = make(runner=runner, timeout=0.05, max_queue=1)
        await svc.start()
        with pytest.raises(SearchError) as e:
            await svc.search("slow")
        await asyncio.sleep(0.4)           # worker completes in the background
        return e.value.code, svc._pending
    assert run(go()) == ("search_timeout", 0)


def test_a_failing_search_propagates_and_frees_its_slot():
    def runner(engine, q):
        raise ValueError("boom")

    async def go():
        svc = make(runner=runner, max_queue=1)
        await svc.start()
        with pytest.raises(ValueError):
            await svc.search("q")
        await asyncio.sleep(0.05)
        return svc._pending
    assert run(go()) == 0


def test_default_loader_reports_unavailable_when_the_pipeline_is_not_installed(monkeypatch):
    """The lean Docker image has no ingestion package or torch: search must degrade, not crash."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")        # the loader sets this default; monkeypatch undoes it afterwards
    monkeypatch.setitem(sys.modules, "ingestion", None)   # makes `import ingestion...` raise ImportError

    async def go():
        svc = SearchService(max_queue=1)
        await svc.start()
        with pytest.raises(SearchError) as e:
            await svc.search("q")
        svc.close()
        return svc.state, e.value.code, e.value.status_code
    assert run(go()) == ("unavailable", "search_unavailable", 503)
