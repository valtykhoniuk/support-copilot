import os

import pytest

from app.router import (
    ROUTE_KB,
    ROUTE_REFUND,
    ROUTE_TICKET,
    intent_to_route,
    route_rules,
    route_with_meta,
)


@pytest.mark.parametrize(
    "intent,expected",
    [
        ("refund", ROUTE_REFUND),
        ("billing", ROUTE_KB),
        ("bug", ROUTE_KB),
        ("how-to", ROUTE_KB),
        ("other", ROUTE_KB),
    ],
)
def test_intent_to_route(intent, expected):
    assert intent_to_route(intent) == expected


def test_ticket_regex_wins_over_keywords():
    question = "Refund on ticket TKT-1003 — what is the status?"
    route, meta = route_with_meta(question)
    assert route == ROUTE_TICKET
    assert meta["router"] == "regex"


def test_refund_keywords_when_lora_disabled(monkeypatch):
    monkeypatch.delenv("USE_LORA_ROUTER", raising=False)
    route, meta = route_with_meta("Can I get my money back after 5 days?")
    assert route == ROUTE_REFUND
    assert meta["router"] == "keywords"


def test_billing_goes_to_kb_with_keywords_router(monkeypatch):
    monkeypatch.delenv("USE_LORA_ROUTER", raising=False)
    route, meta = route_with_meta("How much does the Beginner plan cost?")
    assert route == ROUTE_KB
    assert meta["router"] == "keywords"
