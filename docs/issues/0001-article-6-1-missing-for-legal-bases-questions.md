# Issue 0001: Article 6(1) is missing from the candidates for "legal grounds / legal bases" questions

- **Status:** Open
- **Found:** 2026-10-25 (dev q12, held-out h02), diagnosed 2026-10-26
- **Severity:** High for the product, because the lawful bases for processing are the most-asked GDPR question; mitigated because the failure is flagged, not confidently wrong
- **Tracked by:** `test_legal_bases_question_finds_article_6` in `ingestion/tests/test_integration.py` (strict `xfail`: it will start failing the suite, loudly, the day this is fixed so the marker can be removed)

## Symptom

For "On what legal grounds can an organisation process personal data?" and "What are the legal bases a business can rely on to use personal information?" the Article 6(1) chunk never reaches the reranker, so it cannot be returned.

| Question | Result today |
| --- | --- |
| q12 "legal grounds" | Article 6(3) comes first (0.96); Article 6(1) absent. Article-level hit, strict miss |
| h02 "legal bases ... personal information" | Article 88(1) first at 0.36, status `weak_evidence`; Article 6 absent. **True miss, but flagged as weak** |
| q13 "process ... without their consent" | Article 6(1) ranked 1st. Works |
| "What makes the processing of personal data lawful?" | Article 6(1) ranked 1st (0.996). Works |

So the clause is found when the question uses the regulation's words ("lawful") or the consent angle, and lost when it says "legal grounds/bases".

## Evidence (rank of the Article 6(1) chunk among articles in each first-stage source)

| | dense A | dense T | dense H | dense on glossary-expanded | BM25 on expanded | BM25 plain |
| --- | --- | --- | --- | --- | --- | --- |
| q12 | 30 | 38 | 39 | 12 | 17 | 49 |
| h02 | 96 | 106 | 89 | 39 | 34 | 120 |
| q13 (works) | 3 | 3 | 3 | 2 | 15 | 19 |

The chosen pipeline draws 15 candidates each from dense search on the plain question and BM25 on the expanded question. q12 narrowly misses (dense 30, BM25-expanded 17 against a cut of 15); h02 misses by a wider margin (96 and 34). "Dense on expanded" is shown for diagnosis only; it is not a candidate source.

## Likely causes (not yet all confirmed)

1. **The chunk is a long list.** Article 6(1) is 214 words: six lettered bases plus a caveat. Its embedding and BM25 score are diluted across consent, contract, vital interests, public task and legitimate interests, so no single question phrase matches strongly.
2. **Vocabulary gap.** The text says "processing shall be lawful only if at least one of the following applies"; users say "legal bases/grounds". "Lawfulness of processing" is in the article title, which BM25 uses but the embedding does not.
3. **Sibling pull.** Article 6(3) ("The basis for the processing ... shall be laid down by Union or Member State law") matches "basis" better than the list in 6(1).

## Already tried (do not repeat blindly)

| Attempt | Outcome |
| --- | --- |
| Title or header in the embedded text (variants T, H) | Rank got worse for Article 6(1) (38/39, 106/89) |
| Glossary rule "legal basis/grounds -> lawfulness of processing" | Exists; improves ranks (q12 30 -> 12, h02 96 -> 39) but not enough |
| Glossary bug found and fixed (2026-10-26): the "inform..." rule matched "information", adding "information to be provided" noise for "personal information" | Fix is correct and neutral (no question outcome changed on dev or held-out); h02 BM25-expanded rank improved 60 -> 34 but is still outside the cut |
| Larger candidate pool (k = 25 per source) | No gain on dev, one question worse on held-out |
| Small-to-big sibling expansion of the top 2-3 articles | Net zero (+1 dev, -1 held-out); Article 6 was not in the top articles for h02 |
| Splitting Article 6(1) into per-point chunks (200-word limit run) | Baseline-era result: still missed for q12 |

## Acceptance criteria

1. Article 6 appears in the top 5 for q12, h02, q13 and the "lawful" phrasing, strictly at 6(1) for at least three of the four.
2. `test_legal_bases_question_finds_article_6` passes and its `xfail` marker is removed.
3. No regression under the project rule: the change must not lower hit@5 by more than one question on either the dev or the held-out set (`python -m ingestion.experiments release --heldout`).

## Ideas to evaluate next

- **Fine-tune the embedding model** (ADR 0001 Step 5) with question-clause pairs that include "legal basis/grounds" phrasings for Article 6; the principled fix because it removes the vocabulary gap instead of patching it.
- **Add an article-level retrieval unit** (title + a short list of what the article covers) so queries can match "Lawfulness of processing" directly and then expand to its paragraphs.
- **Per-source candidate budget by article**: guarantee each article that appears in the top N of any source contributes its best chunk.
- Note that h02 can no longer be treated as a clean held-out question for the glossary after the bug fix; add new unseen phrasings of this question to the held-out set before judging a fix.

## Pointers

`ingestion/pipeline.py` (final config), `ingestion/glossary.py`, `ingestion/retrieval.py` (`_union`), `evaluation/gdpr_questions.json` (q12, q13), `evaluation/gdpr_questions_heldout.json` (h02), [ADR 0002](../adr/0002-retrieval-pipeline-and-abstention.md).
