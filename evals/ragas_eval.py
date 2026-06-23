"""Ragas evaluation — 4 RAG metrics on a golden-set subset."""

import json
import sys
import warnings
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

warnings.filterwarnings("ignore")  # hide ragas deprecation noise

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.rag import ask
from evals.snapshot import EVAL_METRICS_PATH, update_eval_snapshot

load_dotenv()

# Core in-scope cases + chunking-sensitive (q14, q22) + adversarial checks (q21)
SUBSET_IDS = {
    "q01", "q02", "q03", "q04", "q05", "q06", "q07", "q08", "q09", "q10",
    "q11", "q14", "q15", "q21", "q22",
}


def contexts_from_result(result: dict) -> list[str]:
    context = result.get("context", "")
    if not context:
        return [""]
    return [part.strip() for part in context.split("\n\n---\n\n") if part.strip()]


def reference_from_case(case: dict) -> str:
    if case.get("reference_answer"):
        return case["reference_answer"]
    parts = case.get("expected_contains", [])
    return " ".join(str(p) for p in parts)


def main() -> None:
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = [c for c in cases if c["id"] in SUBSET_IDS]

    print(f"Building Ragas dataset from {len(cases)} cases...")
    rows = []
    for case in cases:
        print(f"  {case['id']}: {case['question'][:60]}...")
        result = ask(case["question"])
        rows.append(
            {
                "user_input": case["question"],
                "response": result["answer"],
                "retrieved_contexts": contexts_from_result(result),
                "reference": reference_from_case(case),
            }
        )

    ds = Dataset.from_list(rows)

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    emb = OpenAIEmbeddings(model="text-embedding-3-small")

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    print("\nRunning Ragas evaluate (this takes a few minutes)...")
    result = evaluate(ds, metrics=metrics, llm=llm, embeddings=emb)

    df = result.to_pandas()
    print("\nPer-case scores:")
    print(df)

    print("\nAverage scores:")
    averages = df.mean(numeric_only=True)
    print(averages)

    ragas_metrics = {
        "faithfulness": round(float(averages["faithfulness"]), 2),
        "answer_relevancy": round(float(averages["answer_relevancy"]), 2),
        "context_precision": round(float(averages["context_precision"]), 2),
        "context_recall": round(float(averages["context_recall"]), 2),
    }
    update_eval_snapshot(ragas=ragas_metrics)
    print(f"Updated {EVAL_METRICS_PATH.name}: ragas = {ragas_metrics}")

    sys.exit(0)


if __name__ == "__main__":
    main()