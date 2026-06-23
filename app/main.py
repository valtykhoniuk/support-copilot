from pathlib import Path
import json

from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import agent_ask

METRICS_PATH = Path(__file__).parent.parent / "data" / "eval_metrics.json"

app = FastAPI(title="FoxSchool Support Copilot")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class EvalPassRate(BaseModel):
    passed: int
    total: int


class RagasMetrics(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


class EvalMetrics(BaseModel):
    golden_rag: EvalPassRate
    golden_agent: EvalPassRate
    llm_judge: EvalPassRate
    ragas: RagasMetrics


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(body: AskRequest):
    result = agent_ask(body.question)
    usage = result.get("usage", {})
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        latency_ms=result["latency_ms"],
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        cost_usd=result.get("cost_usd", 0.0),
    )


@app.get("/eval_metrics", response_model=EvalMetrics)
def eval_metrics_endpoint():
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
