"""Retrieval logic with fakes: no database, no model downloads, no GPU."""
import re
import zlib

import numpy as np
import pytest

from ingestion import evaluate as E
from ingestion import pipeline as PL
from ingestion import retrieval as R
from ingestion.glossary import expand, expanded_query
from ingestion.lexical import BM25, tokenize


# ---------- lexical + glossary ----------

def test_tokenize_stems_and_drops_stopwords():
    assert tokenize("The controllers are erasing personal data") == ["control", "eras", "person", "data"]


def test_bm25_prefers_the_document_with_the_query_terms():
    bm = BM25(["right to erasure of personal data", "territorial scope of the regulation", "security of processing"])
    s = bm.scores("erasure")
    assert s[0] > 0 and s[1] == 0 and s[2] == 0


def test_glossary_bridges_lay_wording_to_gdpr_terms():
    terms, hits = expand("Does the GDPR apply to companies based outside the EU?")
    assert "not established in the Union" in terms and hits
    assert "supervisory authority" in expand("Can I complain to the regulator?")[0]
    assert "personal data breach" in expand("Our database was hacked")[0]


def test_glossary_leaves_unrelated_questions_alone_and_keeps_the_original_text():
    assert expand("How many days of annual leave do I get in Spain?")[0] == ""
    q = "What is the right to be forgotten?"
    assert expanded_query(q).startswith(q)
    assert expanded_query("annual leave in Spain") == "annual leave in Spain"


# ---------- evaluation helpers ----------

def meta(**kw):
    base = {"type": "article", "article_number": 6, "paragraph": "1", "point": None, "citation": "Article 6(1)"}
    return base | kw


def test_is_hit_rules():
    assert E.is_hit(meta(), {"article": 6})
    assert E.is_hit(meta(), {"article": 6, "paragraph": "1"})
    assert not E.is_hit(meta(paragraph="2"), {"article": 6, "paragraph": "1"})
    assert not E.is_hit(meta(type="recital"), {"article": 6})
    # a whole-paragraph chunk contains every point; a point chunk only matches its own point
    assert E.is_hit(meta(point=None), {"article": 6, "paragraph": "1", "point": "(f)"})
    assert E.is_hit(meta(point="(f)"), {"article": 6, "paragraph": "1", "point": "(f)"})
    assert not E.is_hit(meta(point="(a)"), {"article": 6, "paragraph": "1", "point": "(f)"})


def test_score_question_metrics():
    q = {"relevant": [{"article": 17}, {"article": 19}]}
    ranked = [meta(article_number=5), meta(article_number=17), meta(type="recital")]
    m = E.score_question(q, ranked)
    assert m["first_hit_rank"] == 2 and m["mrr"] == 0.5
    assert m["hit@1"] == 0.0 and m["hit@3"] == 1.0 and m["recall@3"] == 0.5
    assert m["recitals_in_top5"] == 1


# ---------- pipeline status thresholds ----------

@pytest.mark.parametrize("score,status", [
    (0.0, "no_basis"), (0.199, "no_basis"), (0.2, "weak_evidence"), (0.499, "weak_evidence"),
    (0.5, "supported"), (0.99, "supported")])
def test_status_thresholds(score, status):
    assert PL.status_for(score) == status


# ---------- engine on a tiny synthetic corpus ----------

class FakeModel:
    """Hashed bag-of-words 'embeddings': deterministic, and similar texts get similar vectors."""
    def encode(self, texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True):
        out = np.zeros((len(texts), 384), np.float32)
        for i, t in enumerate(texts):
            for w in re.findall(r"[a-z]+", t.lower()):
                out[i, zlib.crc32(w.encode()) % 384] += 1
        return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)


class FakeCE:
    """Scores a (question, passage) pair by word overlap, squashed to 0-1."""
    def predict(self, pairs, show_progress_bar=False):
        def words(s):
            return set(re.findall(r"[a-z]+", s.lower()))
        return [min(1.0, len(words(q) & words(p)) / 4) for q, p in pairs]


ROWS = [
    ("article", 17, "1", "Right to erasure", "The data subject shall have the right to obtain erasure of personal data"),
    ("article", 15, "1", "Right of access", "The data subject shall have the right to obtain access to personal data and a copy"),
    ("article", 3, "2", "Territorial scope", "This Regulation applies to a controller or processor not established in the Union offering goods"),
    ("recital", None, None, None, "A data subject should have the right to be forgotten and to erasure of personal data"),
    ("recital", None, None, None, "Controllers not established in the Union should be covered by this Regulation"),
]


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "CE_CACHE", tmp_path / "ce.json")   # never touch the real cache
    metas = []
    for i, (typ, art, para, title, text) in enumerate(ROWS):
        metas.append({"ordinal": i, "chunk_id": f"t{i}", "type": typ, "article_number": art, "paragraph": para,
                      "point": None, "citation": f"Article {art}({para})" if typ == "article" else f"Recital {i}",
                      "article_title": title, "chapter_title": None, "recital_number": None if typ == "article" else i,
                      "text": text})
    model = FakeModel()
    corpus = R.Corpus(metas, {"A": model.encode([m["text"] for m in metas])})
    ret = R.Retriever(corpus, model)
    ret._ce["fake"] = FakeCE()
    return ret


