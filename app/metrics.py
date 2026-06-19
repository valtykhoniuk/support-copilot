import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "logs" / "metrics.jsonl"

INPUT_USD_PER_1M = 0.40
OUTPUT_USD_PER_1M = 1.60

def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        prompt_tokens * INPUT_USD_PER_1M / 1_000_000
        + completion_tokens * OUTPUT_USD_PER_1M / 1_000_000
    )

def log_request(question: str, result: dict) -> None:
    usage = result.get("usage", {})
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "question": question[:200],
        "latency_ms": result.get("latency_ms"),
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cost_usd": result.get("cost_usd"),
    }

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")