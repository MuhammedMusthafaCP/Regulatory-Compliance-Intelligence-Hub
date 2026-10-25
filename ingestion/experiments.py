"""Run retrieval configs on the dev and held-out sets and print a comparison table.

    ingestion/.venv/bin/python -m ingestion.experiments baseline stage1 ...   # named suites below
    ... --heldout   # also report the held-out set (use only to confirm finished choices)
"""
import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np

from .embedding import load_model
from .evaluate import KS, QUESTIONS, ROOT, is_hit, load_questions, score_question
from .retrieval import Config, Corpus, Retriever

HELD = ROOT / "evaluation/gdpr_questions_heldout.json"
OOS_DEV = ROOT / "evaluation/gdpr_oos_dev.json"
CTX = json.loads((ROOT / "evaluation/recital_context.json").read_text())["map"]


def datasets(include_heldout):
    sets = {"dev": load_questions(QUESTIONS) + load_questions(OOS_DEV)}
    for q in sets["dev"]:
        q.setdefault("kind", "answerable" if q["answerable"] else "out_of_scope")
    if include_heldout:
        sets["held"] = load_questions(HELD)
    return sets


def auroc(pos, neg):
    """P(score_pos > score_neg), ties count half."""
    if not pos or not neg:
        return float("nan")
    p, n = np.array(pos), np.array(neg)
    return float(((p[:, None] > n[None, :]).sum() + 0.5 * (p[:, None] == n[None, :]).sum()) / (len(p) * len(n)))


def gold_context(q):
    out = set()
    for g in q["relevant"]:
        key = f"{g['article']}:{g['point']}" if "point" in g else str(g["article"])
        out.update(CTX.get(key, []))
    return out


def article_metrics(q, ranked):
    arts, seen = [], set()
    for c in ranked:
        if c["type"] == "article" and c["article_number"] not in seen:
            seen.add(c["article_number"]); arts.append(c["article_number"])
    gold = {g["article"] for g in q["relevant"]}
    first = next((i for i, a in enumerate(arts, 1) if a in gold), None)
    return {"a_hit@1": float(first == 1), "a_hit@3": float(first is not None and first <= 3),
            "a_hit@5": float(first is not None and first <= 5), "a_mrr": 1 / first if first else 0.0}


def signals(res, meta):
    top = res.order[0] if res.order else None
    d = res.dense
    out = {"dense_top1": float(d[top]) if top is not None else -1.0}
    if len(res.order) > 1:
        out["margin"] = float(d[res.order[0]] - d[res.order[1]])
    if res.rerank:
        out["rerank_top1"] = max(res.rerank.values())
    return out


def evaluate(ret, cfg, questions):
    ans = [q for q in questions if q["answerable"]]
    rows, sig, ctx_hits, ctx_n, ctx_off = {}, {}, [], 0, []
    for q in questions:
        res = ret.search(q["question"], cfg)
        ranked = [ret.c.meta[i] for i in res.order]
        sig[q["id"]] = signals(res, ret.c.meta)
        if q["answerable"]:
            m = score_question(q, ranked)
            m.update(article_metrics(q, ranked))
            pool_ids = res.cands or res.order[:cfg.rerank_top]
            m["cand_recall"] = float(any(ret.c.meta[i]["article_number"] in {g["article"] for g in q["relevant"]}
                                         for i in pool_ids))
            m["n_cands"] = len(pool_ids)
            rows[q["id"]] = m
            g = gold_context(q)
            if g:
                got = {ret.c.meta[i]["recital_number"] for i, _ in ret.context_recitals(res)}
                ctx_n += 1
                ctx_hits.append(float(bool(g & got)))
    agg = {k: st.mean(r[k] for r in rows.values()) for k in
           ("hit@1", "hit@3", "hit@5", "hit@10", "mrr", "recall@5", "a_hit@1", "a_hit@3", "a_hit@5", "a_mrr", "recitals_in_top5", "cand_recall", "n_cands")}
    agg["miss@5"] = [qid for qid, r in rows.items() if r["hit@5"] == 0]
    agg["a_miss@5"] = [qid for qid, r in rows.items() if r["a_hit@5"] == 0]
    agg["ctx_recall@3"] = st.mean(ctx_hits) if ctx_hits else float("nan")
    agg["n_ans"] = len(ans)
    for name in {k for s in sig.values() for k in s}:
        pos = [sig[q["id"]][name] for q in ans]
        for kind, label in (("out_of_scope", "oos"), ("insufficient", "insuf")):
            neg = [sig[q["id"]][name] for q in questions if q.get("kind") == kind]
            agg[f"auroc[{name}|{label}]"] = auroc(pos, neg)
        agg[f"auroc[{name}|all]"] = auroc(pos, [sig[q["id"]][name] for q in questions if not q["answerable"]])
    return {"aggregate": agg, "per_question": rows, "signals": sig}


def table(results, setname, extra_signal=None):
    cols = [("hit@1", "hit@1"), ("hit@5", "hit@5"), ("mrr", "MRR"), ("a_hit@1", "art@1"), ("a_hit@5", "art@5"),
            ("cand_recall", "cand"), ("ctx_recall@3", "ctx@3")]
    sigcols = sorted({k for r in results.values() for k in r[setname]["aggregate"] if k.startswith("auroc") and k.endswith("|all]")})
    print(f"\n=== {setname}  (n_answerable={next(iter(results.values()))[setname]['aggregate']['n_ans']})")
    print(f"{'config':34}" + "".join(f"{h:>8}" for _, h in cols) + f"{'miss5':>7}" + "".join(f"{s[6:-5][:14]:>15}" for s in sigcols))
    for name, r in results.items():
        a = r[setname]["aggregate"]
        print(f"{name:34}" + "".join(f"{a[k]:8.3f}" for k, _ in cols) + f"{len(a['miss@5']):7d}" +
              "".join(f"{a.get(s, float('nan')):15.3f}" for s in sigcols))


