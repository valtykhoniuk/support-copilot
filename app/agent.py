import time

from langsmith import traceable

from app.guardrails import (
    REFUSAL,
    format_refund_answer,
    format_ticket_answer,
    is_pii_request,
)
from app.metrics import estimate_cost, log_request
from app.rag import ask as rag_ask
from app.router import ROUTE_KB, ROUTE_REFUND, ROUTE_TICKET, extract_ticket_id, route
from app.tools import calculate_refund_eligibility, extract_days_from_question, lookup_ticket

@traceable(name="handle_ticket")
def handle_ticket(question: str) -> dict:
    ticket_id = extract_ticket_id(question)
    if not ticket_id: 
        return{
            "answer": "Please provide a ticket ID (e.g. TKT-1002).",
            "sources": ["data/tickets.json"],
            "route": ROUTE_TICKET,
        }
    ticket = lookup_ticket(ticket_id)
    return {
        "answer": format_ticket_answer(ticket),
        "sources": ["data/tickets.json"],
        "route": ROUTE_TICKET,
        "tool": "lookup_ticket",
        "tool_result": ticket,
    }

@traceable(name="handle_refund")
def handle_refund(question: str) -> dict:
    days = extract_days_from_question(question)
    if days is None:
        result = rag_ask(question)
        result["route"] = ROUTE_REFUND
        result["fallback"] = "kb_no_days"
        return result
    
    calc = calculate_refund_eligibility(days)
    return {
        "answer": format_refund_answer(calc),
        "sources": ["data/kb/billing/refund-policy.md"],
        "route": ROUTE_REFUND,
        "tool": "calculate_refund_eligibility",
        "tool_result": calc,
    }

@traceable(name="agent_ask")
def agent_ask(question: str) -> dict:
    t0 = time.perf_counter()

    if is_pii_request(question):
        result = {
            "answer": REFUSAL,
            "sources": [],
            "route": "blocked_pii",
        }
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        result["cost_usd"] = 0.0
        log_request(question, result)
        return result
    
    chosen_route = route(question)
    
    if chosen_route == ROUTE_TICKET:
        result = handle_ticket(question)
    elif chosen_route == ROUTE_REFUND:
        result = handle_refund(question)
    else:
        result = rag_ask(question)
        result["route"] = ROUTE_KB
    if "latency_ms" not in result:
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    if "cost_usd" not in result:
        result["cost_usd"] = 0.0
    log_request(question, result)
    return result
