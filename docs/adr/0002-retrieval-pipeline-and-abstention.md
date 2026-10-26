# ADR 0002: Article-first retrieval with reranking and evidence-based abstention

- **Status:** Accepted
- **Date:** 2026-10-25
- **Builds on:** [ADR 0001](0001-retrieval-and-fine-tuning-roadmap.md). Baseline preserved at git tag `baseline-eval-v1`.

## Context

The baseline (bge-small-en-v1.5 vectors of the chunk text, exact cosine search, articles and recitals in one pool) found the right clause in the top 5 for only 71% of dev questions. Recitals took about 2.5 of the top 5 slots, because their plain explanatory wording matches lay questions better than the binding articles. Out-of-scope questions still returned GDPR provisions, and raw vector similarity could not tell them apart reliably.

For a compliance system the requirements are: cite the operative article, offer recitals only as interpretive context, cope with lay phrasing that differs from the regulation's vocabulary, and say "no basis" instead of returning an unrelated provision.

## Decision

```
question
  -> candidates: dense search (top 15) + BM25 on the glossary-expanded question (top 15), articles only
  -> cross-encoder rerank (mxbai-rerank-base-v1) against the ORIGINAL question
  -> evidence status from the reranker's top score: supported (>= 0.5), weak_evidence (0.2-0.5), no_basis (< 0.2)
  -> recital context for the top 3 articles, returned separately as role "interpretive_context"
```

- **Articles and recitals are separate pools.** Articles are the operative law and the only thing ranked as an answer. Recitals are selected afterwards for the top articles (score = 0.5 x similarity to the question + 0.5 x best similarity to one of those articles) and are labelled as context. They are never returned when the status is `no_basis`.
- **Query expansion only adds candidates.** A small, readable glossary (`ingestion/glossary.py`) maps lay wording to GDPR terms ("companies outside the EU" -> "controller or processor not established in the Union"). It feeds BM25 candidate generation only. The reranker scores against the original question, so expansion can add recall but cannot distort the final order.
- **Abstention is a three-level evidence status, not a single cut-off.** Thresholds were chosen on the dev set only.
- Implemented in `ingestion/pipeline.py`; `python -m ingestion.search_chunks "question"` uses it.

## Evidence

Dev set: 52 answerable questions the choices were made on. Held-out set: 40 answerable questions written afterwards in different phrasing, never used for tuning. **Rule: a component stays only if it helps on both sets.** Strict = the gold article/paragraph/point must match; article-level = the right article is enough.

| Config | Dev hit@1 | Dev hit@5 | Dev art@5 | Held hit@1 | Held hit@5 | Held art@5 |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline: dense, recitals in pool | 0.442 | 0.712 | 0.885 | 0.525 | 0.725 | 0.900 |
| Dense, articles only | 0.615 | 0.827 | 0.885 | 0.650 | 0.800 | 0.900 |
| + rerank (dense top 30) | 0.827 | 0.923 | 0.942 | 0.775 | 0.925 | 0.975 |
| **Chosen: + candidate union (dense + BM25 on expanded)** | **0.846** | **0.942** | **1.000** | **0.800** | **0.975** | **0.975** |

- Top-5 misses: dev 15 -> 3, held-out 11 -> 1. Recitals in the top 5 of the answer list: 2.5 on average -> 0 by construction.
- **The reranker is the main gain** (hit@1 +0.2). The candidate union mostly fixes recall for terminology gaps: for "companies based outside the EU" Article 3(2) ranked 108th by dense search and never reached the reranker; BM25 on the expanded question ranks it 1st. Excluding the Article 3(2) questions (the glossary rule was written after seeing them) the union adds about one question; treat its broader value as unproven.
- **Recital context:** a gold recital appears in the top 3 context recitals for 78% (dev) and 85% (held-out) of questions. The recital reference list is conservative and incomplete, so precision is a lower bound (about 0.3).

### Abstention (thresholds fixed on dev, applied unchanged to held-out)

| Held-out question type | n | supported | weak_evidence | no_basis |
| --- | --- | --- | --- | --- |
| Answerable | 40 | 80% | 12% | 8% |
| GDPR-related but the text does not answer it | 6 | 0% | 17% | 83% |
| Out of scope (other laws, unrelated) | 10 | 0% | 10% | 90% |

No non-answerable held-out question reached `supported`; on dev, 1 of 19 did (compensation cap, which Article 82 touches). A single strict threshold would wrongly refuse about 28% of legitimate held-out questions, hence the middle band.

