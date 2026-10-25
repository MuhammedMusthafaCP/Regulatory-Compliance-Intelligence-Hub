"""Search the GDPR chunks.

Default: the evaluated pipeline (ADR 0002): candidates -> rerank -> evidence status, with the
operative articles and the interpretive recitals reported separately.

    ingestion/.venv/bin/python -m ingestion.search_chunks "when can I process data without consent?"
    ... --json             # machine-readable output
    ... --baseline         # the original exact dense search over the stored vectors (DB); with
    ...                    #   --local (no DB) and --no-instruction (skip bge's query prefix) variants
"""
import argparse
import asyncio
import json
import sys

import numpy as np
from sqlalchemy import text as sql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from .embedding import MODEL, QUERY_INSTRUCTION, REVISION, VARIANT_A, embed, load_model
from .load_gdpr import PARSED, database_url

SQL = sql("""
    SELECT c.citation, c.article_title, c.text, 1 - (e.embedding <=> CAST(:q AS vector)) AS score
    FROM chunk_embeddings e JOIN chunks c ON c.id = e.chunk_id
    WHERE e.model = :m AND e.model_revision = :r AND e.variant = :v
    ORDER BY e.embedding <=> CAST(:q AS vector) LIMIT :k""")


def show(question, hits):
    print(f"\nQ: {question}")
    for i, (cite, title, text, score) in enumerate(hits, 1):
        label = f"{cite} — {title}" if title else cite
        print(f"  {i}. {score:.3f}  {label}\n       {' '.join(text.split())[:130]}…")


async def db_search(model, questions, k, prefix):
    engine = create_async_engine(database_url(), poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            for q in questions:
                v = embed(model, [prefix + q])[0]
                rows = (await conn.execute(SQL, {"q": "[" + ",".join(f"{x:.7f}" for x in v) + "]",
                                                 "m": MODEL, "r": REVISION, "v": VARIANT_A, "k": k})).all()
                show(q, [tuple(r) for r in rows])
    finally:
        await engine.dispose()


def local_search(model, questions, k, prefix):
    chunks = json.loads((PARSED / "chunks.json").read_text())
    mat = embed(model, [c["text"] for c in chunks], progress=True)
    for q in questions:
        scores = mat @ embed(model, [prefix + q])[0]   # cosine == dot product (normalised)
        top = np.argsort(-scores)[:k]
        show(q, [(chunks[i]["citation"], chunks[i].get("article_title"), chunks[i]["text"], float(scores[i])) for i in top])


def pipeline_search(questions, as_json, k):
    from .pipeline import retrieve_evidence
    from .retrieval import Corpus, Retriever
    ret = Retriever(Corpus.from_db(variants=("A",)), load_model())
    for q in questions:
        r = retrieve_evidence(ret, q, top_k=k)
        if as_json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
            continue
        print(f"\nQ: {q}\n  status: {r['status']}  (confidence {r['confidence']})" + (f"\n  note: {r['note']}" if "note" in r else ""))
        for p in r["provisions"]:
            print(f"  [operative] {p['citation']:18} {p['score']:.2f}  {p.get('article_title', '')[:50]}\n       {' '.join(p['text'].split())[:130]}…")
        for c in r["context"]:
            print(f"  [context]   {c['citation']:18} {c['relevance']:.2f}  {' '.join(c['text'].split())[:100]}…")
    ret.save_cache()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("questions", nargs="+")
    ap.add_argument("--baseline", action="store_true", help="original dense search (no rerank, recitals mixed in)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--no-instruction", action="store_true")
    a = ap.parse_args(argv)
    if not a.baseline:
        pipeline_search(a.questions, a.json, min(a.k, 5) if a.k else 5)
        return 0
    prefix = "" if a.no_instruction else QUERY_INSTRUCTION
    model = load_model()
    if a.local:
        local_search(model, a.questions, a.k, prefix)
    else:
        asyncio.run(db_search(model, a.questions, a.k, prefix))
    return 0


if __name__ == "__main__":
    sys.exit(main())
