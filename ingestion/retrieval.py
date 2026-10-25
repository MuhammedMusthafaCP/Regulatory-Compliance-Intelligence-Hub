"""Retrieval pipeline used by the experiments (and, once chosen, the search CLI).

Stages (each switchable through Config so every change can be measured against the baseline):
  1. dense search over a chosen embedding variant (cosine; vectors are normalised)
  2. optional lay->legal query expansion (glossary)
  3. optional BM25 lexical search, fused with dense results by reciprocal rank fusion
  4. optional cross-encoder rerank of the top candidates
Articles (the operative law) and recitals (interpretive context) are kept in separate pools.
"""
import asyncio
import hashlib
import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from sqlalchemy import text as sql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from .embedding import MODEL, QUERY_INSTRUCTION, REVISION, embed
from .glossary import expanded_query
from .lexical import BM25
from .load_gdpr import database_url

RRF_K = 60
CE_CACHE = Path(__file__).resolve().parent.parent / "evaluation/results/.rerank_cache.pkl"  # git-ignored


@dataclass(frozen=True)
class Config:
    name: str
    variant: str = "A"
    prefix: bool = False
    expand: str = "none"        # none | dense | lexical | both
    lexical: str = "none"       # none | text | title   (what BM25 indexes)
    w_lex: float = 1.0          # weight of the lexical ranking in RRF
    pool: str = "articles"      # articles | all
    rerank: str = ""            # "" or a key of RERANKERS
    rerank_top: int = 30
    # Candidate union (needs rerank): which first-stage sources feed the reranker, k per source.
    #   d = dense on the question, e = dense on the glossary-expanded question, b = BM25 on the expanded question.
    # The reranker always scores candidates against the ORIGINAL question, so expansion can only add
    # recall, never distort the final order.
    sources: str = ""
    source_k: int = 15
    src_variant_e: str = ""     # embedding variant for source "e" (default: cfg.variant)
    # Small-to-big: after the first rerank, also score every other chunk of the top N articles
    # (finding part of an article is a strong hint to look at the rest), then rerank everything.
    siblings: int = 0


class Corpus:
    def __init__(self, meta, vectors):
        self.meta = meta                       # list of dicts, ordered by ordinal
        self.vec = vectors                     # variant -> (n, 384) float32
        self.n = len(meta)
        self.is_article = np.array([m["type"] == "article" for m in meta])
        self.bm25 = {
            "text": BM25([m["text"] for m in meta]),
            "title": BM25([f"{m['article_title'] or ''} {m['text']}" for m in meta]),
        }

    @classmethod
    def from_db(cls, variants=("A", "T", "H")):
        async def fetch():
            eng = create_async_engine(database_url(), poolclass=NullPool)
            try:
                async with eng.connect() as c:
                    meta = [dict(r) for r in (await c.execute(sql(
                        "SELECT ordinal, chunk_id, type, article_number, paragraph, point, citation, article_title, "
                        "chapter_title, recital_number, text FROM chunks ORDER BY ordinal"))).mappings()]
                    vecs = {}
                    for v in variants:
                        rows = (await c.execute(sql(
                            "SELECT c.ordinal, e.embedding::text FROM chunk_embeddings e JOIN chunks c ON c.id = e.chunk_id "
                            "WHERE e.model = :m AND e.model_revision = :r AND e.variant = :v ORDER BY c.ordinal"),
                            {"m": MODEL, "r": REVISION, "v": v})).all()
                        assert len(rows) == len(meta), f"variant {v}: {len(rows)} vectors for {len(meta)} chunks"
                        vecs[v] = np.array([json.loads(r[1]) for r in rows], dtype=np.float32)
                    return meta, vecs
            finally:
                await eng.dispose()
        meta, vecs = asyncio.run(fetch())
        return cls(meta, vecs)


@dataclass
class Result:
    order: list                                  # chunk indexes, best first (primary pool)
    dense: np.ndarray                            # dense cosine for every chunk
    fused: np.ndarray                            # score used for the final order (before rerank)
    rerank: dict = field(default_factory=dict)   # chunk index -> cross-encoder score
    query_vec: np.ndarray = None
    cands: list = field(default_factory=list)    # first-stage candidates handed to the reranker


