import re

from app import intent_classifier

TICKET_PATTERN = re.compile(r"TKT-\d{4}", re.IGNORECASE)

REFUND_KEYWORDS = (
    "refund",
    "money back",
    "eligible for refund",
    "get my money",
)

ROUTE_KB = "kb"
ROUTE_TICKET = "ticket"
ROUTE_REFUND = "refund"


def intent_to_route(intent: str) -> str:
    if intent == "refund":
        return ROUTE_REFUND
    return ROUTE_KB


def route_rules(question: str) -> str:
    """Keyword router — used when LoRA is off or as refund fallback."""
    q = question.lower()
    if any(kw in q for kw in REFUND_KEYWORDS):
        return ROUTE_REFUND
    return ROUTE_KB


def route(question: str) -> str:
    """Backward-compatible: returns route only."""
    chosen, _ = route_with_meta(question)
    return chosen


def route_with_meta(question: str) -> tuple[str, dict]:
    """
    Pick agent path: ticket | refund | kb.

    Returns (route, meta) where meta may include:
      - router: "regex" | "lora" | "keywords"
      - intent: billing | bug | how-to | refund | other (LoRA only)
    """
    if TICKET_PATTERN.search(question):
        return ROUTE_TICKET, {"router": "regex"}

    if intent_classifier.is_enabled():
        intent = intent_classifier.predict_intent(question)
        return intent_to_route(intent), {"router": "lora", "intent": intent}

    return route_rules(question), {"router": "keywords"}


def extract_ticket_id(question: str) -> str | None:
    match = TICKET_PATTERN.search(question)
    if not match:
        return None
    return match.group(0).upper()
