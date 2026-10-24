"""Load data/parsed/gdpr/chunks.json into the documents/chunks tables.

Idempotent: re-running upserts by chunk_id and removes chunks that no longer exist
(e.g. after re-chunking with a different --max-words). One transaction, one connection.
Run with the backend virtualenv (it has asyncpg/SQLAlchemy):

    backend/.venv/bin/python -m ingestion.load_gdpr [--dry-run]

DATABASE_URL comes from the environment or backend/.env. Run `alembic upgrade head` first.
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import dotenv_values  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.models.regulatory import Chunk, Document  # noqa: E402

PARSED = ROOT / "data/parsed/gdpr"
RAW_META = ROOT / "data/raw/gdpr/metadata.json"
SLUG = "gdpr"
# JSON field -> column, where they differ
RENAME = {"order": "ordinal"}
DOCUMENT_FIELDS = {"doc_id", "regulation"}  # stored once on the documents row


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def build_rows(chunks, document_id=None):
    cols = {c.name for c in Chunk.__table__.columns}
    rows = []
    for c in chunks:
        assert c["doc_id"] == SLUG, f"{c['chunk_id']}: unexpected doc_id {c['doc_id']!r}"
        r = {RENAME.get(k, k): v for k, v in c.items() if k not in DOCUMENT_FIELDS}
        r["text_sha256"] = sha256(c["text"])
        r["document_id"] = document_id
        extra = set(r) - cols
        if extra:
            sys.exit(f"{c['chunk_id']}: fields with no column: {sorted(extra)}")
        r.setdefault("footnote_refs", [])
        for name in cols - {"id", "created_at"}:  # batched insert needs identical keys in every row
            r.setdefault(name, None)
        rows.append({k: r[k] for k in sorted(r)})
    return rows


def load_inputs():
    chunks = json.loads((PARSED / "chunks.json").read_text())
    report = json.loads((PARSED / "chunk_report.json").read_text())
    parse_report = json.loads((PARSED / "parse_report.json").read_text())
    meta = json.loads(RAW_META.read_text())
    if not (report["ok"] and parse_report["ok"]):
        sys.exit("parse/chunk report not ok; fix those first")
    if report["source_sha256"] != parse_report["source"]["sha256"] or \
            parse_report["source"]["sha256"] != meta["files"][0]["sha256"]:
        sys.exit("source hash mismatch between raw metadata, parse report and chunk report")
    if len(chunks) != report["counts"]["chunks"]:
        sys.exit("chunks.json does not match chunk_report.json")
    doc = {
        "slug": SLUG, "title": chunks[0]["regulation"], "celex": meta["celex"],
        "language": meta["language"], "source_url": meta["source_url"],
        "retrieved_at": meta["retrieved_at"], "source_sha256": meta["files"][0]["sha256"],
        "chunk_max_words": report["max_words"],
    }
    return doc, chunks


def database_url():
    url = os.environ.get("DATABASE_URL") or dotenv_values(ROOT / "backend/.env").get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set (env or backend/.env)")
    return url


async def load(doc, chunks):
    engine = create_async_engine(database_url(), poolclass=NullPool)  # single short-lived connection
    try:
        async with engine.begin() as conn:
            stmt = insert(Document).values(**doc)
            stmt = stmt.on_conflict_do_update(
                index_elements=["slug"],
                set_={k: stmt.excluded[k] for k in doc if k != "slug"} | {"updated_at": func.now()},
            ).returning(Document.id)
            document_id = (await conn.execute(stmt)).scalar_one()

            rows = build_rows(chunks, document_id)
            ins = insert(Chunk)
            upsert = ins.on_conflict_do_update(
                index_elements=["chunk_id"],
                set_={k: ins.excluded[k] for k in rows[0] if k != "chunk_id"},
            )
            await conn.execute(upsert, rows)  # one batched round trip
            stale = await conn.execute(
                delete(Chunk).where(Chunk.document_id == document_id,
                                    Chunk.chunk_id.not_in([r["chunk_id"] for r in rows])))

            total = (await conn.execute(select(func.count()).select_from(Chunk)
                                        .where(Chunk.document_id == document_id))).scalar_one()
            by_type = dict((await conn.execute(select(Chunk.type, func.count()).where(
                Chunk.document_id == document_id).group_by(Chunk.type))).all())
            arts = (await conn.execute(select(func.count(func.distinct(Chunk.article_number)))
                                       .where(Chunk.document_id == document_id))).scalar_one()
            if total != len(rows):  # transaction rolls back on exception
                raise RuntimeError(f"expected {len(rows)} chunks in DB, found {total}")
    finally:
        await engine.dispose()
    print(json.dumps({"document_id": document_id, "chunks_in_db": total, "by_type": by_type,
                      "distinct_articles": arts, "stale_removed": stale.rowcount}, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="validate rows against the schema, no DB access")
    args = ap.parse_args(argv)
    doc, chunks = load_inputs()
    rows = build_rows(chunks, document_id=0)
    required = {c.name for c in Chunk.__table__.columns if not c.nullable
                and c.server_default is None and not c.primary_key}
    bad = [r["chunk_id"] for r in rows if any(r.get(k) is None for k in required)]
    if bad:
        sys.exit(f"rows missing required columns: {bad[:5]}")
    print(f"validated {len(rows)} rows for document {doc['slug']!r}")
    if args.dry_run:
        return 0
    asyncio.run(load(doc, chunks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
