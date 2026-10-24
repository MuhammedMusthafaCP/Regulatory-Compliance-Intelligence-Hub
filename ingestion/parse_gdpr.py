"""Parse the raw EUR-Lex GDPR HTML into structured records and validate them.

Deterministic and dependency-free: the same raw file always yields byte-identical output.

    python3 -m ingestion.parse_gdpr [--raw PATH] [--out DIR]

Outputs (data/parsed/gdpr/): structure.json, articles.json, recitals.json,
footnotes.json, parse_report.json. Exits non-zero if any validation check fails.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from .htmltree import Node, parse

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/gdpr/gdpr-celex-32016R0679-en.html"
OUT = ROOT / "data/parsed/gdpr"

EXPECTED = {"articles": 99, "recitals": 173, "chapters": 11, "sections": 15}
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}
ROMAN_CHAPTERS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


# ---------- helpers ----------

def kids(n):
    return [c for c in n.children if isinstance(c, Node)]


def cls(n):
    return (n.get("class") or "").split()


def is_note_ref(n):
    """Footnote marker: <a>(<span class="oj-note-tag">N</span>)</a>."""
    return n.tag == "a" and any("oj-note-tag" in cls(s) for s in n.iter() if s is not n)


def note_ref_number(n):
    return int("".join(s.children[0] for s in n.iter() if "oj-note-tag" in cls(s)).strip())


def raw_text(n):
    """Text of a node, footnote markers dropped, whitespace untouched."""
    out = []
    for c in n.children:
        if isinstance(c, str):
            out.append(c)
        elif is_note_ref(c):
            continue
        else:
            out.append(raw_text(c))
    return "".join(out)


def clean(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def text(n):
    return clean(raw_text(n))


def squash(s):
    return re.sub(r"\s+", "", s.replace("\xa0", ""))


def note_refs(n):
    return [note_ref_number(a) for a in n.iter() if is_note_ref(a)]


def heading_text(container, kind):
    """Text of the first <p class=kind> directly in container (e.g. 'CHAPTER I')."""
    for c in kids(container):
        if c.tag == "p" and kind in cls(c):
            return text(c)
    return None


def title_text(container):
    for c in kids(container):
        if "eli-title" in cls(c):
            return text(c)
    return None


# ---------- points (tables) ----------

def parse_table(tbl):
    """A <table> is one point: [label cell][content cell]; content may nest tables."""
    rows = [r for b in kids(tbl) if b.tag == "tbody" for r in kids(b) if r.tag == "tr"]
    assert len(rows) == 1, "unexpected multi-row table"
    cells = [c for c in kids(rows[0]) if c.tag == "td"]
    assert len(cells) == 2, "unexpected table shape"
    label = text(cells[0])
    paras, subs = [], []
    for c in kids(cells[1]):
        if c.tag == "p":
            paras.append(text(c))
        elif c.tag == "table":
            subs.append(parse_table(c))
        else:
            raise ValueError(f"unexpected <{c.tag}> in point {label}")
    return {"label": label, "text": "\n".join(p for p in paras if p), "points": subs}


# ---------- articles ----------

def parse_paragraph_div(div, article_no):
    """Numbered paragraph: lead-in <p>(s), point tables, optional trailing <p>(s)."""
    lead, points, trail, interleaved = [], [], [], False
    for c in kids(div):
        if c.tag == "p":
            (trail if points else lead).append(text(c))
        elif c.tag == "table":
            if trail:
                interleaved = True
            points.append(parse_table(c))
        else:
            raise ValueError(f"unexpected <{c.tag}> in {div.get('id')}")
    ordinal = int(div.get("id").split(".")[1])
    body = "\n".join(lead)
    m = re.match(r"(\d+)\.\s+", body)
    label = None
    if m:
        label, body = m.group(1), body[m.end():]
    return {
        "label": label, "ordinal": ordinal, "anchor": div.get("id"),
        "text": body, "points": points, "trailing": "\n".join(trail),
        "_interleaved": interleaved,
    }


def parse_article(div, chapter, section):
    aid = div.get("id")
    number = int(aid.split("_")[1])
    title = title_text(div)
    paragraphs = []
    for c in kids(div):
        if c.tag == "div" and re.fullmatch(r"\d{3}\.\d{3}", c.get("id") or ""):
            paragraphs.append(parse_paragraph_div(c, number))
        elif c.tag == "p" and "oj-normal" in cls(c):  # unnumbered paragraph
            paragraphs.append({"label": None, "ordinal": None, "anchor": None,
                               "text": text(c), "points": [], "trailing": "", "_interleaved": False})
        elif c.tag == "table":  # points directly under the article (Art. 4): attach to previous paragraph
            paragraphs[-1]["points"].append(parse_table(c))
        elif c.tag == "p" and "oj-ti-art" in cls(c) or "eli-title" in cls(c):
            continue
        else:
            raise ValueError(f"unexpected <{c.tag} {c.get('class')}> in {aid}")
    for i, p in enumerate(paragraphs, 1):
        p["index"] = i
    return {
        "type": "article", "number": number, "anchor": aid, "title": title,
        "chapter": chapter["number"], "chapter_title": chapter["title"],
        "section": section["number"] if section else None,
        "section_title": section["title"] if section else None,
        "paragraphs": paragraphs,
    }


# ---------- recitals ----------

def parse_recital(div):
    rid = div.get("id")
    tbl = next(c for c in kids(div) if c.tag == "table")
    cells = [c for b in kids(tbl) if b.tag == "tbody" for r in kids(b) for c in kids(r) if c.tag == "td"]
    assert len(cells) == 2, f"unexpected recital shape {rid}"
    paras = [text(p) for p in kids(cells[1]) if p.tag == "p"]
    assert len(paras) == len(kids(cells[1])), f"non-<p> content in {rid}"
    return {
        "type": "recital", "number": int(rid.split("_")[1]), "anchor": rid,
        "label": text(cells[0]), "text": "\n".join(paras),
        "footnote_refs": note_refs(cells[1]),
    }


# ---------- top level ----------

def walk(root):
    byid = {n.get("id"): n for n in root.iter() if n.get("id")}
    recitals = [parse_recital(n) for n in root.iter()
                if re.fullmatch(r"rct_\d+", n.get("id") or "")]
    chapters, sections, articles = [], [], []
    for n in root.iter():
        i = n.get("id") or ""
        if re.fullmatch(r"cpt_[IVX]+", i):
            chapters.append({
                "anchor": i, "number": i.split("_")[1],
                "heading": heading_text(n, "oj-ti-section-1"), "title": title_text(n),
                "sections": [], "articles": [],
            })
    for ch in chapters:
        node = byid[ch["anchor"]]
        for c in kids(node):
            cid = c.get("id") or ""
            if re.fullmatch(r"art_\d+", cid):
                articles.append(parse_article(c, ch, None))
            elif re.fullmatch(r"cpt_[IVX]+\.sct_\d+", cid):
                sec = {"anchor": cid, "number": int(cid.rsplit("_", 1)[1]),
                       "heading": heading_text(c, "oj-ti-section-1"), "title": title_text(c),
                       "chapter": ch["number"], "articles": []}
                sections.append(sec)
                ch["sections"].append(sec["number"])
                for a in kids(c):
                    if re.fullmatch(r"art_\d+", a.get("id") or ""):
                        articles.append(parse_article(a, ch, sec))
                        sec["articles"].append(articles[-1]["number"])
        ch["articles"] = [a["number"] for a in articles if a["chapter"] == ch["number"]]
    # footnotes: bodies are <p class="oj-note">(N) text</p>
    footnotes = []
    for n in root.iter():
        if "oj-note" in cls(n) and n.tag == "p":
            t = text(n)
            m = re.match(r"\((\d+)\)\s*(.*)$", t)
            footnotes.append({"number": int(m.group(1)), "text": m.group(2)})
    return chapters, sections, articles, recitals, footnotes, byid


def flatten(a):
    """Reconstruct an article's text from parsed records, in document order, for coverage check."""
    def pts(points):
        return "".join(p["label"] + p["text"] + pts(p["points"]) for p in points)
    return "".join((p["label"] + "." if p["label"] else "") + p["text"] + pts(p["points"]) + p["trailing"]
                   for p in a["paragraphs"])


