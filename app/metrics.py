import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "logs" / "metrics.jsonl"

# gpt-4.1-mini (OpenAI)
OPENAI_INPUT_USD_PER_1M = 0.40
OPENAI_OUTPUT_USD_PER_1M = 1.60

# Claude 3 Haiku on Bedrock (approximate)
BEDROCK_INPUT_USD_PER_1M = 0.25
BEDROCK_OUTPUT_USD_PER_1M = 1.25


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    provider: str | None = None,
) -> float:
    llm_provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
    if llm_provider == "bedrock":
        input_rate, output_rate = BEDROCK_INPUT_USD_PER_1M, BEDROCK_OUTPUT_USD_PER_1M
    else:
        input_rate, output_rate = OPENAI_INPUT_USD_PER_1M, OPENAI_OUTPUT_USD_PER_1M
    return (
        prompt_tokens * input_rate / 1_000_000
        + completion_tokens * output_rate / 1_000_000
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
        "llm_provider": result.get("llm_provider"),
    }

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")