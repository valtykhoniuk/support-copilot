import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp.server.fastmcp import FastMCP
from app.guardrails import format_ticket_answer
from app.tools import lookup_ticket

mcp = FastMCP("foxschool-tickets")

TICKET_ID_PATTERN = re.compile(r"^TKT-\d{4}$", re.IGNORECASE)

def _normalize_ticket_id(ticket_id: str) -> str:
    return ticket_id.strip().upper()

@mcp.tool()
def get_ticket_status(ticket_id: str) -> str:
    """Look up a FoxSchool support ticket by ID (e.g. TKT-1002).
    Returns status, priority, plan, subject, and last update.
    Does NOT return customer email or other PII.
    Use when the user asks about ticket status or what's in a ticket.
    """
    ticket_id = _normalize_ticket_id(ticket_id)
    if not TICKET_ID_PATTERN.match(ticket_id):
        return f"Invalid ticket ID format: {ticket_id}. Expected TKT-1001 style."
    ticket = lookup_ticket(ticket_id)
    return format_ticket_answer(ticket)

@mcp.tool()
def list_open_tickets() -> str:
    """List all open FoxSchool support tickets (id, subject, priority, plan).
    No customer emails. Use for overview questions like 'what open tickets do we have?'
    """
    tickets_path = Path(__file__).parent.parent / "data" / "tickets.json"
    tickets = json.loads(tickets_path.read_text(encoding="utf-8"))
    open_tickets = [t for t in tickets if t["status"] == "open"]
    if not open_tickets:
        return "No open tickets."
    lines = []
    for t in open_tickets:
        lines.append(
            f"- {t['id']}: {t['subject']} "
            f"(priority: {t['priority']}, plan: {t['plan']})"
        )
    return "\n".join(lines)

if __name__ == "__main__":
    mcp.run()