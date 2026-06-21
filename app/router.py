import re

TICKET_PATTERN = re.compile(r"TKT-\d{4}", re.IGNORECASE)

REFUND_KEYWORDS = (
    "refund",
    "money back",
    "eligible for refund",
    "get my money"
)

ROUTE_KB = "kb"
ROUTE_TICKET = "ticket"
ROUTE_REFUND = "refund"

def route(question: str) -> str:
    q = question.lower()

    if TICKET_PATTERN.search(question):
        return ROUTE_TICKET
    if any(kw in q for kw in REFUND_KEYWORDS):
        return ROUTE_REFUND
    
    return ROUTE_KB

def extract_ticket_id(question: str) -> str | None:
    match = TICKET_PATTERN.search(question)
    if not match:
        return None
    return match.group(0).upper()