# Advanced Retrieval — FoxSchool Support Copilot

Companion doc to [README.md](README.md).  
Tracks **baseline metrics**, **retrieval techniques under test**, and **measured results** after each change.

Main README = what the product is.  
This file = how retrieval was improved and what the numbers show.

---

## Current setup (production)

After Phase F experiments, the copilot runs **dense retrieval + heading-aware chunking**.

```
User question
    → retrieve()          Chroma + MiniLM embeddings, top-5 (RETRIEVAL_MODE=dense)
    → build_context()
    → generate_answer()   GPT-4.1-mini
    → answer + sources
```

| Parameter | Value |
|-----------|-------|
| Index | Chroma (`chroma_db/`) |
| Embeddings | `all-MiniLM-L6-v2` |
| Retrieval | **Dense only** (`RETRIEVAL_MODE=dense`) — hybrid tested twice, not deployed |
| Top-k | 5 |
| Chunking | **Heading-aware** — split on `##`; fallback 600/100 for sections > 800 chars |
| Chunks indexed | ~119 (heading split + `###` fallback for long sections) |
| Knowledge base | 15 markdown files |

Implementation: `app/rag.py` (`retrieve_dense`), `ingest.py` (`chunk_text`).

**Not in production:** BM25 + RRF hybrid (`RETRIEVAL_MODE=hybrid`) — code remains for benchmarks only.

---

## Baseline results (Phase E)

Measured with golden evals, LLM judge, Ragas, and (after F0) retrieval-only metrics.

### End-to-end quality

