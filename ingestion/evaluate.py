"""Retrieval evaluation against evaluation/gdpr_questions.json (ADR Step 4).

    ingestion/.venv/bin/python -m ingestion.evaluate --check   # verify every gold reference matches a chunk
    ingestion/.venv/bin/python -m ingestion.evaluate           # run all configs against the DB, print metrics

A chunk is a hit for a gold entry when it is an article chunk with the same article and a consistent
paragraph/point, so results stay comparable if chunk boundaries change. Metrics (per config):
  hit@k     share of questions with at least one gold clause in the top k
  recall@k  average share of a question's gold clauses found in the top k
  MRR       mean of 1/rank of the first gold hit (0 if none in the top 10)
Configs vary the bge query prefix (on/off) and whether recitals are searchable.
"""
import argparse
import asyncio
import json
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text as sql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from .embedding import MODEL, QUERY_INSTRUCTION, REVISION, VARIANT_A, embed, load_model
from .load_gdpr import ROOT, database_url

QUESTIONS = ROOT / "evaluation/gdpr_questions.json"
RESULTS = ROOT / "evaluation/results"
KS = (1, 3, 5, 10)
TOP = 10

SQL = {
    scope: sql(f"""
    SELECT c.type, c.article_number, c.paragraph, c.point, c.citation,
           1 - (e.embedding <=> CAST(:q AS vector)) AS score
    FROM chunk_embeddings e JOIN chunks c ON c.id = e.chunk_id
    WHERE e.model = :m AND e.model_revision = :r AND e.variant = :v {extra}
    ORDER BY e.embedding <=> CAST(:q AS vector) LIMIT {TOP}""")
    for scope, extra in (("all", ""), ("articles", "AND c.type = 'article'"))
}


def is_hit(chunk, gold):
    if chunk["type"] != "article" or chunk["article_number"] != gold["article"]:
        return False
    if "paragraph" in gold and chunk["paragraph"] != gold["paragraph"]:
        return False
    if "point" in gold and chunk["point"] not in (None, gold["point"]):
        return False
    return True


def load_questions(path=None):
    return json.loads((path or QUESTIONS).read_text())["questions"]


def score_question(q, ranked):
    """ranked: list of chunk dicts, best first. Returns per-question metrics."""
    gold = q["relevant"]
    first = next((i for i, c in enumerate(ranked, 1) if any(is_hit(c, g) for g in gold)), None)
    m = {"first_hit_rank": first, "mrr": 1 / first if first else 0.0}
    for k in KS:
        top = ranked[:k]
        covered = sum(1 for g in gold if any(is_hit(c, g) for c in top))
        m[f"hit@{k}"] = float(covered > 0)
        m[f"recall@{k}"] = covered / len(gold)
    m["recitals_in_top5"] = sum(1 for c in ranked[:5] if c["type"] == "recital")
    return m


def check(chunks_path, questions_path=None):
    chunks = json.loads(chunks_path.read_text())
    bad = 0
    for q in load_questions(questions_path):
        for g in q["relevant"]:
            hits = [c for c in chunks if is_hit({"type": c["type"], "article_number": c.get("article_number"),
                                                 "paragraph": c.get("paragraph"), "point": c.get("point")}, g)]
            title = hits[0]["article_title"] if hits else "-"
            flag = "" if hits else "   <-- NO MATCHING CHUNK"
            bad += not hits
            print(f"{q['id']} {q['question'][:62]:62} -> {g}  [{len(hits)} chunk(s)] {title[:45]}{flag}")
    print(f"\n{bad} gold reference(s) without a matching chunk")
    return bad


async def run(model, questions):
    results = {}
    engine = create_async_engine(database_url(), poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            for prefix_on in (True, False):
                vecs = embed(model, [(QUERY_INSTRUCTION if prefix_on else "") + q["question"] for q in questions])
                for scope in ("all", "articles"):
                    name = f"prefix={'on' if prefix_on else 'off'},scope={scope}"
                    per_q = {}
                    for q, v in zip(questions, vecs):
                        rows = (await conn.execute(SQL[scope], {
                            "q": "[" + ",".join(f"{x:.7f}" for x in v) + "]",
                            "m": MODEL, "r": REVISION, "v": VARIANT_A})).mappings().all()
                        per_q[q["id"]] = [dict(r) for r in rows]
                    results[name] = per_q
    finally:
        await engine.dispose()
    return results


def summarise(questions, results):
    ans = [q for q in questions if q["answerable"]]
    out = {}
    for name, per_q in results.items():
        scored = {q["id"]: score_question(q, per_q[q["id"]]) for q in ans}
        agg = {"n": len(ans)}
        for k in KS:
            agg[f"hit@{k}"] = st.mean(s[f"hit@{k}"] for s in scored.values())
            agg[f"recall@{k}"] = st.mean(s[f"recall@{k}"] for s in scored.values())
        agg["MRR"] = st.mean(s["mrr"] for s in scored.values())
        agg["recitals_in_top5_avg"] = st.mean(s["recitals_in_top5"] for s in scored.values())
        agg["top1_score_answerable_median"] = st.median(per_q[q["id"]][0]["score"] for q in ans)
        un = [q for q in questions if not q["answerable"]]
        agg["top1_score_unanswerable_median"] = st.median(per_q[q["id"]][0]["score"] for q in un) if un else None
        out[name] = {"aggregate": agg, "per_question": scored}
    return out


def print_table(summary):
    cols = ["hit@1", "hit@3", "hit@5", "hit@10", "recall@5", "MRR", "recitals_in_top5_avg"]
    print(f"\n{'config':32}" + "".join(f"{c:>12}" for c in cols))
    for name, s in summary.items():
        print(f"{name:32}" + "".join(f"{s['aggregate'][c]:12.3f}" for c in cols))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify gold references against data/parsed/gdpr/chunks.json")
    ap.add_argument("--label", default="baseline_A")
    ap.add_argument("--questions", type=Path, default=None, help="questions file (default: the dev set)")
    a = ap.parse_args(argv)
    if a.check:
        return 1 if check(ROOT / "data/parsed/gdpr/chunks.json", a.questions) else 0
    questions = load_questions()
    model = load_model()
    results = asyncio.run(run(model, questions))
    summary = summarise(questions, results)
    print_table(summary)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{a.label}.json").write_text(json.dumps({
        "label": a.label, "model": MODEL, "revision": REVISION, "variant": VARIANT_A,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "questions_file": str(QUESTIONS.relative_to(ROOT)), "summary": summary,
        "rankings": {cfg: {qid: [{k: r[k] for k in ("citation", "type", "score")} for r in rows[:5]]
                           for qid, rows in per_q.items()} for cfg, per_q in results.items()},
    }, indent=2, default=float) + "\n")
    print(f"\nsaved evaluation/results/{a.label}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
