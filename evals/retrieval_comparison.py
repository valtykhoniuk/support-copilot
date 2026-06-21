"""Retrieval-only benchmark — compare dense vs hybrid (no LLM calls)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag import RETRIEVAL_MODE, retrieve_dense, retrieve_hybrid

TOP_K = 5


def hit_at_k(hits: list[dict], expected_source: str) -> bool:
    return any(expected_source in h["source"] for h in hits)


def reciprocal_rank(hits: list[dict], expected_source: str) -> float:
    for i, h in enumerate(hits, start=1):
        if expected_source in h["source"]:
            return 1.0 / i
    return 0.0


def eval_retrieve(retrieve_fn, cases: list[dict], top_k: int = TOP_K) -> dict:
    hits_total = 0
    mrr_sum = 0.0
    failures = []

    for case in cases:
        hits = retrieve_fn(case["question"], top_k=top_k)
        expected = case["expected_sources_contain"]
        ok = hit_at_k(hits, expected)
        rr = reciprocal_rank(hits, expected)
        if ok:
            hits_total += 1
        else:
            failures.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "expected": expected,
                    "got": [h["source"] for h in hits],
                }
            )
        mrr_sum += rr

    n = len(cases)
    return {
        "hit_at_k": hits_total / n if n else 0.0,
        "mrr": mrr_sum / n if n else 0.0,
        "total": n,
        "failures": failures,
    }


def print_report(label: str, result: dict, top_k: int = TOP_K) -> None:
    print(f"\n=== {label} ===")
    print(
        f"Hit@{top_k}: {result['hit_at_k']:.1%}  "
        f"({int(result['hit_at_k'] * result['total'])}/{result['total']})"
    )
    print(f"MRR:       {result['mrr']:.3f}")
    if result["failures"]:
        print(f"\nMisses ({len(result['failures'])}):")
        for f in result["failures"]:
            print(f"  {f['id']}: {f['question'][:60]}...")
            print(f"    expected: *{f['expected']}*")
            print(f"    got:      {f['got'][:3]}")


def main() -> None:
    path = Path(__file__).parent / "golden_dataset.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    cases = [
        c for c in cases
        if not c.get("must_refuse") and c.get("expected_sources_contain")
    ]

    dense_result = eval_retrieve(retrieve_dense, cases)
    print_report("Dense only (Chroma)", dense_result)

    hybrid_result = eval_retrieve(retrieve_hybrid, cases)
    print_report("Hybrid (BM25 + dense, RRF)", hybrid_result)

    print(f"\nActive RETRIEVAL_MODE for ask(): {RETRIEVAL_MODE}")
    print("Benchmark always runs both modes; set RETRIEVAL_MODE in .env for API/evals.")

    sys.exit(0)


if __name__ == "__main__":
    main()
