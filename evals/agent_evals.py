import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.agent import agent_ask

REFUSAL_PHRASE = "I don't have that information in the knowledge base"


def check_case(case: dict, result: dict) -> tuple[bool, str]:
    answer = result.get("answer", "")
    answer_lower = answer.lower()
    route = result.get("route")

    expected_route = case.get("expected_route")
    if expected_route and route != expected_route:
        return False, f"wrong route: expected {expected_route}, got {route}"

    if case.get("must_refuse"):
        if REFUSAL_PHRASE.lower() not in answer_lower:
            return False, f"expected refusal, got: {answer[:80]}"
        return True, "ok refusal"

    for kw in case.get("expected_contains", []):
        if kw.lower() not in answer_lower:
            return False, f"missing keyword: {kw}"

    for bad in case.get("must_not_contain", []):
        if bad.lower() in answer_lower:
            return False, f"forbidden content leaked: {bad}"

    return True, "ok"


def main() -> None:
    dataset_path = Path(__file__).parent / "agent_dataset.json"
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))

    passed = 0
    failed = []

    for case in cases:
        result = agent_ask(case["question"])
        ok, reason = check_case(case, result)
        if ok:
            passed += 1
        else:
            failed.append({"id": case["id"], "reason": reason, "route": result.get("route")})

    total = len(cases)
    rate = passed / total * 100
    print(f"Agent pass rate: {passed}/{total} ({rate:.1f}%)")

    if failed:
        print("\nFailed:")
        for f in failed:
            print(f"  {f['id']}: {f['reason']} (route={f.get('route')})")

    threshold = 80
    sys.exit(0 if rate >= threshold else 1)


if __name__ == "__main__":
    main()