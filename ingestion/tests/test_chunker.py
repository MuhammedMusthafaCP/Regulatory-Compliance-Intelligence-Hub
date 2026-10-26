"""Chunker: parsed records -> retrieval chunks with citations."""
import filecmp
import json

import pytest

from ingestion import chunk_gdpr as C
from ingestion.tests.conftest import PARSED


def run_chunker(directory, max_words=None):
    argv = ["--dir", str(directory)] + (["--max-words", str(max_words)] if max_words else [])
    assert C.main(argv) == 0
    chunks = json.loads((directory / "chunks.json").read_text())
    report = json.loads((directory / "chunk_report.json").read_text())
    return chunks, report


@pytest.fixture
def chunks350(parsed_copy):
    return run_chunker(parsed_copy)


def test_default_run_validates_and_covers_everything(chunks350):
    chunks, report = chunks350
    assert report["ok"] and report["errors"] == [] and report["warnings"] == []
    assert report["counts"]["chunks"] == 670 == len(chunks)
    assert report["counts"]["articles_covered"] == 99 and report["counts"]["recitals_covered"] == 173
    assert report["cross_refs"]["unresolved"] == 0


def test_smaller_limit_splits_more_paragraphs(parsed_copy):
    chunks, report = run_chunker(parsed_copy, max_words=200)
    assert len(chunks) == 739 and report["ok"]


def test_ids_and_citations_are_unique(chunks350):
    chunks, _ = chunks350
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)
    keyed = [(c["citation"], c["split_reason"] == "trailing") for c in chunks]
    assert len(set(keyed)) == len(keyed)


def test_article_6_1_stays_whole_with_its_caveat(chunks350):
    chunks, _ = chunks350
    (c,) = [c for c in chunks if c["chunk_id"] == "gdpr:art6:p1"]
    assert c["citation"] == "Article 6(1)" and c["split_reason"] == "paragraph"
    assert "(f) processing is necessary for the purposes of the legitimate interests" in c["text"]
    assert "Point (f) of the first subparagraph shall not apply" in c["text"]
    assert c["source_anchor"] == "006.001" and c["source_url"].endswith("#006.001")


def test_long_paragraph_splits_by_point_with_lead_in(chunks350):
    chunks, _ = chunks350
    pts = [c for c in chunks if c["chunk_id"].startswith("gdpr:art9:p2:")]
    assert len(pts) == 10
    assert pts[0]["citation"] == "Article 9(2)(a)" and pts[0]["split_reason"] == "point"
    assert pts[0]["text"].startswith("Paragraph 1 shall not apply if one of the following applies:")
    assert pts[0]["lead_in"].startswith("Paragraph 1 shall not apply")


def test_article_4_has_one_chunk_per_definition_without_lead_in(chunks350):
    chunks, _ = chunks350
    defs = [c for c in chunks if c.get("article_number") == 4]
    assert [c["citation"] for c in defs] == [f"Article 4({i})" for i in range(1, 27)]
    assert all(c["split_reason"] == "definition" and "For the purposes of this Regulation" not in c["text"] for c in defs)


def test_unnumbered_paragraph_citation(chunks350):
    chunks, _ = chunks350
    assert "Article 67, second paragraph" in {c["citation"] for c in chunks}


def test_recitals_are_one_chunk_each_and_tagged(chunks350):
    chunks, _ = chunks350
    rec = [c for c in chunks if c["type"] == "recital"]
    assert len(rec) == 173
    assert all(c["split_reason"] == "recital" and c["citation"] == f"Recital {c['recital_number']}" for c in rec)
    assert not any("article_number" in c for c in rec)


def test_output_is_deterministic_and_matches_committed_chunks(parsed_copy, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    for n in ("articles.json", "recitals.json", "parse_report.json"):
        (other / n).write_bytes((parsed_copy / n).read_bytes())
    run_chunker(parsed_copy)
    run_chunker(other)
    assert filecmp.cmp(parsed_copy / "chunks.json", other / "chunks.json", shallow=False)
    assert filecmp.cmp(parsed_copy / "chunks.json", PARSED / "chunks.json", shallow=False), "committed chunks.json is stale"


@pytest.mark.parametrize("text,expected", [
    ("pursuant to Article 6(1)(a)", [(6, "1", "(a)")]),
    ("Articles 13 and 14", [(13, None, None), (14, None, None)]),
    ("Articles 12 to 22", [(n, None, None) for n in range(12, 23)]),
    ("referred to in Article 93(2).", [(93, "2", None)]),
    ("Article 16(2) TFEU mandates", []),
    ("Article 8(1) of the Charter of Fundamental Rights", []),
    ("decisions adopted on the basis of Article 25(6) or Article 26(4) of Directive 95/46/EC", []),
    ("Article 3 of this Regulation", [(3, None, None)]),
])
def test_cross_reference_extraction(text, expected):
    refs, _ = C.extract_refs(text)
    assert [(r["article"], r["paragraph"], r["point"]) for r in refs] == expected
