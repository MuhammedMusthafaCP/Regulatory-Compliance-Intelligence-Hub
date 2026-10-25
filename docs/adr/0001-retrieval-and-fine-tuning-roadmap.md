# ADR 0001: Retrieval-first roadmap with embedding fine-tuning

- **Status:** Accepted (Steps 1-2 done; Step 4 evaluation set is being built before Step 3, see Progress notes)
- **Date:** 2026-10-24
- **Builds on:** Phase 1 foundation ([BRD](../../requirement-docs/brd-1.md))

## Context

Phase 1 delivered the foundation: Next.js dashboard, FastAPI backend, and Neon PostgreSQL with pgvector, plus one health-check diagnostic. There are no documents, embeddings or search yet.

The project's idea (from the BRD): compliance answers must be **grounded in official regulatory text and auditable** (every claim cites a specific article or clause), not generated from a model's memory.

The owner's main purpose for the next phase is **learning**: how chunking, embeddings, indexing and vector search actually work, plus fine-tuning a model for the regulatory domain. Constraints: use free Hugging Face models, keep to zero-cost infrastructure (BRD NFR-3.1), and stay on the existing stack.

## Decision

Build **retrieval first, LLM last**, in measurable steps. Fine-tune the **embedding model** (not the generator LLM) and only after a baseline and an evaluation set exist.

Reasoning:
- Accuracy and citations come from retrieval. Fine-tuning a generator on legal text mostly changes style and can increase hallucination if relied on for facts.
- Fine-tuning is only justified if it can be measured, so the evaluation set comes before it.
- Search mechanics (chunking, indexes, metrics) are the learning goal, and they are visible without an LLM in the loop.

## Roadmap

Each step ends with something you can run and inspect. Tick the box when done.

- [x] **Step 1: Ingest and chunk.** Get the GDPR text (EUR-Lex), parse it by article/clause, chunk it, and keep metadata for citations (regulation, article, page, URL). Add `documents` and `chunks` tables via Alembic. *(Done: 670 chunks, 350-word limit.)*
- [x] **Step 2: Embed and store.** Embed chunks with a free baseline model (e.g. `BAAI/bge-small-en-v1.5` or `all-MiniLM-L6-v2`). Replace the `vector(3)` assumption with the model's real dimension for the new table. Store the model name and version with each vector. *(Done: `bge-small-en-v1.5`, pinned revision, separate `chunk_embeddings` table.)*
- [ ] **Step 3: Search and index.** Exact (brute-force) search first and inspect results by hand. Then add an HNSW index (and compare IVFFlat). Compare cosine, L2 and inner product. Use `EXPLAIN ANALYZE` to confirm index use. Expose a simple search page showing retrieved clauses and scores.
- [x] **Step 4: Evaluate the baseline.** Build a small question set (50–200) with known correct clauses. Measure recall@k and MRR. Measure ANN recall against exact search, and latency against recall.
- [ ] **Step 5: Fine-tune the embedding model.** Generate synthetic question-chunk pairs with a free LLM, review a sample by hand, then fine-tune on a free Colab/Kaggle GPU.
- [ ] **Step 6: Re-evaluate and decide.** Re-run the same evaluation. Keep the fine-tuned model only if the numbers improve. Re-embed all chunks if the model changes.
- [ ] **Later:** hybrid search (vector + Postgres full-text, rank fusion), reranker (cross-encoder), LLM answers with verified citations and refusal when sources are weak, policy gap analysis, PDF/CSV export, authentication and roles.

## Progress notes

- **2026-10-25: order changed.** The evaluation set (Step 4) is built before Step 3, because comparing distance metrics and index types needs a scoreboard. Step 3 is judged with it.
- **Chunking decision:** paragraph-level chunks, split into points only above 350 words (200 was tested; it split Article 6(1) and 9 other paragraphs that read better whole). Article 4 is one chunk per definition. The limit fits `bge-small` (512 tokens) but not `all-MiniLM-L6-v2` (256).
- **Embedding decision:** variant A (chunk text only) is the baseline. Variant C (regulation/chapter/article-title header + text) is the first experiment, to be judged by the evaluation. Vectors live in `chunk_embeddings` so variants and the later fine-tuned model sit side by side.
- **Observation to test, not a conclusion:** in a 5-question smoke test, recitals outranked the binding articles (e.g. Recitals 43/42/69 before Article 6(1)). The evaluation should measure this with and without recitals.
- **2026-10-25: Step 4 baseline measured; retrieval redesigned.** Baseline kept at tag `baseline-eval-v1`. The evidence-driven pipeline (article-first, reranker, evidence-status abstention) is recorded in [ADR 0002](0002-retrieval-pipeline-and-abstention.md). Step 3 (distance metrics and ANN indexes) is still open; at 670 rows it is for learning, not for quality.
- **Known limits:** Recital 143 exceeds 512 tokens and is truncated when embedded; six long paragraphs (Art. 9(2), 28(3), 47(2), 49(1), 57(1), 70(1)) are still split into point chunks; the text is the original 2016 Official Journal version without later corrigenda.

## What each step teaches

| Step | Concepts |
| --- | --- |
| 1 | Parsing, chunking strategies, metadata for citations |
| 2 | What embeddings are, model choice, dimensions, versioning |
| 3 | Distance metrics, exact vs approximate search, HNSW/IVFFlat parameters |
| 4 | Evaluation: recall@k, MRR, recall vs latency |
| 5 | Synthetic training data, contrastive fine-tuning of embeddings |
| 6 | Measuring improvement, re-embedding costs |

## Constraints and risks

- **Neon free tier:** limited storage (~0.5 GB) and compute hours. Index size and build time matter as the corpus grows. Keep the connection pool small.
- **Compute:** embedding fine-tuning is feasible on free GPUs. Generator-LLM fine-tuning (LoRA/QLoRA) is optional and tight on free hardware.
- **Data:** no ready-made GDPR question-clause dataset is assumed. Training pairs are synthetic and need manual review. Check the license of every dataset and model used.
- **Re-embedding:** changing the embedding model invalidates stored vectors, so keep the model name/version on each row.
- **Prompt injection (later, LLM phase):** retrieved document text is untrusted input to the LLM.

## Alternatives considered

- **Fine-tune the generator LLM first:** rejected for now. It adds cost and mostly changes style, and it moves facts away from retrieval.
- **Skip fine-tuning and use an off-the-shelf model only:** viable fallback. The evaluation in Step 4 shows whether fine-tuning is worth it.
- **Compare a dedicated vector DB (e.g. Qdrant, Chroma) with pgvector:** optional, after the pgvector baseline exists.

## Open questions

- Local embedding models only, or is a hosted API acceptable? (Default: local, to match the zero-cost goal.)
- Should the first release after Step 3 stay retrieval-only, or include LLM answers (the "Later" item)?
- Is this a learning project only, or might real users use it? This decides when authentication and roles are needed.
- First dataset: full GDPR text, or a smaller subset?
