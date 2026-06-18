import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.rag import ask

REFUSAL_PHRASE = "I don't have that information in the knowledge base"

def check_case(case: dict, result: dict) -> tuple[bool, str]:
    answer = result['answer']
    sources = result['sources']

    answer_lower = answer.lower()
    if case.get("must_refuse"):
        if REFUSAL_PHRASE.lower() in answer_lower:
            return True, "ok refusal"
        return False, f"expected refusal, got: {answer[:80]}"
    
    for kw in case.get("expected_contains", []):
        if kw.lower() not in answer_lower:
            return False, f"missing keyword: {kw}"
        
    src_needle = case.get("expected_sources_contain")
    if src_needle:
        if not any(src_needle in s for s in sources):
            return False, f"source missing: {src_needle}"
    return True, "ok"

def main():
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))
    passed = 0
    failed = []
    for case in cases:
        result = ask(case["question"])
        ok, reason = check_case(case, result)
        if ok:
            passed += 1
        else:
            failed.append({"id": case["id"], "reason": reason})
    total = len(cases)
    rate = passed / total * 100
    print(f"Pass rate: {passed}/{total} ({rate:.1f}%)")
    if failed:
        print("\nFailed:")
        for f in failed:
            print(f"  {f['id']}: {f['reason']}")
    THRESHOLD = 80 
    sys.exit(0 if rate >= THRESHOLD else 1)

    
if __name__ == "__main__":
    main()



