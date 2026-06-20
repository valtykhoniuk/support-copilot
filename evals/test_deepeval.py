import json
import sys
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.rag import ask

# 5 cases — enough for CI, ~5 extra LLM calls per push
CASE_IDS = ["q01", "q02", "q04", "q05", "q06"]

def _load_cases():
    path = Path(__file__).parent / "golden_dataset.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [c for c in data if c["id"] in CASE_IDS]

def _contexts_from_result(result: dict) -> list[str]:
    context = result.get("context", "")
    if not context:
        return [""]
    return [p.strip() for p in context.split("\n\n---\n\n") if p.strip()]

@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_faithfulness(case):
    result = ask(case["question"])

    test_case = LLMTestCase(
        input=case["question"],
        actual_output=result["answer"],
        retrieval_context=_contexts_from_result(result),
    )

    metric = FaithfulnessMetric(threshold=0.7, model="gpt-4.1-mini")
    assert_test(test_case, [metric])