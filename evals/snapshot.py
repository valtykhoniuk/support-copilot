"""Merge eval run results into data/eval_metrics.json for the dashboard API."""

import json
from pathlib import Path

EVAL_METRICS_PATH = Path(__file__).parent.parent / "data" / "eval_metrics.json"


def update_eval_snapshot(**sections: dict) -> None:
    """Update one or more top-level keys (e.g. llm_judge, golden_rag, ragas)."""
    if EVAL_METRICS_PATH.exists():
        data = json.loads(EVAL_METRICS_PATH.read_text(encoding="utf-8"))
    else:
        data = {}

    data.update(sections)

    EVAL_METRICS_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