def cites(ret, idxs):
    return [ret.c.meta[i]["citation"] for i in idxs]


def test_article_pool_never_returns_recitals_even_when_a_recital_is_closer(engine):
    q = "right to be forgotten"
    all_pool = engine.search(q, R.Config("all", pool="all"))
    assert engine.c.meta[all_pool.order[0]]["type"] == "recital"          # the recital really is closest
    articles = engine.search(q, R.Config("art"))
    assert articles.order and all(engine.c.meta[i]["type"] == "article" for i in articles.order)


def test_context_recitals_are_recitals_only(engine):
    res = engine.search("right to erasure of personal data", R.Config("art"))
    ctx = engine.context_recitals(res, k=2)
    assert ctx and all(engine.c.meta[i]["type"] == "recital" for i, _ in ctx)


def test_glossary_union_surfaces_a_clause_dense_search_misses(engine):
    q = "do rules apply to companies outside the EU"
    dense_only = engine.search(q, R.Config("d", rerank="fake", sources="d", source_k=1))
    union = engine.search(q, R.Config("db", rerank="fake", sources="db", source_k=1))
    scope = next(i for i, m in enumerate(engine.c.meta) if m["article_number"] == 3)
    assert scope not in dense_only.cands            # first stage alone misses it
    assert scope in union.cands                      # glossary + BM25 adds it
    assert scope in union.rerank                     # and the reranker scores it


def test_reranker_scores_against_the_original_question_not_the_expansion(engine):
    seen = []
    class Spy(FakeCE):
        def predict(self, pairs, show_progress_bar=False):
            seen.extend(q for q, _ in pairs)
            return super().predict(pairs)
    engine._ce["fake"] = Spy()
    q = "companies outside the EU"
    engine.search(q, R.Config("db", rerank="fake", sources="db", source_k=2))
    assert seen and set(seen) == {q}


def test_rerank_scores_are_cached_per_query_and_passage(engine):
    calls = []
    class Counting(FakeCE):
        def predict(self, pairs, show_progress_bar=False):
            calls.append(len(pairs))
            return super().predict(pairs)
    engine._ce["fake"] = Counting()
    cfg = R.Config("c", rerank="fake", sources="d", source_k=3)
    engine.search("erasure of personal data", cfg)
    engine.search("erasure of personal data", cfg)
    assert len(calls) == 1


# ---------- pipeline output contract ----------

def test_no_basis_returns_no_provisions_and_no_recitals(engine, monkeypatch):
    monkeypatch.setattr(PL, "CONFIG", R.Config("t", rerank="fake", sources="d", source_k=3))
    out = PL.retrieve_evidence(engine, "xylophone quarterly revenue forecast")
    assert out["status"] == "no_basis" and out["provisions"] == [] and out["context"] == []
    assert "No GDPR provision" in out["note"]


def test_supported_answer_separates_operative_articles_from_recital_context(engine, monkeypatch):
    monkeypatch.setattr(PL, "CONFIG", R.Config("t", rerank="fake", sources="d", source_k=3))
    out = PL.retrieve_evidence(engine, "data subject right to obtain erasure of personal data")
    assert out["status"] == "supported" and out["confidence"] >= PL.SUPPORTED_FROM
    assert out["provisions"] and all(p["role"] == "operative" and p["citation"].startswith("Article") for p in out["provisions"])
    assert out["context"] and all(c["role"] == "interpretive_context" and c["citation"].startswith("Recital") for c in out["context"])
    assert out["provisions"][0]["citation"] == "Article 17(1)"


def test_weak_evidence_is_flagged(engine, monkeypatch):
    monkeypatch.setattr(PL, "CONFIG", R.Config("t", rerank="fake", sources="d", source_k=3))
    out = PL.retrieve_evidence(engine, "controller zebra giraffe lion")
    assert out["status"] == "weak_evidence" and "weakly" in out["note"] and out["provisions"]


def test_provisions_are_limited_to_a_score_band_around_the_best(engine, monkeypatch):
    monkeypatch.setattr(PL, "CONFIG", R.Config("t", rerank="fake", sources="d", source_k=3))
    q = "data subject right to obtain erasure of personal data"
    wide = PL.retrieve_evidence(engine, q, band=1.0)
    tight = PL.retrieve_evidence(engine, q, band=0.0)
    assert len(wide["provisions"]) == 3                       # every article in the corpus
    assert 1 <= len(tight["provisions"]) < len(wide["provisions"])
    assert tight["provisions"][0] == wide["provisions"][0]    # the best provision is always kept
    top = wide["provisions"][0]["score"]
    assert all(p["score"] >= top - PL.SCORE_BAND for p in PL.retrieve_evidence(engine, q)["provisions"])


def test_provision_count_never_exceeds_top_k(engine, monkeypatch):
    monkeypatch.setattr(PL, "CONFIG", R.Config("t", rerank="fake", sources="d", source_k=3))
    assert len(PL.retrieve_evidence(engine, "data subject personal data", top_k=2, band=1.0)["provisions"]) <= 2