**Why the reranker score and not vector similarity.** Ranking quality alone does not separate them (AUROC is 0.93-0.99 for the reranker score, the best candidate's dense similarity and its pool maximum alike). The difference is at the low end. With bands calibrated by the same recipe on dev (LOW = lowest dev answerable score, HIGH = its 8th percentile), the reranker puts 90% of held-out out-of-scope questions in `no_basis`; dense similarity puts only about 40% there and leaves the rest in `weak_evidence`, where provisions would still be shown. The price is that fewer legitimate held-out questions reach `supported` with the reranker (75-80%) than with dense similarity (88-90%). We accept that trade because showing GDPR provisions for an unrelated question is the worse failure for a compliance tool; revisit it if too many valid questions come back as weak.

### Display rules (measured 2026-10-26)

Rule fixed before looking at results: adopt only if, on both sets, it shows at least 25% fewer items, loses at most one question of coverage per set, and does not lower precision (`ingestion/display_experiments.py`, `evaluation/results/display_tweaks.json`).

- **Provisions: adopted.** Show only provisions whose reranker score is within 0.2 of the best (max 5, min 1). Items shown fall from 5.0 to 3.5 (dev) and 3.05 (held-out); precision rises from 0.52 to 0.69 and from 0.54 to 0.79; coverage is unchanged on dev and one question lower on held-out (0.975 -> 0.950). Tighter bands (0.1, 0.05, 0.02) lost two or more held-out questions.
- **Recitals: unchanged (top 3).** Showing 2 lost coverage on both sets (any-gold 0.78 -> 0.74 dev, 0.85 -> 0.79 held-out); relevance cut-offs either removed nothing (0.7) or lost coverage (0.75 and above). Recital context stays valuable but imprecise (about 0.3); showing fewer is a product decision, not something the numbers support.
- **The band does not fix score saturation.** Reranker scores for topically close clauses bunch near 1.0, so for "what rights does a data subject have to access their data" Articles 16 and 13(2) (0.97) still appear next to Article 15 (0.99).

### Rejected (each measured)

| Option | Result |
| --- | --- |
| Article title or header added to the embedded text (variants T, H) | Small gains on dense-only search (hit@5 0.83 -> 0.85-0.87) that disappear after reranking |
| Glossary expansion appended to the dense query | Dev +1 question, held-out hit@5 0.925 -> 0.875; fails the both-sets rule |
| BM25 + dense fused by RRF as the final ranker | hit@1 0.46-0.60 vs 0.615 dense alone; at low weights only ties |
| bge-reranker-base | Worse than no reranker (hit@1 0.46) |
| bge-reranker-v2-m3 | hit@5 0.94 but hit@1 only 0.67; mxbai better and 3x smaller |
| Small-to-big sibling expansion after the first rerank | +1 dev, -1 held-out |
| bge query instruction prefix | No gain (equal or slightly worse) |

## Limits and risks

- **The question sets are AI-drafted, small and share an author with the glossary.** One question is about 2 points. Differences under about 0.04 are noise. The held-out set limits overfitting but is not independent evidence of real-user performance.
- **Known failure: "legal bases / legal grounds for processing".** Article 6(1) (a long list chunk) is missing from the candidates for two of three phrasings; the answers come back as weak evidence rather than confidently wrong. Tracked in [docs/issues/0001](../issues/0001-article-6-1-missing-for-legal-bases-questions.md).
- When asked "when can I process data without consent", Article 9(2) points can outrank Article 6(1).
- **"GDPR-related but needs interpretation"** cannot be decided by retrieval; it belongs to the later answer-generation step, which must stay grounded in the returned provisions.
- Thresholds are specific to this reranker revision (pinned) and need recalibration if it changes. Reranker scores on the GPU differ from CPU by about 5e-4.
- Strict gold counts a sibling paragraph as a miss (for example 6(3) instead of 6(1)); article-level numbers are the fairer view for citing an article.

## Change log

- 2026-10-26: glossary bug fixed (the "inform..." rule matched "information"); no question outcome changed on dev or held-out. Provision display band added (see above).

## Reproduce

```
ingestion/.venv/bin/python -m ingestion.experiments release --heldout   # table above (HF_HUB_OFFLINE=1 once models are cached)
```
Results are stored in `evaluation/results/`; `baseline_A.json` is the untouched baseline.
