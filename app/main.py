from fastapi import FastAPI
from pydantic import BaseModel
from app.agent import agent_ask

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

class EvalMetrics(BaseModel):
    golden_dataset_rag: int
    golden_dataset_agents: int
    llm_judge: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    faithfulness: float

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