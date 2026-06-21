# Advanced Retrieval — FoxSchool Support Copilot

Companion doc to [README.md](README.md).  
Tracks **baseline metrics**, **retrieval techniques under test**, and **measured results** after each change.

Main README = what the product is.  
This file = how retrieval was improved and what the numbers show.

---

## Current setup (baseline)

Before Phase F, the copilot uses **dense vector search only**.

```
User question
    → retrieve()          Chroma + MiniLM embeddings, top-5
    → build_context()
    → generate_answer()   GPT-4.1-mini
    → answer + sources
```

| Parameter | Value |
|-----------|-------|
| Index | Chroma (`chroma_db/`) |
| Embeddings | `all-MiniLM-L6-v2` |
| Retrieval | Dense (semantic similarity) |
| Top-k | 5 |
| Chunk size / overlap | 600 / 100 |
| Knowledge base | 15 markdown files |

Implementation: `app/rag.py` (`retrieve`), `ingest.py` (chunking).

---

## Baseline results (Phase E)

Measured with golden evals, LLM judge, Ragas, and (after F0) retrieval-only metrics.

### End-to-end quality

| Check | Tool | Result |
|-------|------|--------|
| Golden set | `evals/run_evals.py` | **25/25 (100%)** |
| Groundedness | `evals/model_graded.py` | **19/20 (95%)** |

### RAG metrics (Ragas, 11 in-scope questions)

| Metric | Score | What it means |
|--------|-------|---------------|
| Faithfulness | **1.00** | Answers stay grounded in retrieved text |
| Answer relevancy | **0.91** | Answers match the question |
| Context precision | **0.88** | Top-5 chunks are mostly relevant |
| **Context recall** | **0.64** | Retrieved context often misses information needed for a full answer |

### Retrieval-only metrics

Measured with `evals/retrieval_comparison.py` on 20 in-scope golden questions (`expected_sources_contain`).

| Metric | Dense baseline | Description |
|--------|----------------|-------------|
| Hit@5 | **100% (20/20)** | Expected KB file appears in top-5 for every question |
| MRR | **0.648** | Correct file ranks ~1st–2nd on average (1.0 = always first) |

### Diagnosis

Generation is not the bottleneck: **faithfulness is 1.0** and keyword evals pass.

**File-level retrieval is already strong** — Hit@5 is 100%. The expected article is almost always in top-5.

**Context recall (0.64) is lower** — Ragas checks whether the **text inside** retrieved chunks is enough for a full answer. So the gap is likely:

- wrong **chunk** within the right file (600-char splits),
- or the answer needs **more than one chunk**, while only part of it ranks high.

**MRR 0.648** confirms ranking noise: the correct file is often 2nd or 3rd, not 1st — hybrid should mainly improve **MRR** and chunk order.

Dense search handles paraphrases well; hybrid (BM25 + dense) adds exact-term matching (`$20`, `7-day`) and should push the best chunk higher via RRF.

---

## Techniques under test

