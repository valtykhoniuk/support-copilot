import os
import re
import time
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv
from langsmith import traceable
from openai import OpenAI
from rank_bm25 import BM25Okapi

from app.metrics import estimate_cost, log_request
from app.prompts import SYSTEM_PROMPT

load_dotenv()

CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION_NAME = "foxscool_kb"
TOP_K = 5
CANDIDATE_K = 20
RRF_K = 60
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "dense").lower()

_BM25_CACHE: dict | None = None


def get_collection():
    embed_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(name=COLLECTION_NAME, embedding_function=embed_fn)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _load_corpus() -> list[dict]:
    collection = get_collection()
    data = collection.get()
    corpus = []
    for doc_id, text, meta in zip(data["ids"], data["documents"], data["metadatas"]):
        corpus.append(
            {
                "id": doc_id,
                "text": text,
                "source": meta["source"],
            }
        )
    return corpus


def _get_bm25_index():
    global _BM25_CACHE
    if _BM25_CACHE is None:
        corpus = _load_corpus()
        tokenized = [_tokenize(c["text"]) for c in corpus]
        bm25 = BM25Okapi(tokenized)
        _BM25_CACHE = {"bm25": bm25, "corpus": corpus}
    return _BM25_CACHE


@traceable(name="retrieve_dense")
def retrieve_dense(query: str, top_k: int = TOP_K) -> list[dict]:
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    hits = []
    for text, metadata, distance, doc_id in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0],
    ):
        hits.append(
            {
                "id": doc_id,
                "text": text,
                "source": metadata["source"],
                "distance": distance,
            }
        )
    return hits


@traceable(name="retrieve_bm25")
def retrieve_bm25(query: str, top_k: int = CANDIDATE_K) -> list[dict]:
    cache = _get_bm25_index()
    bm25 = cache["bm25"]
    corpus = cache["corpus"]

    tokens = _tokenize(query)
    scores = bm25.get_scores(tokens)

    ranked = sorted(
        zip(corpus, scores),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    hits = []
    for chunk, score in ranked:
        hits.append(
            {
                "id": chunk["id"],
                "text": chunk["text"],
                "source": chunk["source"],
                "score_bm25": float(score),
            }
        )
    return hits


def rrf_merge(dense_hits: list[dict], bm25_hits: list[dict], top_k: int = TOP_K) -> list[dict]:
    scores: dict[str, float] = {}
    chunks: dict[str, dict] = {}

    for rank, hit in enumerate(dense_hits):
        cid = hit["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        chunks[cid] = hit

    for rank, hit in enumerate(bm25_hits):
        cid = hit["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        chunks[cid] = {**chunks.get(cid, {}), **hit}

    ranked_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

    result = []
    for cid in ranked_ids[:top_k]:
        hit = chunks[cid]
        hit["rrf_score"] = scores[cid]
        result.append(hit)
    return result


@traceable(name="retrieve_hybrid")
def retrieve_hybrid(query: str, top_k: int = TOP_K) -> list[dict]:
    dense = retrieve_dense(query, top_k=CANDIDATE_K)
    sparse = retrieve_bm25(query, top_k=CANDIDATE_K)
    return rrf_merge(dense, sparse, top_k=top_k)


@traceable(name="retrieve")
def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    if RETRIEVAL_MODE == "hybrid":
        return retrieve_hybrid(query, top_k=top_k)
    return retrieve_dense(query, top_k=top_k)


def build_context(hits: list[dict]) -> str:
    parts = []
    for hit in hits:
        parts.append(f"[Source: {hit['source']}] \n{hit['text']}")
    return "\n\n---\n\n".join(parts)


@traceable(name="generate_answer")
def generate_answer(query: str, context: str, hits: list[dict]) -> dict:
    prompt = SYSTEM_PROMPT.format(context=context)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ],
        temperature=0,
    )
    answer = response.choices[0].message.content
    usage = response.usage
    sources = list(dict.fromkeys(h["source"] for h in hits))

    return {
        "answer": answer,
        "sources": sources,
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
        },
    }


@traceable(name="ask")
def ask(query: str) -> dict:
    t0 = time.perf_counter()
    hits = retrieve(query)
    context = build_context(hits)
    gen = generate_answer(query, context, hits)

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    pt = gen["usage"]["prompt_tokens"]
    ct = gen["usage"]["completion_tokens"]

    result = {
        **gen,
        "context": context,
        "latency_ms": latency_ms,
        "cost_usd": round(estimate_cost(pt, ct), 6),
        "retrieval_mode": RETRIEVAL_MODE,
    }

    log_request(query, result)
    return result
