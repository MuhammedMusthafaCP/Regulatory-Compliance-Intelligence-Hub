"""Chunk the parsed GDPR records into retrieval units with citation metadata.

Reads data/parsed/gdpr/{articles,recitals,parse_report}.json, writes chunks.json and
chunk_report.json next to them. Deterministic; exits non-zero if validation fails.

    python3 -m ingestion.chunk_gdpr [--max-words 350]

Rules (first match wins, per article paragraph):
  1. Article 4 (definitions): one chunk per definition, lead-in dropped.
  2. Paragraph <= max_words: one chunk (lead-in + points + trailing text together).
  3. Paragraph > max_words with points: one chunk per top-level point with the lead-in
     prepended, plus a separate chunk for any trailing text.
  4. Paragraph > max_words without points: kept whole and flagged in the report.
Recitals: one chunk each. No overlap; every source word lands in exactly one chunk.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from .parse_gdpr import OUT, flatten, squash

REGULATION = "Regulation (EU) 2016/679 (GDPR)"
DOC_ID = "gdpr"
DEFINITIONS_ARTICLE = 4
ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]


def words(s):
    return len(s.split())


# ---------- text assembly ----------

def point_lines(points, depth=0):
    out = []
    for x in points:
        out.append("  " * depth + f"{x['label']} {x['text']}".rstrip())
        out.extend(point_lines(x["points"], depth + 1))
    return out


def point_flat(x):
    """Same concatenation as parse_gdpr.flatten uses, for the coverage check."""
    return x["label"] + x["text"] + "".join(point_flat(y) for y in x["points"])


# ---------- cross references ----------

ITEM = r"\d{1,3}(?:\(\d+\))?(?:\([a-z]\))?"
SEQ = rf"{ITEM}(?:(?:,\s*|\s+and\s+|\s+or\s+|\s+to\s+){ITEM})*"
ART_RE = re.compile(rf"\bArticles?\s+({SEQ})")
EXTERNAL_RE = re.compile(
    r"\s*(?:\([^)]*\)\s*)?of\s+(?!this Regulation)(?:the\s+)?"
    r"(?:Charter|Treaty|TFEU|TEU|Directive|Regulation|Council|Commission|Decision|Convention|Protocol|Framework|Statute)")
CHAIN_RE = re.compile(rf"(?:,?\s*(?:or|and)\s+Articles?\s+{SEQ})*")
TREATY_RE = re.compile(r"\s*(?:TFEU|TEU)\b")
PART_RE = re.compile(r"(\d{1,3})(?:\((\d+)\))?(?:\(([a-z])\))?")


def extract_refs(text):
    """Internal references to GDPR articles. Returns (refs, n_external_skipped)."""
    refs, external = [], 0
    for m in ART_RE.finditer(text):
        tail = CHAIN_RE.match(text, m.end()).end()  # "Article 25(6) or Article 26(4) of Directive ..."
        if EXTERNAL_RE.match(text, tail) or TREATY_RE.match(text, m.end()):
            external += 1
            continue
        seq = m.group(1)
        items = re.split(r"(,\s*|\s+and\s+|\s+or\s+|\s+to\s+)", seq)
        parts = items[0::2]
        seps = items[1::2]
        parsed = [PART_RE.fullmatch(p).groups() for p in parts]
        for i, (art, para, pt) in enumerate(parsed):
            if i > 0 and seps[i - 1].strip() == "to" and para is None and pt is None and parsed[i - 1][1] is None:
                for k in range(int(parsed[i - 1][0]) + 1, int(art) + 1):  # "Articles 12 to 22"
                    refs.append({"raw": m.group(0), "article": k, "paragraph": None, "point": None})
            else:
                refs.append({"raw": m.group(0), "article": int(art), "paragraph": para,
                             "point": f"({pt})" if pt else None})
    return refs, external


# ---------- chunk building ----------

def make_chunk(base, **kw):
    c = dict(base)
    c.update(kw)
    c["word_count"] = words(c["text"])
    return c


def article_chunks(a, max_words, base_url):
    n = a["number"]
    base = {
        "doc_id": DOC_ID, "regulation": REGULATION, "type": "article",
        "chapter": a["chapter"], "chapter_title": a["chapter_title"],
        "section": a["section"], "section_title": a["section_title"],
        "article_number": n, "article_title": a["title"], "article_id": f"{DOC_ID}:art{n}",
    }
    chunks = []
    multi = len(a["paragraphs"]) > 1
    for p in a["paragraphs"]:
        label, idx = p["label"], p["index"]
        pcode = f"p{label}" if label else f"u{idx}"
        if label:
            cite_p = f"Article {n}({label})"
        elif multi:
            cite_p = f"Article {n}, {ORDINALS[idx - 1]} paragraph"
        else:
            cite_p = f"Article {n}"
        anchor = p["anchor"] or a["anchor"]
        lead = p["text"]
        lead_piece = (label + "." if label else "") + lead
        pbase = dict(base, paragraph=label, paragraph_index=idx, source_anchor=anchor,
                     source_url=f"{base_url}#{anchor}")
        whole = "\n".join(x for x in [lead] + point_lines(p["points"]) + [p["trailing"]] if x)
        pieces = [lead_piece] + [point_flat(x) for x in p["points"]] + [p["trailing"]]

        def add(cid, cite, text, point, reason, own, lead_in="", extra=None):
            chunks.append(make_chunk(
                pbase, chunk_id=cid, citation=cite, point=point, split_reason=reason,
                text=text, lead_in=lead_in, cross_refs=[], _own=own))

        if n == DEFINITIONS_ARTICLE and p["points"]:
            for i, x in enumerate(p["points"]):
                own = ([lead_piece] if i == 0 else []) + [point_flat(x)]
                add(f"{DOC_ID}:art{n}:{pcode}:{x['label'].strip('()')}", f"Article {n}{x['label']}",
                    "\n".join(point_lines([x])), x["label"], "definition", own)
        elif words(whole) <= max_words or not p["points"]:
            add(f"{DOC_ID}:art{n}:{pcode}", cite_p, whole, None, "paragraph", pieces)
        else:
            for i, x in enumerate(p["points"]):
                text = "\n".join([lead] + point_lines([x]))
                own = ([lead_piece] if i == 0 else []) + [point_flat(x)]
                add(f"{DOC_ID}:art{n}:{pcode}:{x['label'].strip('()')}", f"{cite_p}{x['label']}",
                    text, x["label"], "point", own, lead_in=lead)
            if p["trailing"]:
                add(f"{DOC_ID}:art{n}:{pcode}:trailing", cite_p, p["trailing"], None, "trailing", [p["trailing"]])
    return chunks


def recital_chunk(r, base_url):
    return make_chunk(
        {"doc_id": DOC_ID, "regulation": REGULATION, "type": "recital"},
        chunk_id=f"{DOC_ID}:rct{r['number']}", citation=f"Recital {r['number']}",
        recital_number=r["number"], source_anchor=r["anchor"], source_url=f"{base_url}#{r['anchor']}",
        split_reason="recital", text=r["text"], lead_in="", cross_refs=[], _own=[r["text"]],
        footnote_refs=r["footnote_refs"])


def ref_resolves(art, ref):
    if ref["paragraph"] is None:
        return True
    labels = [p["label"] for p in art["paragraphs"]]
    if ref["paragraph"] in labels:
        return True
    # Article 4: "(1)" is a point of the single unnumbered paragraph
    return any(x["label"] == f"({ref['paragraph']})" for p in art["paragraphs"] for x in p["points"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-words", type=int, default=350)
    ap.add_argument("--dir", type=Path, default=OUT)
    args = ap.parse_args(argv)

    articles = json.loads((args.dir / "articles.json").read_text())
    recitals = json.loads((args.dir / "recitals.json").read_text())
    pr = json.loads((args.dir / "parse_report.json").read_text())
    if not pr["ok"]:
        sys.exit("parse_report.json is not ok; fix parsing first")
    base_url = pr["source"]["url"]
    by_num = {a["number"]: a for a in articles}

    chunks = []
    for a in articles:
        chunks.extend(article_chunks(a, args.max_words, base_url))
    chunks.extend(recital_chunk(r, base_url) for r in recitals)

    errs, warns, external_total = [], [], 0
    for c in chunks:
        refs, ext = extract_refs(c["text"])
        external_total += ext
        seen = set()
        for r in refs:
            key = (r["article"], r["paragraph"], r["point"])
            if key in seen:
                continue
            seen.add(key)
            art = by_num.get(r["article"])
            r["resolved"] = bool(art) and ref_resolves(art, r)
            if not r["resolved"]:
                warns.append(f"{c['chunk_id']}: unresolved reference {r['raw']!r} -> {key}")
            c["cross_refs"].append(r)

    # ---- validation ----
    ids = [c["chunk_id"] for c in chunks]
    cites = [c["citation"] for c in chunks]
    dup = [k for k, v in Counter(ids).items() if v > 1]
    errs += [f"duplicate chunk_id {d}" for d in dup]
    # citations may repeat only when the same paragraph is split (point chunks never repeat; trailing repeats the paragraph cite)
    cdup = [k for k, v in Counter((c["citation"], c["split_reason"] == "trailing") for c in chunks).items() if v > 1]
    errs += [f"duplicate citation {d[0]}" for d in cdup]
    for c in chunks:
        if not c["text"].strip():
            errs.append(f"{c['chunk_id']} empty")
        if c["word_count"] == 0:
            errs.append(f"{c['chunk_id']} zero words")
    for a in articles:  # every source word in exactly one chunk, in order
        got = "".join("".join(c["_own"]) for c in chunks if c.get("article_number") == a["number"])
        if squash(got) != squash(flatten(a)):
            errs.append(f"article {a['number']}: chunk coverage mismatch")
        if not any(c.get("article_number") == a["number"] for c in chunks):
            errs.append(f"article {a['number']}: no chunks")
    for r in recitals:
        got = [c for c in chunks if c.get("recital_number") == r["number"]]
        if len(got) != 1 or squash(got[0]["text"]) != squash(r["text"]):
            errs.append(f"recital {r['number']}: coverage mismatch")
    # recitals are kept whole by design, so only oversized article chunks are warnings
    over = [(c["chunk_id"], c["word_count"]) for c in chunks if c["word_count"] > args.max_words]
    for cid, wc in over:
        if cid.startswith(f"{DOC_ID}:art"):
            warns.append(f"{cid}: {wc} words exceeds limit (kept whole, no splittable points)")

    for i, c in enumerate(chunks):
        c["order"] = i
        c.pop("_own")

    wcs = sorted(c["word_count"] for c in chunks)
    q = lambda f: wcs[min(len(wcs) - 1, int(f * len(wcs)))]
    report = {
        "max_words": args.max_words,
        "source_sha256": pr["source"]["sha256"],
        "counts": {
            "chunks": len(chunks),
            "by_split_reason": dict(sorted(Counter(c["split_reason"] for c in chunks).items())),
            "by_type": dict(Counter(c["type"] for c in chunks)),
            "articles_covered": len({c["article_number"] for c in chunks if c["type"] == "article"}),
            "recitals_covered": len({c["recital_number"] for c in chunks if c["type"] == "recital"}),
        },
        "words": {"min": wcs[0], "p25": q(.25), "median": q(.5), "p75": q(.75), "p90": q(.9), "max": wcs[-1]},
        "over_limit": {
            "article_chunks": [{"chunk_id": a, "words": b} for a, b in over if a.startswith(f"{DOC_ID}:art")],
            "recitals": len([1 for a, b in over if a.startswith(f"{DOC_ID}:rct")]),
            "recitals_over_384_words": [a for a, b in over if a.startswith(f"{DOC_ID}:rct") and b > 384],
        },
        "cross_refs": {
            "chunks_with_refs": sum(1 for c in chunks if c["cross_refs"]),
            "internal_refs": sum(len(c["cross_refs"]) for c in chunks),
            "unresolved": sum(1 for c in chunks for r in c["cross_refs"] if not r["resolved"]),
            "external_skipped": external_total,
        },
        "ok": not errs, "errors": errs, "warnings": warns,
    }
    (args.dir / "chunks.json").write_text(json.dumps(chunks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.dir / "chunk_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("counts", "words", "cross_refs", "ok", "errors", "warnings")}, indent=2))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
