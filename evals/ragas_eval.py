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

load_dotenv()

SUBSET_IDS = {"q01", "q02", "q03", "q04", "q05", "q06", "q07", "q08", "q09", "q10", "q15"}


def contexts_from_result(result: dict) -> list[str]:
    context = result.get("context", "")
    if not context:
        return [""]
    return [part.strip() for part in context.split("\n\n---\n\n") if part.strip()]


def reference_from_case(case: dict) -> str:
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
    print(df.mean(numeric_only=True))

    sys.exit(0)


if __name__ == "__main__":
    main()