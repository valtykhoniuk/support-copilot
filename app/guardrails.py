REFUSAL = "Your query is refused. I don't have that information in the knowledge base."

PII_PATTERNS = (
    "customer_email",
    "@example.com",
    "send me the email",
    "customer email",
    "email on ticket",
    "email for ticket",
    "email address on",
    "email address for",
)

def is_pii_request(question: str) -> bool:
    q = question.lower()
    return any(p in q for p in PII_PATTERNS)

def format_ticket_answer(ticket: dict) -> str:
    if not ticket.get("found"):
        return f"I couldn't find a ticket with ID {ticket['id']}."
    return (
        f"Ticket {ticket['id']} is **{ticket['status']}** "
        f"(priority: {ticket['priority']}, plan: {ticket['plan']}). "
        f"Subject: {ticket['subject']}. "
        f"Last updated: {ticket['updated_at']}."
    )

def format_refund_answer(result: dict) -> str:
    if result["eligible"]:
        return (
            f"Yes — you are within the {result['refund_window_days']}-day refund window "
            f"({result['days_since_first_payment']} days since first payment). "
            f"{result['reason']}"
        )
    return (
        f"No — {result['days_since_first_payment']} days since first payment exceeds "
        f"the {result['refund_window_days']}-day window. {result['reason']}"
    )