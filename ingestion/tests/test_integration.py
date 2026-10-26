"""End-to-end checks against the real database, models and reranker.

Skipped by default. Run with:  RUN_INTEGRATION=1 HF_HUB_OFFLINE=1 ingestion/.venv/bin/python -m pytest
"""
import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

pytestmark = pytest.mark.integration
os.environ.setdefault("HF_HUB_OFFLINE", "1")


@pytest.fixture(scope="module")
def retriever():
    from ingestion.embedding import load_model
    from ingestion.retrieval import Corpus, Retriever
    ret = Retriever(Corpus.from_db(variants=("A",)), load_model())
    yield ret
    ret.save_cache()


def ask(retriever, q):
    from ingestion.pipeline import retrieve_evidence
    return retrieve_evidence(retriever, q)


def articles(result, n=5):
    return [p["article"] for p in result["provisions"][:n]]


def test_database_holds_the_full_corpus():
    from ingestion.load_gdpr import database_url

    async def counts():
        eng = create_async_engine(database_url(), poolclass=NullPool)
        try:
            async with eng.connect() as c:
                q = lambda s: c.execute(text(s))
                return ((await q("select count(*) from chunks")).scalar_one(),
                        (await q("select count(distinct article_number) from chunks")).scalar_one(),
                        (await q("select count(*) from chunks where type='recital'")).scalar_one(),
                        (await q("select count(*) from chunk_embeddings where variant='A'")).scalar_one())
        finally:
            await eng.dispose()
    assert asyncio.run(counts()) == (670, 99, 173, 670)


def test_right_to_be_forgotten_returns_article_17_as_the_answer(retriever):
    r = ask(retriever, "What is the right to be forgotten?")
    assert r["status"] == "supported" and articles(r, 1) == [17]
    assert all(c["citation"].startswith("Recital") for c in r["context"])


def test_breach_deadline_finds_article_33(retriever):
    assert 33 in articles(ask(retriever, "How quickly must a data breach be reported to the authority?"), 3)


def test_terminology_gap_companies_outside_the_eu_finds_article_3(retriever):
    """Regression: dense search alone ranks Article 3(2) 108th; the glossary candidates fix it."""
    assert 3 in articles(ask(retriever, "Does the GDPR apply to companies based outside the EU?"))


@pytest.mark.parametrize("q", [
    "How do I file my income tax return in France?",
    "How many days of annual leave am I entitled to in Spain?",
])
def test_out_of_scope_questions_are_refused(retriever, q):
    r = ask(retriever, q)
    assert r["status"] == "no_basis" and r["provisions"] == [] and r["context"] == []


@pytest.mark.xfail(strict=True, reason="Known issue docs/issues/0001: Article 6(1) misses the candidates for 'legal bases'")
def test_legal_bases_question_finds_article_6(retriever):
    assert 6 in articles(ask(retriever, "What are the legal bases a business can rely on to use personal information?"))