def grid():
    out = []
    for v in ("A", "T", "H"):
        out.append(Config(f"{v} +expand(dense)", variant=v, expand="dense"))
        for lx in ("title",):
            out.append(Config(f"{v} hybrid({lx}) no-expand", variant=v, lexical=lx))
            out.append(Config(f"{v} hybrid({lx}) expand(both)", variant=v, lexical=lx, expand="both"))
            out.append(Config(f"{v} hybrid({lx}) expand(lex)", variant=v, lexical=lx, expand="lexical"))
    out.append(Config("A hybrid(text) expand(both)", variant="A", lexical="text", expand="both"))
    return out


def sweep():
    out = []
    for w in (0.1, 0.2, 0.35, 0.5):
        out.append(Config(f"T hybrid(title) expand(both) w={w}", variant="T", lexical="title", expand="both", w_lex=w))
    return out


def rerank_suite():
    out = []
    for key in ("bge-base", "mxbai-base", "bge-m3"):
        out.append(Config(f"T+expand(dense) rerank={key}", variant="T", expand="dense", rerank=key))
    return out


def mxbai_suite():
    m = "mxbai-base"
    return [
        Config("T noexp +mxbai", variant="T", rerank=m),
        Config("A expand +mxbai", variant="A", expand="dense", rerank=m),
        Config("H expand +mxbai", variant="H", expand="dense", rerank=m),
        Config("T expand +mxbai top30", variant="T", expand="dense", rerank=m, rerank_top=30),
        Config("T expand +mxbai top50", variant="T", expand="dense", rerank=m, rerank_top=50),
    ]


UNION = [
    Config("A d + mxbai (dense top30)", variant="A", rerank="mxbai-base"),
    Config("A d+e union", variant="A", rerank="mxbai-base", sources="de"),
    Config("A d+b union", variant="A", rerank="mxbai-base", sources="db"),
    Config("A d+e+b union", variant="A", rerank="mxbai-base", sources="deb"),
    Config("A d+e+b union, e=T", variant="A", rerank="mxbai-base", sources="deb", src_variant_e="T"),
    Config("A d+e+b union k=25", variant="A", rerank="mxbai-base", sources="deb", source_k=25),
]

FINAL = [
    Config("A dense, articles only (no rerank)", variant="A"),
    Config("A noexp +mxbai", variant="A", rerank="mxbai-base"),
    Config("A expand +mxbai", variant="A", expand="dense", rerank="mxbai-base"),
    Config("T expand +mxbai", variant="T", expand="dense", rerank="mxbai-base"),
]

RELEASE = [
    Config("A dense, recitals in pool (BASELINE)", variant="A", pool="all"),
    Config("A dense, articles only", variant="A"),
    Config("A + mxbai rerank (dense top30)", variant="A", rerank="mxbai-base"),
    Config("A + mxbai + union d+b (CHOSEN)", variant="A", rerank="mxbai-base", sources="db", source_k=15),
]

SIB = [
    Config("CHOSEN (no siblings)", variant="A", rerank="mxbai-base", sources="db"),
    Config("CHOSEN + siblings of top 2", variant="A", rerank="mxbai-base", sources="db", siblings=2),
    Config("CHOSEN + siblings of top 3", variant="A", rerank="mxbai-base", sources="db", siblings=3),
]

SUITES = {
    "siblings": SIB,
    "release": RELEASE,
    "union": UNION,
    "final": FINAL,
    "mxbai": mxbai_suite(),
    "rerank": rerank_suite(),
    "grid": grid(),
    "sweep": sweep(),
    "baseline": [Config("A dense, recitals in pool", pool="all"), Config("A dense, articles only")],
    "variants": [Config("A dense", variant="A"), Config("T title+text", variant="T"), Config("H header+text", variant="H")],
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("suites", nargs="+")
    ap.add_argument("--heldout", action="store_true")
    ap.add_argument("--save", default="")
    a = ap.parse_args(argv)
    configs = [c for s in a.suites for c in SUITES[s]]
    data = datasets(a.heldout)
    ret = Retriever(Corpus.from_db(), load_model())
    results = {}
    for cfg in configs:
        t0 = time.time()
        results[cfg.name] = {name: evaluate(ret, cfg, qs) for name, qs in data.items()}
        ret.save_cache()
        dv = results[cfg.name]["dev"]["aggregate"]
        print(f"[{time.time() - t0:5.0f}s] {cfg.name:30} dev hit@1={dv['hit@1']:.3f} hit@5={dv['hit@5']:.3f} art@5={dv['a_hit@5']:.3f}",
              file=sys.stderr, flush=True)
    for name in data:
        table(results, name)
    if a.save:
        (ROOT / "evaluation/results" / f"{a.save}.json").write_text(json.dumps(
            {cfg: {s: {"aggregate": v["aggregate"], "per_question": v["per_question"]} for s, v in r.items()}
             for cfg, r in results.items()}, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
