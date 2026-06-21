import json
import re
from pathlib import Path

TICKETS_PATH = Path(__file__).parent.parent / "data" / "tickets.json"
REFUND_WINDOW_DAYS = 7 

def _load_tickets() -> list[dict]:
    return json.loads(TICKETS_PATH.read_text(encoding="utf-8"))

def lookup_ticket(ticket_id: str) -> dict:
    ticket_id = ticket_id.upper()
    for ticket in _load_tickets():
        if ticket["id"] == ticket_id:
            return {
                "found": True,
                "id": ticket["id"],
                "status": ticket["status"],
                "priority": ticket["priority"],
                "plan": ticket["plan"],
                "subject": ticket["subject"],
                "created_at": ticket["created_at"],
                "updated_at": ticket["updated_at"],
            }
    return {"found": False, "id": ticket_id}

def calculate_refund_eligibility(days_since_first_payment: int) -> dict:
    eligible = days_since_first_payment <= REFUND_WINDOW_DAYS
    return {
        "days_since_first_payment": days_since_first_payment,
        "refund_window_days": REFUND_WINDOW_DAYS,
        "eligible": eligible,
        "reason": (
            "Full refund available within 7 days of first subscription payment." 
            if eligible
            else "Outside the 7-day first-payment refund window; renewal charges are not refundable."
        ),
    }

def extract_days_from_question(question: str) -> int | None:
    q = question.lower()
    patterns = [
        r"(\d+)\s*days?\s*ago",
        r"after\s*(\d+)\s*days?",
        r"(\d+)\s*days?\s*after",
    ]
    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            return int(match.group(1))
    return None
