from fastapi import FastAPI
from pydantic import BaseModel
from app.rag import ask

app = FastAPI(title="FoxSchool Support Copilot")

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    sources: list[str]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AskResponse)
def ask_endpoint(body: AskRequest):
    result = ask(body.question)
    return AskResponse(answer=result['answer'], sources=result['sources'])