class Retriever:
    def __init__(self, corpus, model):
        self.c, self.model = corpus, model
        self._qcache, self._ce = {}, {}
        try:
            self._ce_scores = pickle.loads(CE_CACHE.read_bytes())
        except Exception:
            self._ce_scores = {}   # (reranker key, query, passage hash) -> score

    def save_cache(self):
        CE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        CE_CACHE.write_bytes(pickle.dumps(self._ce_scores))

    def ce_scores(self, key, q, texts):
        """Cross-encoder scores, computed once per (reranker, query, passage) and cached on disk."""
        keys = [(key, q, hashlib.md5(t.encode()).hexdigest()) for t in texts]
        missing = [i for i, k in enumerate(keys) if k not in self._ce_scores]
        if missing:
            new = self.cross_encoder(key).predict([(q, texts[i]) for i in missing], show_progress_bar=False)
            for i, sc in zip(missing, new):
                self._ce_scores[keys[i]] = float(sc)
        return [self._ce_scores[k] for k in keys]

    def qvec(self, text, prefix):
        key = (text, prefix)
        if key not in self._qcache:
            self._qcache[key] = embed(self.model, [(QUERY_INSTRUCTION if prefix else "") + text])[0]
        return self._qcache[key]

    def cross_encoder(self, key):
        if key not in self._ce:
            from .rerank import load_reranker
            self._ce[key] = load_reranker(key)
        return self._ce[key]

    def search(self, q, cfg, top=50):
        c = self.c
        dense_q = expanded_query(q) if cfg.expand in ("dense", "both") else q
        qv = self.qvec(dense_q, cfg.prefix)
        dense = c.vec[cfg.variant] @ qv
        pool = np.ones(c.n, bool) if cfg.pool == "all" else c.is_article.copy()
        fused = np.where(pool, dense, -np.inf)
        if cfg.lexical != "none":
            lex_q = expanded_query(q) if cfg.expand in ("lexical", "both") else q
            lex = np.array(c.bm25[cfg.lexical].scores(lex_q))
            rd = _ranks(np.where(pool, dense, -np.inf))
            fused = np.where(pool, 1.0 / (RRF_K + rd), -np.inf)
            lex_pool = np.where(pool & (lex > 0), lex, -np.inf)
            rl = _ranks(lex_pool)
            fused = fused + np.where(np.isfinite(lex_pool), cfg.w_lex / (RRF_K + rl), 0.0)
        order = [int(i) for i in np.argsort(-fused)[:top] if np.isfinite(fused[i])]
        res = Result(order=order, dense=dense, fused=fused, query_vec=qv)
        if cfg.rerank and cfg.sources:
            cand = self._union(q, cfg, pool)
            res.cands = cand
            scores = self.ce_scores(cfg.rerank, q, [_passage(c.meta[i]) for i in cand])
            res.rerank = {i: float(sc) for i, sc in zip(cand, scores)}
            res.order = sorted(cand, key=lambda i: -res.rerank[i])
            if cfg.siblings:
                top_arts = []
                for i in res.order:
                    a = c.meta[i]["article_number"]
                    if a not in top_arts:
                        top_arts.append(a)
                    if len(top_arts) == cfg.siblings:
                        break
                extra = [j for j, m in enumerate(c.meta) if m["type"] == "article"
                         and m["article_number"] in top_arts and j not in res.rerank]
                if extra:
                    more = self.ce_scores(cfg.rerank, q, [_passage(c.meta[j]) for j in extra])
                    res.rerank.update({j: float(sc) for j, sc in zip(extra, more)})
                    res.cands = res.cands + extra
                    res.order = sorted(res.rerank, key=lambda i: -res.rerank[i])
            return res
        if cfg.rerank:
            cand = order[:cfg.rerank_top]
            res.cands = cand
            texts = [_passage(c.meta[i]) for i in cand]
            scores = self.ce_scores(cfg.rerank, q, texts)
            res.rerank = {i: float(s) for i, s in zip(cand, scores)}
            order = sorted(cand, key=lambda i: -res.rerank[i]) + order[cfg.rerank_top:]
            res.order = order
        return res

    def _union(self, q, cfg, pool):
        c, k, cand = self.c, cfg.source_k, []
        def add(scores):
            masked = np.where(pool, scores, -np.inf)
            for i in np.argsort(-masked)[:k]:
                if np.isfinite(masked[i]) and int(i) not in cand:
                    cand.append(int(i))
        exp_q = expanded_query(q)
        if "d" in cfg.sources:
            add(c.vec[cfg.variant] @ self.qvec(q, cfg.prefix))
        if "e" in cfg.sources:
            add(c.vec[cfg.src_variant_e or cfg.variant] @ self.qvec(exp_q, cfg.prefix))
        if "b" in cfg.sources:
            add(np.array(c.bm25["title"].scores(exp_q)))
        return cand

    def context_recitals(self, res, k=3, n_articles=3, w_query=0.5):
        """Recitals to show as interpretive context for the top articles (never as the answer).

        Score = w * similarity(query, recital) + (1-w) * best similarity(recital, one of the top articles).
        """
        c = self.c
        arts = [i for i in res.order if c.is_article[i]][:n_articles]
        if not arts:
            return []
        V = c.vec["A"]
        rec = np.where(~c.is_article)[0]
        q_sim = V[rec] @ res.query_vec
        a_sim = (V[rec] @ V[arts].T).max(axis=1)
        score = w_query * q_sim + (1 - w_query) * a_sim
        top = np.argsort(-score)[:k]
        return [(int(rec[i]), float(score[i])) for i in top]


def _ranks(scores):
    """1-based rank of every element (best = 1); -inf entries get a rank but are masked by callers."""
    order = np.argsort(-scores)
    r = np.empty(len(scores), int)
    r[order] = np.arange(1, len(scores) + 1)
    return r


def _passage(m):
    return f"{m['article_title']}. {m['text']}" if m["type"] == "article" else m["text"]