def label_seq_ok(labels):
    """Contiguous (a)(b).. | (1)(2).. | (i)(ii)..  sequences."""
    if labels and all(l == "\u2014" for l in labels):  # unlabelled dash bullets
        return True
    vals = []
    for l in labels:
        core = l.strip("()")
        if core.isdigit():
            vals.append(int(core))
        elif core in ROMAN and not (len(core) == 1 and core in "vx" and False):
            vals.append(("r", ROMAN[core]))
        elif len(core) == 1 and core.isalpha():
            vals.append(("a", ord(core) - 96))
        else:
            return False
    if not vals:
        return True
    nums = [v if isinstance(v, int) else v[1] for v in vals]
    return nums == list(range(1, len(nums) + 1)) or (
        # lone 'i' following 'h' in an alphabetical list is a letter, not a roman numeral
        all(isinstance(v, tuple) for v in vals) and
        [ord(l.strip("()")) - 96 for l in labels] == list(range(1, len(labels) + 1)))


def validate(chapters, sections, articles, recitals, footnotes, byid):
    errs, warns = [], []
    chk = lambda cond, msg: None if cond else errs.append(msg)

    chk(len(articles) == EXPECTED["articles"], f"articles {len(articles)} != {EXPECTED['articles']}")
    chk(len(recitals) == EXPECTED["recitals"], f"recitals {len(recitals)} != {EXPECTED['recitals']}")
    chk(len(chapters) == EXPECTED["chapters"], f"chapters {len(chapters)} != {EXPECTED['chapters']}")
    chk(len(sections) == EXPECTED["sections"], f"sections {len(sections)} != {EXPECTED['sections']}")
    chk([c["number"] for c in chapters] == ROMAN_CHAPTERS, "chapter numerals not I..XI in order")
    chk([a["number"] for a in articles] == list(range(1, 100)), "article numbers not 1..99 contiguous/in order")
    chk([r["number"] for r in recitals] == list(range(1, 174)), "recital numbers not 1..173 contiguous/in order")
    chk([f["number"] for f in footnotes] == list(range(1, len(footnotes) + 1)), "footnotes not contiguous")

    for c in chapters:
        chk(bool(c["title"]) and (c["heading"] or "").startswith("CHAPTER"), f"chapter {c['number']} heading/title missing")
        chk(len(c["articles"]) > 0, f"chapter {c['number']} has no articles")
    for s in sections:
        chk(bool(s["title"]), f"section {s['anchor']} title missing")
    for r in recitals:
        chk(r["label"] == f"({r['number']})", f"recital {r['number']} label {r['label']!r}")
        chk(bool(r["text"]), f"recital {r['number']} empty")

    for a in articles:
        n = a["number"]
        chk(bool(a["title"]), f"article {n} no title")
        chk(len(a["paragraphs"]) > 0, f"article {n} no paragraphs")
        numbered = [p for p in a["paragraphs"] if p["ordinal"] is not None]
        if numbered:
            chk([p["ordinal"] for p in numbered] == list(range(1, len(numbered) + 1)), f"article {n} paragraph ordinals gap")
            chk([p["label"] for p in numbered] == [str(i) for i in range(1, len(numbered) + 1)],
                f"article {n} paragraph labels differ from anchors: {[p['label'] for p in numbered]}")
        for p in a["paragraphs"]:
            chk(bool(p["text"]) or bool(p["points"]), f"article {n} para {p['index']} empty")
            if p["_interleaved"]:
                warns.append(f"article {n} para {p['index']}: text interleaved between point lists")

            def check_points(points, where):
                chk(label_seq_ok([x["label"] for x in points]), f"{where}: point labels not contiguous {[x['label'] for x in points]}")
                for x in points:
                    chk(bool(x["text"]), f"{where} point {x['label']} empty")
                    check_points(x["points"], f"{where}{x['label']}")
            check_points(p["points"], f"article {n} para {p['index']}")
        # completeness: parsed text must equal source text minus headings/footnote markers
        node = byid[a["anchor"]]
        src = "".join(raw_text(c) for c in kids(node)
                      if not ("oj-ti-art" in cls(c) or "eli-title" in cls(c)))
        chk(squash(src) == squash(flatten(a)), f"article {n} text coverage mismatch")
        chk(a["chapter"] in ROMAN_CHAPTERS, f"article {n} no chapter")

    # chapter/section article ranges contiguous & non-overlapping
    covered = [x for c in chapters for x in c["articles"]]
    chk(covered == list(range(1, 100)), "chapters do not partition articles 1..99 in order")
    # hygiene: no NBSP / runs of whitespace / leftover markers in any text
    def all_text(a):
        for p in a["paragraphs"]:
            yield p["text"]; yield p["trailing"]
            stack = list(p["points"])
            while stack:
                x = stack.pop(); yield x["text"]; stack.extend(x["points"])
    for a in articles:
        for t in all_text(a):
            chk("\xa0" not in t and "  " not in t and t == t.strip(), f"article {a['number']} unclean whitespace")
    for r in recitals:
        chk("\xa0" not in r["text"] and "  " not in r["text"], f"recital {r['number']} unclean whitespace")
    # footnote refs resolve
    nums = {f["number"] for f in footnotes}
    for r in recitals:
        for ref in r["footnote_refs"]:
            chk(ref in nums, f"recital {r['number']} refs missing footnote {ref}")
    return errs, warns


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=RAW)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    data = args.raw.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    meta = json.loads((args.raw.parent / "metadata.json").read_text())
    expected_sha = meta["files"][0]["sha256"]
    if sha != expected_sha:
        sys.exit(f"raw file hash {sha} != metadata.json {expected_sha}")

    root = parse(data.decode("utf-8"))
    chapters, sections, articles, recitals, footnotes, byid = walk(root)
    errs, warns = validate(chapters, sections, articles, recitals, footnotes, byid)

    for a in articles:
        for p in a["paragraphs"]:
            p.pop("_interleaved")

    args.out.mkdir(parents=True, exist_ok=True)
    dump(args.out / "structure.json", {"chapters": chapters, "sections": sections})
    dump(args.out / "articles.json", articles)
    dump(args.out / "recitals.json", recitals)
    dump(args.out / "footnotes.json", footnotes)
    dump(args.out / "parse_report.json", {
        "source": {"file": args.raw.name, "sha256": sha, "url": meta["source_url"], "retrieved_at": meta["retrieved_at"]},
        "counts": {"chapters": len(chapters), "sections": len(sections), "articles": len(articles),
                   "recitals": len(recitals), "footnotes": len(footnotes),
                   "paragraphs": sum(len(a["paragraphs"]) for a in articles)},
        "ok": not errs, "errors": errs, "warnings": warns,
    })
    print(json.dumps({"ok": not errs, "errors": errs, "warnings": warns}, indent=2))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
