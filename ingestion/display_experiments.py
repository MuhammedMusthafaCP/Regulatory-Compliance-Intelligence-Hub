"""How many provisions / recitals should the answer show? Measured on dev and held-out.

    HF_HUB_OFFLINE=1 ingestion/.venv/bin/python -m ingestion.display_experiments

Provision rules operate on the reranked list; recital rules on the context candidates.
Precision is a LOWER bound: gold lists are short and some extra clauses are legitimately useful.
"""
import json
import statistics as st
import sys

from .embedding import load_model
from .evaluate import ROOT, is_hit
from .experiments import datasets, gold_context
from .pipeline import CONFIG
from .retrieval import Corpus, Retriever


def provision_rules():
    rules = {"top5 (current)": lambda s: list(range(min(5, len(s)))), "top3": lambda s: list(range(min(3, len(s))))}
    for d in (0.02, 0.05, 0.1, 0.2):
        rules[f"within {d} of top1 (max5)"] = lambda s, d=d: [i for i in range(min(5, len(s))) if s[i] >= s[0] - d] or [0]
    rules["score>=0.9 (max5)"] = lambda s: [i for i in range(min(5, len(s))) if s[i] >= 0.9] or [0]
    return rules


def recital_rules():
    rules = {"top3 (current)": lambda r: r[:3], "top2": lambda r: r[:2], "top1": lambda r: r[:1]}
    for t in (0.7, 0.75, 0.8, 0.85):
        rules[f"rel>={t} (max3)"] = lambda r, t=t: [x for x in r[:3] if x[1] >= t]
    return rules


def main():
    data = datasets(True)
    ret = Retriever(Corpus.from_db(variants=("A",)), load_model())
    meta = ret.c.meta
    runs = {sn: [(q, ret.search(q["question"], CONFIG)) for q in qs if q["answerable"]] for sn, qs in data.items()}
    ret.save_cache()
    out = {"provisions": {}, "recitals": {}}

    print("PROVISIONS shown (answerable questions)")
    print(f"{'rule':26}" + "".join(f" | {sn:4} any-hit  gold-rec  art-prec  avg-shown" for sn in runs))
    for name, rule in provision_rules().items():
        row, rec = f"{name:26}", {}
        for sn, items in runs.items():
            anyhit, grec, aprec, shown = [], [], [], []
            for q, res in items:
                order = res.order
                sc = [res.rerank[i] for i in order]
                keep = [order[k] for k in rule(sc)]
                gold = q["relevant"]
                anyhit.append(float(any(is_hit(meta[i], g) for i in keep for g in gold)))
                grec.append(sum(any(is_hit(meta[i], g) for i in keep) for g in gold) / len(gold))
                ga = {g["article"] for g in gold}
                aprec.append(sum(meta[i]["article_number"] in ga for i in keep) / len(keep))
                shown.append(len(keep))
            rec[sn] = {"any_hit": st.mean(anyhit), "gold_recall": st.mean(grec), "article_precision_lb": st.mean(aprec),
                       "avg_shown": st.mean(shown), "n_any_hit": int(sum(anyhit)), "n": len(anyhit)}
            row += f" |      {rec[sn]['any_hit']:.3f}    {rec[sn]['gold_recall']:.3f}     {rec[sn]['article_precision_lb']:.3f}      {rec[sn]['avg_shown']:.2f}"
        out["provisions"][name] = rec
        print(row)

    print("\nRECITAL context shown (questions that have a recital reference)")
    print(f"{'rule':26}" + "".join(f" | {sn:4} any-gold  precision  avg-shown  none-shown" for sn in runs))
    for name, rule in recital_rules().items():
        row, rec = f"{name:26}", {}
        for sn, items in runs.items():
            hit, prec, shown, none = [], [], [], []
            for q, res in items:
                g = gold_context(q)
                if not g:
                    continue
                got = [(meta[i]["recital_number"], s) for i, s in ret.context_recitals(res, k=3)]
                kept = rule(got)
                nums = {n for n, _ in kept}
                hit.append(float(bool(g & nums)))
                prec.append(len(g & nums) / len(kept) if kept else 0.0)
                shown.append(len(kept)); none.append(float(not kept))
            rec[sn] = {"any_gold": st.mean(hit), "precision_lb": st.mean(prec), "avg_shown": st.mean(shown),
                       "none_shown": st.mean(none), "n": len(hit)}
            row += f" |      {rec[sn]['any_gold']:.3f}    {rec[sn]['precision_lb']:.3f}      {rec[sn]['avg_shown']:.2f}      {rec[sn]['none_shown']:.2f}"
        out["recitals"][name] = rec
        print(row)
    (ROOT / "evaluation/results/display_tweaks.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    sys.exit(main())
