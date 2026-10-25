"""Embed chunks with the baseline model (variant A: the chunk text, unchanged) and store them.

Idempotent: only chunks with no vector for this (model, revision, variant), or whose text
changed since it was embedded, are processed. Run with the ingestion virtualenv, from the repo root:

    ingestion/.venv/bin/python -m ingestion.embed_chunks            # embed + store
    ingestion/.venv/bin/python -m ingestion.embed_chunks --dry-run  # embed chunks.json locally, no DB
    ingestion/.venv/bin/python -m ingestion.embed_chunks --variant T  # title+text variant (see embedding.VARIANTS)
"""
import argparse
import asyncio
import json
import sys
import time

import numpy as np
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from .embedding import DIM, MODEL, REVISION, VARIANT_A, VARIANTS, embed, load_model, text_sha256, truncated
from .load_gdpr import PARSED, database_url  # also puts backend/ on sys.path

from app.models.regulatory import Chunk, ChunkEmbedding  # noqa: E402


def report_model(model, texts):
    cut, limit, longest = truncated(model, texts)
    print(f"model {MODEL}@{REVISION[:8]} dim={DIM} max_seq_length={limit}; longest chunk={longest} tokens; "
          f"{len(cut)} chunk(s) would be truncated")
    return cut


async def run(args):
    variant = args.variant
    build = VARIANTS[variant]
    engine = create_async_engine(database_url(), poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            same = and_(ChunkEmbedding.chunk_id == Chunk.id, ChunkEmbedding.model == MODEL,
                        ChunkEmbedding.model_revision == REVISION, ChunkEmbedding.variant == variant)
            rows = (await conn.execute(
                select(Chunk.id, Chunk.chunk_id, Chunk.text, Chunk.type, Chunk.citation, Chunk.article_title,
                       Chunk.chapter_title, ChunkEmbedding.embedded_text_sha256)
                .outerjoin(ChunkEmbedding, same).order_by(Chunk.ordinal))).all()
        inputs = {r.id: build(r._asdict()) for r in rows}
        todo = [r for r in rows if r.embedded_text_sha256 != text_sha256(inputs[r.id])]
        print(f"{len(rows)} chunks in DB, {len(todo)} need embedding")
        if not todo:
            return
        model = load_model()
        cut = report_model(model, [inputs[r.id] for r in todo])
        t0 = time.time()
        vecs = embed(model, [inputs[r.id] for r in todo], progress=True)
        print(f"embedded {len(todo)} chunks in {time.time() - t0:.1f}s")
        assert vecs.shape == (len(todo), DIM) and np.isfinite(vecs).all()
        assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-3), "vectors not normalised"

        payload = [{"chunk_id": r.id, "model": MODEL, "model_revision": REVISION, "variant": variant,
                    "embedded_text_sha256": text_sha256(inputs[r.id]), "embedding": v.tolist()}
                   for r, v in zip(todo, vecs)]
        ins = insert(ChunkEmbedding)
        stmt = ins.on_conflict_do_update(
            constraint="uq_chunk_embeddings_chunk_model_variant",
            set_={"embedding": ins.excluded.embedding,
                  "embedded_text_sha256": ins.excluded.embedded_text_sha256,
                  "embedded_at": func.now()})
        async with engine.begin() as conn:  # one transaction, one batched insert
            await conn.execute(stmt, payload)
            n = (await conn.execute(select(func.count()).select_from(ChunkEmbedding)
                                    .where(ChunkEmbedding.model == MODEL, ChunkEmbedding.model_revision == REVISION,
                                           ChunkEmbedding.variant == variant))).scalar_one()
            if n != len(rows):
                raise RuntimeError(f"expected {len(rows)} embeddings, found {n}")
        print(f"stored; chunk_embeddings now has {n} rows for variant {variant}")
    finally:
        await engine.dispose()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="embed data/parsed/gdpr/chunks.json locally; no DB access")
    ap.add_argument("--variant", choices=sorted(VARIANTS), default=VARIANT_A, help="which text is embedded")
    args = ap.parse_args(argv)
    if args.dry_run:
        chunks = json.loads((PARSED / "chunks.json").read_text())
        model = load_model()
        report_model(model, [c["text"] for c in chunks])
        t0 = time.time()
        vecs = embed(model, [c["text"] for c in chunks], progress=True)
        print(f"embedded {len(chunks)} chunks in {time.time() - t0:.1f}s; shape={vecs.shape}; "
              f"norms ok={np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-3)}")
        return 0
    asyncio.run(run(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