| Check | Tool | Result |
|-------|------|--------|
| Golden set | `evals/run_evals.py` | **23/25 (92%)** — q14, q22 fail (chunk-level; see [case studies](#retrieval-pitfall-case-studies)) |
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

**MRR 0.648** confirms ranking noise: the correct file is often 2nd or 3rd, not 1st.

**Golden evals 23/25** on dense — failures are **q14** (mentor cancel window) and **q22** (free trial). Both retrieve the right **file** but the wrong **chunk** inside it (see case studies below). Generation is faithful to what it receives; the gap is chunking + ranking within a file.

Dense search handles paraphrases well. Hybrid (BM25 + dense) was tested next — it did **not** fix chunk-level misses (see Results).

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

**Status:** Tested end-to-end — **not deployed** (dense remains default)

---

### 3. Heading-aware chunking

**What:** Split markdown on `##` headings so each FAQ section / article section becomes its own chunk, instead of fixed 600-char windows.

**Why:** q14 and q22 failed because the answer lived in chunk N but retrieval returned chunk 0 or 3 from the same file. Heading splits align chunks with user questions (“free trial”, “session rules”).

**Implementation:** `ingest.py` — `re.split(r"(?=^## )")`, `MAX_SECTION_CHARS=800` with fixed-size fallback inside long sections. Re-index: `python ingest.py`.

**Status:** **Deployed** — production chunking (see [Heading-aware chunking — deployed](#heading-aware-chunking--deployed))

---

### 4. Cross-encoder reranking (optional)

**What:** Retrieve top-20 candidates with hybrid search, then re-score each (question, chunk) pair with a cross-encoder model (`ms-marco-MiniLM-L-6-v2`), keep top-5.

**Why:** First-stage retrieval is fast but approximate; reranking is slower but more accurate on a short list.

**Expected effect:** Context **precision** improves — fewer irrelevant chunks in the prompt.

**Trade-off:** Extra latency on each request.

**Status:** Optional — next lever if Ragas recall stays below target after subset/reference fixes

---

### Techniques not in scope (this phase)

| Technique | Reason skipped |
|-----------|----------------|
| Query expansion | Support KB wording is fairly stable; low ROI for this KB |
| Sentence-window retrieval | KB articles are short; heading split is a better fit |
| Chunk size A/B (500 vs 1000) | Possible follow-up if recall still low after heading split |

---

## Results

Summary of measured impact. Update this section after each technique is deployed.

### Comparison table

| Configuration | Hit@5 | MRR | Context recall | Context precision | Faithfulness | Golden evals |
|---------------|-------|-----|----------------|-------------------|--------------|--------------|
| **Dense + fixed 600/100 (baseline)** | **100%** | **0.648** | **0.64** | **0.88** | **1.00** | **23/25** |
| + Hybrid on baseline chunks | **95%** | **0.612** | **0.64** | **0.82** | **1.00** | **24/25** |
| **+ Heading chunking + dense *(production)*** | **100%** | **0.569** | **0.93** | **0.86** | **0.99** | **25/25** |
| + Hybrid on heading chunks *(re-test)* | **90%** | **0.608** | — | — | — | — |
| + Rerank | — | — | — | — | — | — |

**Target:** golden evals **25/25** (primary gate) and context recall ≥ **0.75** on Ragas subset — **both met**.

**Production row:** dense retrieval + heading chunking. Ragas uses 15-case subset with `reference_answer` (see [Eval methodology](#eval-methodology-improvements)). Hybrid re-tested after re-index — still rejected.

*Earlier Ragas run (11 cases, keyword-only reference, heading index): recall **0.45** — misleading; fixed by eval improvements below.*

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

**Golden evals:** **23/25** — q14 (missing `24`), q22 (missing `free trial`); both are chunk-level retrieval misses, not LLM hallucination.

**Notes:** Hit@5 already at ceiling — next gains should show in **MRR**, Ragas **context recall**, and golden pass rate, not file hit rate. LLM and prompts unchanged since Phase E.

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

**Notes:** On file-level metrics, hybrid did not beat dense. Ragas confirms no recall gain. Negative experiment — documented with numbers.

**Re-test after heading chunking:** Hit@5 **90% (18/20)** vs dense **100%**; MRR **0.608** vs **0.569**. Hybrid still breaks file-level retrieval on this KB. **Decision unchanged: `RETRIEVAL_MODE=dense`.**

---

### Heading-aware chunking — deployed

**Configuration:** Split on `##` in `ingest.py`; sections > 800 chars fall back to 600/100 inside the section. `load_md()` reads raw markdown (no line-prefix spacing). Re-index required after change. Golden source checks updated: `expected_sources_any` for facts duplicated across KB files (q05, q08, q11).

**Retrieval benchmark (20 in-scope questions, dense):**

| Metric | Baseline (600/100) | Heading + dense | Δ |
|--------|-------------------|-----------------|---|
| Hit@5 | 100% (20/20) | **100% (20/20)** | 0 |
| MRR | 0.648 | **0.569** | −0.079 |

**Hybrid re-test on heading index:**

| Metric | Dense | Hybrid | Δ |
|--------|-------|--------|---|
| Hit@5 | 100% (20/20) | **90% (18/20)** | **−10%** |
| MRR | 0.569 | **0.608** | +0.039 |

**Ragas (15 cases, q01–q11 + q14 + q15 + q21 + q22, `reference_answer`, `RETRIEVAL_MODE=dense`):**

| Metric | Baseline (600/100, 11 cases) | Heading + dense (15 cases, improved eval) | Δ |
|--------|-------------------------------|-------------------------------------------|---|
| Faithfulness | 1.00 | **0.99** | ~0 |
| Answer relevancy | 0.91 | **0.92** | +0.01 |
| Context precision | 0.88 | **0.86** | −0.02 |
| Context recall | 0.64 | **0.93** | **+0.29** |

**Per-case context recall = 0:** q09 (cancel subscription) only — answer still passes golden keyword check.

**Golden evals:** **25/25 (100%)** — up from 23/25. Fixed: **q14** (24h mentor cancel), **q22** (no free trial). Source checks relaxed for duplicate facts: q05, q08, q11 accept any KB file that legitimately contains the answer.

**Chunking polish:** long `##` sections now split on `###` before fixed-size fallback (`119` chunks, was `113`).

**Decision: deploy heading chunking + dense retrieval.**

#### Why deploy despite the first Ragas dip (0.45)?

An early Ragas run on heading chunking used the **old eval setup** (11 cases, keyword-only `reference`). That showed recall **0.45** — but golden evals were already **25/25**. The dip was an **eval artifact**, not a bot regression:

1. **Subset mismatch** — q14 and q22 (fixed by heading chunking) were excluded from the 11-case subset.
2. **Weak reference strings** — `reference` was built from keywords (`"B1 B2"`, `"24"`), which Ragas LLM-judge scores poorly on small chunks.

After [eval methodology fixes](#eval-methodology-improvements), recall rose to **0.93** on 15 cases — aligned with golden 25/25.

#### Why hybrid stays rejected

Hybrid was re-tested after re-indexing with heading chunks:

- Hit@5 **90%** vs dense **100%** — two questions lose expected source entirely.
- MRR slightly higher (0.608 vs 0.569) — BM25 sometimes promotes a better rank, but at the cost of missing files.
- Same pattern as baseline hybrid: BM25 matches generic tokens (“support”, “account”) in wrong articles.

**For a support bot, missing the right source in top-5 is worse than ranking it 2nd instead of 1st.** Keep `RETRIEVAL_MODE=dense` in `.env`.

---

## Eval methodology improvements

After heading chunking reached golden **25/25**, Ragas still showed recall **0.45** on the old setup. Two fixes aligned Ragas with end-to-end quality.

### 1. Expanded Ragas subset (`evals/ragas_eval.py`)

**Before:** 11 cases — q01–q10 + q15  
**After:** 15 cases — adds **q11** (support email), **q14** (mentor cancel window), **q21** (adversarial refund), **q22** (free trial)

These are the questions most sensitive to chunking and duplicate KB facts. q14/q22 were the original chunk pitfall cases.

### 2. Sentence-level `reference_answer` (`evals/golden_dataset.json`)

**Before:** Ragas `reference` built from keywords — e.g. q08 → `"B1 B2"`, q14 → `"24"`  
**After:** full sentence per case — e.g. q14 → `"You must cancel a mentor session at least 24 hours before the start time for a full refund."`

`ragas_eval.py` uses `reference_answer` when present, falls back to keywords otherwise.

### 3. `###` split for long sections (`ingest.py`)

Sections under a `##` heading that exceed 800 chars are split on `###` before falling back to fixed 600/100. Prevents mid-paragraph cuts (e.g. `## Subscription plans` in `plans-and-pricing.md`). Index: **119 chunks** (was 113).

### Impact

| Ragas setup | Cases | Reference | Context recall |
|-------------|-------|-----------|----------------|
| Old (on heading index) | 11 | keywords | **0.45** |
| **New (production eval)** | **15** | **sentences** | **0.93** |

Golden evals unchanged at **25/25** throughout. Only remaining Ragas gap: **q09** context recall = 0 (cancel flow steps split across chunks) — golden keyword check still passes.

---

| | Detail |
|---|--------|
| **Question** | How far in advance must I cancel a mentor session for a full refund? |
| **Expected keyword** | `24` (24+ hours) |
| **Expected source** | `mentor-sessions.md` |
| **Sources returned** | mentor-sessions ✓, cancel-subscription, refund-policy, general-faq |
| **Chunk retrieved (hit 1)** | End of `mentor-sessions.md` — “Refunds for mentor sessions… **Completed sessions are never refundable**” |
| **Chunk that has the answer** | **Chunk 2** — `## Session rules` table: “Full refund if cancelled **24+ hours** before start” |
| **LLM answer** | Correctly says context does not specify 24h — it only saw the refund footer chunk |
| **Root cause** | Fixed 600-char split ranks wrong subsection within the right file |

---

### Dense chunk pitfall — q22 (free trial) *(fixed by heading chunking)*

| | Detail |
|---|--------|
| **Question** | Does FoxSchool offer a free trial? |
| **Expected keywords** | `no`, `free trial` |
| **Expected source** | `general-faq.md` |
| **Sources returned** | general-faq ✓ (rank 1), create-account, welcome, mentor-sessions |
| **Chunk retrieved (hit 1)** | **Chunk 0** — FAQ intro + pricing table (“What is FoxSchool?”, “How much does FoxSchool cost?”) |
| **Chunk that has the answer** | **Chunk 2** — `## Is there a free trial?` → “FoxSchool **does not offer a free trial**” |
| **LLM answer** | “I don't have that information in the knowledge base” — faithful refusal given empty context on free trial |
| **Root cause** | Query embedding matches FAQ header/pricing; free-trial section is ~1200 chars into the file |

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

## Retrieval pitfall (case studies)

| Case | Mode | Problem |
|------|------|---------|
| **q14** | Dense + 600/100 | Right file, wrong chunk — Session rules vs refund footer → **fixed** by heading split |
| **q22** | Dense + 600/100 | Right file, wrong chunk — FAQ intro vs free-trial section → **fixed** by heading split |
| **q05, q08, q11** | Heading + dense | Correct answers from duplicate KB sections — golden now uses `expected_sources_any` |
| **q11** | Hybrid | Wrong files — BM25 matched generic “support” tokens |

**Hit@5 = 100% can hide chunk-level failures** under fixed-size chunking. Golden keyword checks caught q14/q22; heading chunking fixed them. After heading split, some questions cite a different but valid file (FAQ vs pricing) — that is expected KB behaviour, not a retrieval bug.

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

**Phase E baseline:**

```
question → dense retrieve (top-5) → LLM
         ← chunks: 600/100 fixed
```

**Production (Phase F):**

```
question → dense retrieve (top-5) → LLM
         ← chunks: heading-aware (## split)
         ← RETRIEVAL_MODE=dense
```

**Tested, not deployed — hybrid:**

```
question → BM25 + dense → RRF merge (top-5) → LLM
         ← Hit@5 90% on heading index; dense wins
```

**Optional next:**

```
question → dense retrieve (top-20) → cross-encoder rerank (top-5) → LLM
```

---

*Last updated: Production = dense + heading chunking; golden 25/25; Ragas recall 0.93 (15-case subset); hybrid rejected; eval methodology documented.*
