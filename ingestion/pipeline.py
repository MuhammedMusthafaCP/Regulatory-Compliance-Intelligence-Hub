"""The retrieval pipeline chosen by the evaluation (ADR 0002).

    question -> candidates (dense search + BM25 on the glossary-expanded question, articles only)
             -> cross-encoder rerank against the ORIGINAL question
             -> evidence status from the reranker's confidence
             -> recital context for the top articles, kept separate from the operative provisions

Articles are the operative law and are returned as `provisions`. Recitals are interpretive
context only: they are never ranked against articles and never returned as the answer.
Thresholds were calibrated on the dev set only; they belong to this reranker revision and must be
re-calibrated if the model changes.
"""
from .retrieval import Config, Retriever

CONFIG = Config("final", variant="A", rerank="mxbai-base", rerank_top=30, sources="db", source_k=15)
NO_BASIS_BELOW = 0.2     # reranker top-1 score; below this the sources do not support an answer
SUPPORTED_FROM = 0.5     # at or above this the top provision is treated as directly supporting
TOP_PROVISIONS = 5
CONTEXT_RECITALS = 3


def status_for(score):
    if score < NO_BASIS_BELOW:
        return "no_basis"
    return "weak_evidence" if score < SUPPORTED_FROM else "supported"


def retrieve_evidence(retriever, question, top_k=TOP_PROVISIONS, context_k=CONTEXT_RECITALS, debug=False):
    res = retriever.search(question, CONFIG)
    meta = retriever.c.meta
    confidence = max(res.rerank.values()) if res.rerank else 0.0
    status = status_for(confidence)
    out = {"question": question, "status": status, "confidence": round(confidence, 3),
           "provisions": [], "context": []}
    if status == "no_basis":
        out["note"] = "No GDPR provision supports an answer to this question."
        if debug:
            out["closest"] = [_item(meta[i], res.rerank[i], "operative") for i in res.order[:3]]
        return out
    if status == "weak_evidence":
        out["note"] = "The closest provisions only weakly match; they may not answer the question directly."
    out["provisions"] = [_item(meta[i], res.rerank[i], "operative") for i in res.order[:top_k]]
    out["context"] = [dict(_item(meta[i], s, "interpretive_context"), relevance=round(s, 3))
                      for i, s in retriever.context_recitals(res, k=context_k)]
    return out


def _item(m, score, role):
    d = {"role": role, "citation": m["citation"], "text": m["text"], "score": round(float(score), 3)}
    if m["type"] == "article":
        d["article"] = m["article_number"]
        d["article_title"] = m["article_title"]
    return d
