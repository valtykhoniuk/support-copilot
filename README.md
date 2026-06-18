# FoxSchool Support Copilot

![CI](https://github.com/valtykhoniuk/support-copilot/actions/workflows/ci.yml/badge.svg)

AI support assistant for **FoxSchool** — a fictional SaaS language-learning platform. Answers customer questions from a synthetic knowledge base (pricing, refunds, mentor sessions, troubleshooting) with **source citations** and **refusal** for out-of-scope queries.

Built as a production-style RAG pipeline with automated evals and a CI eval gate — not a tutorial chatbot.

## Problem

Support teams for subscription products answer the same factual questions repeatedly (plan prices, refund windows, billing). This copilot:

- Retrieves relevant KB chunks via dense vector search (Chroma)
- Generates answers **only from retrieved context** (GPT-4.1-mini, temperature 0)
- Returns `{answer, sources[]}` for traceability
- Is regression-tested on 25 golden questions with an **80% pass-rate gate** in CI

## Architecture

```
data/kb/*.md  ──►  ingest.py  ──►  Chroma (chroma_db/)
                                      │
User question ──►  POST /ask  ──►  retrieve (top-5)
                                      │
                                      ▼
                              build context + SYSTEM_PROMPT
                                      │
                                      ▼
                              OpenAI gpt-4.1-mini  ──►  answer + sources
```

| Component | Choice |
|-----------|--------|
| API | FastAPI (`/health`, `/ask`) |
| Vector DB | Chroma (persistent, local) |
| Embeddings | `all-MiniLM-L6-v2` via sentence-transformers (local, free) |
| LLM | OpenAI `gpt-4.1-mini` |
| Prompt | Context-only + fixed refusal phrase (`prompts.py` v1.0) |
| Chunking | 600 chars, 100 overlap |

## Quickstart

### Prerequisites

- Python 3.13+
- OpenAI API key

### Setup

```bash
git clone https://github.com/valtykhoniuk/support-copilot.git
cd support-copilot

python -m venv support-copilot
source support-copilot/bin/activate   # Windows: support-copilot\Scripts\activate

pip install -r requirements.txt
```

Create `.env` in the project root:

```env
OPENAI_API_KEY=your_key_here
```

### Index the knowledge base

Run once (or after KB changes):

```bash
python ingest.py
```

Expected output: `Ingested N chunks from 15 files`. Creates `chroma_db/` (gitignored).

### Run the API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Ask a question

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How much does the Beginner plan cost?"}'
```

Example response:

```json
{
  "answer": "The Beginner plan costs $20 per month and includes A1 and A2 levels.",
  "sources": ["data/kb/billing/plans-and-pricing.md"]
}
```

## API

| Endpoint | Method | Body | Response |
|----------|--------|------|----------|
| `/health` | GET | — | `{"status": "ok"}` |
| `/ask` | POST | `{"question": "..."}` | `{"answer": "...", "sources": ["..."]}` |

## Evaluation

Automated regression tests on a golden dataset — the main quality signal for this project.

| Metric | Value |
|--------|-------|
| Golden set | 25 questions (`evals/golden_dataset.json`) |
| In-scope | 15 — pricing, refunds, mentor sessions, FAQ |
| Out-of-scope | 5 — must trigger refusal phrase |
| Adversarial | 5 — in-scope traps (e.g. refund after 20 days → answer is *no*) |
| **Pass rate** | **25/25 (100%)** — prompt v1.0 |
| Eval gate | CI fails if pass rate < **80%** |

### Run evals locally

```bash
python ingest.py && python evals/run_evals.py
```

### What each case checks

1. **In-scope / adversarial:** answer contains expected keywords; at least one source matches expected file substring
2. **Out-of-scope:** answer contains `"I don't have that information in the knowledge base."`

Re-run evals after any change to prompts, chunking, or retrieval.

## CI

GitHub Actions (`.github/workflows/ci.yml`) on every push/PR to `main`:

1. Install dependencies
2. Lint with ruff (non-blocking)
3. `python ingest.py`
4. `python evals/run_evals.py` — **eval gate**

Requires `OPENAI_API_KEY` in repository Secrets.

## Project structure

```
support-copilot/
├── app/
│   ├── main.py       # FastAPI: /health, /ask
│   ├── rag.py        # retrieve + generate
│   └── prompts.py    # system prompt v1.0
├── data/
│   └── kb/           # 15 synthetic FoxSchool KB articles
├── evals/
│   ├── golden_dataset.json
│   └── run_evals.py
├── ingest.py         # md → chunks → Chroma
├── chroma_db/        # vector index (local, not in git)
└── .github/workflows/ci.yml
```

## Trade-offs (current)

- **Local embeddings (MiniLM):** free and fast; cloud embeddings may improve retrieval quality
- **Dense retrieval only:** no BM25 / hybrid search yet (on roadmap)
- **Keyword-based evals:** fast and deterministic; brittle on source file matching when multiple docs contain the same fact
- **No agent layer yet:** ticket lookup and refund calculation via tools — planned

## Roadmap

**Shipped (v0.1)**

- RAG over synthetic support KB (ingest → Chroma → cited answers)
- FastAPI `/ask` endpoint with refusal for out-of-scope questions
- Golden-set evals (25 cases) + 80% pass-rate gate in CI

**Next**

| Priority | Capability |
|----------|------------|
| Security | Red-team harness (jailbreak, prompt injection, OWASP LLM risks) |
| Quality | LLM-as-judge, RAGAS metrics, request latency/cost logging |
| Retrieval | Hybrid search (BM25 + dense) + cross-encoder reranking |
| Agents | Tool use: ticket status, refund calculator, KB search via MCP |
| Production | Docker, multi-provider LLM, cloud deploy |
