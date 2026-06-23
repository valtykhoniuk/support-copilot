import json
import os
import sys
from pathlib import Path
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.rag import ask
from evals.snapshot import EVAL_METRICS_PATH, update_eval_snapshot

JUDGE_PROMPT = """You evaluate a support chatbot.
CONTEXT (retrieved from KB):
{context}
USER QUESTION:
{question}
ASSISTANT ANSWER:
{answer}
Is every factual claim in the answer fully supported by the CONTEXT?
Reply with JSON only: {{"grounded": true or false, "reason": "one sentence"}}
"""

def judge(client: OpenAI, question: str, context: str, answer: str) -> dict:
    msg = JUDGE_PROMPT.format(context=context, question=question, answer=answer)
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": msg}],
        temperature=0,
        response_format={"type": "json_object"}
    )

    return json.loads(resp.choices[0].message.content)

def main():
    dataset = json.loads(
        (Path(__file__).parent / "golden_dataset.json").read_text(encoding="utf-8")
    )

    cases = [c for c in dataset if not c.get("must_refuse")]
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    passed = 0
    for case in cases:
        response = ask(case["question"])
        verdict = judge(client, case["question"], response["context"], response["answer"])
        ok = verdict.get("grounded") is True
        if ok:
            passed += 1
        print(f"{case['id']}: {'PASS' if ok else 'FAIL'} — {verdict.get('reason')}")
    
    total = len(cases)
    rate = passed / total * 100
    print(f"\nGroundedness: {passed}/{total} ({rate:.1f}%)")

    update_eval_snapshot(llm_judge={"passed": passed, "total": total})
    print(f"Updated {EVAL_METRICS_PATH.name}: llm_judge = {passed}/{total}")

    sys.exit(0 if rate >= 80 else 1)

if __name__ == "__main__":
    main()