Each technique below is applied **one at a time**. After each change we re-run retrieval metrics and Ragas, then record results in [Results](#results).

---

### 1. Retrieval benchmark (`retrieval_comparison.py`)

**What:** Script that evaluates retrieval **without calling the LLM** — only whether the expected source file appears in top-k.

**Metrics:** Hit@5, MRR.

**Why:** Fast baseline before/after comparison; cheaper than full Ragas runs.

**Status:** Done — baseline recorded (Hit@5 100%, MRR 0.648)

---

### 2. Hybrid search (BM25 + dense)

**What:** Combine two search methods and merge rankings:

| Method | Strength |
|--------|----------|
| **Dense (Chroma)** | Semantic similarity — "cancel subscription" finds cancellation policy |
| **BM25 (sparse)** | Keyword overlap — `$20`, `7-day`, plan names |

**Merge:** Reciprocal Rank Fusion (RRF) — combine rank positions from both lists, take top-5.

**Expected effect:** Higher **MRR** (correct file/chunk ranked first). May also lift context recall if better chunks surface.

**Implementation:** `retrieve_hybrid()` in `app/rag.py`, BM25 over Chroma chunks + RRF merge. Toggle via `RETRIEVAL_MODE=hybrid` in `.env`.

**Status:** Tested — retrieval benchmark recorded; Ragas pending

---

### 3. Cross-encoder reranking (optional)

**What:** Retrieve top-20 candidates with hybrid search, then re-score each (question, chunk) pair with a cross-encoder model (`ms-marco-MiniLM-L-6-v2`), keep top-5.

**Why:** First-stage retrieval is fast but approximate; reranking is slower but more accurate on a short list.

**Expected effect:** Context **precision** improves — fewer irrelevant chunks in the prompt.

**Trade-off:** Extra latency on each request.

**Status:** Optional — after hybrid if recall is still below target

---

### Techniques not in scope (this phase)

| Technique | Reason skipped |
|-----------|----------------|
| Query expansion | Support KB wording is fairly stable; hybrid covers most gaps |
| Sentence-window retrieval | KB articles are short; chunk overlap already 100 chars |
| Chunk size A/B (500 vs 1000) | Possible follow-up if recall still low after hybrid |

---

## Results

Summary of measured impact. Update this section after each technique is deployed.

### Comparison table

| Configuration | Hit@5 | MRR | Context recall | Context precision | Faithfulness | Golden evals |
|---------------|-------|-----|----------------|-------------------|--------------|--------------|
| **Dense only (baseline)** | **100%** | **0.648** | **0.64** | **0.88** | **1.00** | 25/25 |
| + Hybrid (BM25 + dense) | **95%** | **0.612** | **0.64** | **0.82** | **1.00** | **24/25** |
| Dense Ragas re-run *(sanity)* | 100% | 0.648 | 0.55 | 0.91 | 1.00 | 25/25 *(with dense)* |
| + Rerank | — | — | — | — | — | — |

**Target:** context recall ≥ **0.75** without breaking faithfulness or golden eval pass rate.

---

### Dense only (baseline)

**Configuration:** Chroma dense search, top-5, chunks 600/100.

**Ragas (11 cases):**

| Metric | Score |
|--------|-------|
| Faithfulness | 1.00 |
| Answer relevancy | 0.91 |
| Context precision | 0.88 |
| Context recall | 0.64 |

**Retrieval:** Hit@5 **100% (20/20)** · MRR **0.648**

**Notes:** Hit@5 already at ceiling — next gains should show in **MRR** and Ragas **context recall**, not file hit rate. LLM and prompts unchanged since Phase E.

---

### + Hybrid (BM25 + dense)

**Configuration:** BM25 (`rank_bm25`) + Chroma dense → RRF merge (k=60) → top-5. `CANDIDATE_K=20` before merge. Toggle: `RETRIEVAL_MODE=hybrid` in `.env`.

**Retrieval benchmark (20 golden questions):**

| Metric | Dense (before) | Hybrid (after) | Δ |
|--------|----------------|----------------|---|
| Hit@5 | 100% (20/20) | **95% (19/20)** | **−5%** |
| MRR | 0.648 | **0.612** | **−0.036** |

**Regression on q11:** *"What is the support email address?"* — dense finds `welcome.md`; hybrid returns create-account + troubleshooting chunks instead.

**Ragas (11 cases, `RETRIEVAL_MODE=hybrid`):**

| Metric | Dense baseline | Hybrid | Δ |
|--------|----------------|--------|---|
| Context recall | 0.64 | **0.64** | ~0 |
| Context precision | 0.88 | **0.82** | −0.06 |
| Answer relevancy | 0.91 | **0.90** | −0.01 |
| Faithfulness | 1.00 | **1.00** | 0 |

**Per-case context recall = 0:** q03 (Advanced plan), q04 (refund policy), q05 (mentor cost), q09 (cancel subscription).

**Golden evals:** **24/25** — q11 fails (`source missing: welcome`) under hybrid.

**Decision:** **Do not deploy hybrid.** Revert `.env` to `RETRIEVAL_MODE=dense`. Hybrid did not improve context recall, lowered precision, and broke q11.

**Notes:** On file-level metrics, hybrid did not beat dense. Ragas confirms no recall gain. Negative experiment — documented with numbers. Next lever for recall gaps on q03/q04/q05/q09: **chunking** or **rerank**, not BM25 hybrid.

---

### Hybrid regression case (q11)

| | Dense | Hybrid |
|---|-------|--------|
| **Question** | What is the support email address? | same |
| **Expected source** | `welcome.md` | same |
| **Top sources** | welcome in top-5 ✓ | create-account, login-problems, video-playback ✗ |
| **What went wrong** | — | BM25 matched generic “support” / account tokens in wrong articles |
| **Decision** | **Use dense** for production | Hybrid not deployed |

---

### + Rerank

**Configuration:** —

**Ragas (11 cases):**

| Metric | Before | After | Δ |
|--------|--------|-------|---|
| Context recall | — | — | — |
| Context precision | — | — | — |

**Retrieval:** Hit@5 — → — · MRR — → —

**Notes:** —

---

## Retrieval pitfall (case study)

See **Hybrid regression case (q11)** above — example where hybrid hurt retrieval vs dense.

---

## How to reproduce

```bash
# Index (once)
python ingest.py

# Retrieval-only benchmark
python evals/retrieval_comparison.py

# Full RAG metrics (slow, uses OpenAI)
python evals/ragas_eval.py

# Regression checks
python evals/run_evals.py
python redteam/run_csv_attacks.py
```

After any retrieval change: re-run benchmark + Ragas subset, update [Results](#results), then red team.

---

## Architecture evolution

**Today (baseline):**

```
question → dense retrieve (top-5) → LLM
```

**After hybrid:**

```
question → BM25 + dense → RRF merge (top-5) → LLM
```

**After rerank (optional):**

```
question → hybrid (top-20) → cross-encoder rerank (top-5) → LLM
```

---

*Last updated: Hybrid tested end-to-end — not deployed; dense remains production mode.*
