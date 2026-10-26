"""Parser: raw EUR-Lex HTML -> structured records. Uses the real raw file (no network)."""
import filecmp
import hashlib
import json

import pytest

from ingestion import parse_gdpr as P
from ingestion.htmltree import parse
from ingestion.tests.conftest import PARSED, ROOT


@pytest.fixture(scope="module")
def parsed():
    root = parse(P.RAW.read_text(encoding="utf-8"))
    chapters, sections, articles, recitals, footnotes, byid = P.walk(root)
    return {"chapters": chapters, "sections": sections, "articles": {a["number"]: a for a in articles},
            "recitals": {r["number"]: r for r in recitals}, "footnotes": footnotes,
            "all": (chapters, sections, articles, recitals, footnotes, byid)}


def test_raw_file_matches_recorded_hash():
    meta = json.loads((ROOT / "data/raw/gdpr/metadata.json").read_text())
    assert hashlib.sha256(P.RAW.read_bytes()).hexdigest() == meta["files"][0]["sha256"]


def test_expected_counts(parsed):
    assert len(parsed["articles"]) == 99
    assert len(parsed["recitals"]) == 173
    assert len(parsed["chapters"]) == 11
    assert len(parsed["sections"]) == 15
    assert len(parsed["footnotes"]) == 21


def test_builtin_validation_passes(parsed):
    errors, warnings = P.validate(*parsed["all"])
    assert errors == []
    assert warnings == []


def test_article_4_definitions_are_26_points_without_numbered_paragraphs(parsed):
    (para,) = parsed["articles"][4]["paragraphs"]
    assert para["label"] is None
    assert [p["label"] for p in para["points"]] == [f"({i})" for i in range(1, 27)]
    assert para["points"][0]["text"].startswith("‘personal data’ means")


def test_article_6_paragraph_1_keeps_points_and_trailing_text(parsed):
    p = parsed["articles"][6]["paragraphs"][0]
    assert p["label"] == "1" and p["anchor"] == "006.001"
    assert [x["label"] for x in p["points"]] == ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)"]
    assert p["trailing"].startswith("Point (f) of the first subparagraph shall not apply")


def test_unnumbered_paragraphs_and_dash_bullets(parsed):
    art67 = parsed["articles"][67]["paragraphs"]
    assert [p["label"] for p in art67] == [None, None]
    assert all(x["label"] == "—" for x in parsed["articles"][53]["paragraphs"][0]["points"])


def test_chapter_and_section_structure(parsed):
    art6 = parsed["articles"][6]
    assert (art6["chapter"], art6["chapter_title"], art6["section"]) == ("II", "Principles", None)
    art13 = parsed["articles"][13]
    assert (art13["chapter"], art13["section"]) == ("III", 2)
    assert [c["number"] for c in parsed["chapters"]] == ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


def test_recitals_are_tagged_and_footnote_markers_removed(parsed):
    r3 = parsed["recitals"][3]
    assert r3["type"] == "recital" and r3["anchor"] == "rct_3" and r3["label"] == "(3)"
    assert r3["footnote_refs"] == [4]
    assert not any("(4)" in t for t in [r3["text"]]) or r3["text"].count("(4)") == 0


def test_text_is_whitespace_normalised(parsed):
    for a in parsed["articles"].values():
        for p in a["paragraphs"]:
            for t in (p["text"], p["trailing"]):
                assert "\xa0" not in t and "  " not in t and t == t.strip()


def test_tolerant_tree_builder_handles_unclosed_meta():
    root = parse("<html><head><meta charset='x'><title>t</title></head><body><p>a<br>b</p></body></html>")
    assert [n.tag for n in root.iter() if n.tag in ("title", "p")] == ["title", "p"]


def test_output_is_deterministic_and_matches_committed_files(tmp_path):
    out1, out2 = tmp_path / "1", tmp_path / "2"
    assert P.main(["--out", str(out1)]) == 0
    assert P.main(["--out", str(out2)]) == 0
    for name in ("articles.json", "recitals.json", "structure.json", "footnotes.json", "parse_report.json"):
        assert filecmp.cmp(out1 / name, out2 / name, shallow=False), f"{name} differs between runs"
        assert filecmp.cmp(out1 / name, PARSED / name, shallow=False), f"{name} is stale: re-run the parser"
