import re
import uuid
from decimal import Decimal
from datetime import date
from app.services.rules_engine import RulesEngine, RuleMatch
from app.services.parsers.base import TransactionRow

def make_tx(**kwargs):
    defaults = dict(
        booking_date=date(2026, 1, 1),
        value_date=None,
        amount=Decimal("-250.00"),
        currency="CZK",
        counterparty_name="ALBERT SUPERMARKET",
        counterparty_account=None,
        description="Nákup",
        raw_reference=None,
    )
    return TransactionRow(**{**defaults, **kwargs})

def make_rule(match_type, match_value, category_id=None, priority=100):
    return {
        "id": uuid.uuid4(),
        "match_type": match_type,
        "match_value": match_value,
        "category_id": category_id or uuid.uuid4(),
        "priority": priority,
        "enabled": True,
    }

def test_counterparty_contains_match():
    tx = make_tx(counterparty_name="ALBERT SUPERMARKET")
    rule = make_rule("counterparty_contains", {"value": "albert"})
    result = RulesEngine.apply(tx, [rule])
    assert result is not None
    assert result.category_id == rule["category_id"]

def test_counterparty_contains_no_match():
    tx = make_tx(counterparty_name="KAUFLAND")
    rule = make_rule("counterparty_contains", {"value": "albert"})
    assert RulesEngine.apply(tx, [rule]) is None

def test_counterparty_regex_match():
    tx = make_tx(counterparty_name="ALBERT CZ s.r.o.")
    rule = make_rule("counterparty_regex", {"pattern": r"^ALBERT"})
    result = RulesEngine.apply(tx, [rule])
    assert result is not None

def test_description_contains_match():
    tx = make_tx(description="nájem byt")
    rule = make_rule("description_contains", {"value": "nájem"})
    assert RulesEngine.apply(tx, [rule]) is not None

def test_amount_range_match():
    tx = make_tx(amount=Decimal("-14500.00"))
    rule = make_rule("amount_range", {"min": 14000, "max": 15000})
    assert RulesEngine.apply(tx, [rule]) is not None

def test_amount_range_no_match():
    tx = make_tx(amount=Decimal("-500.00"))
    rule = make_rule("amount_range", {"min": 14000, "max": 15000})
    assert RulesEngine.apply(tx, [rule]) is None

def test_composite_all_conditions_match():
    tx = make_tx(counterparty_name="SBERBANK", amount=Decimal("-14500.00"))
    rule = make_rule("composite", {"conditions": [
        {"type": "counterparty_contains", "value": "SBERBANK"},
        {"type": "amount_range", "min": 14000, "max": 15000},
    ]})
    assert RulesEngine.apply(tx, [rule]) is not None

def test_composite_partial_match_fails():
    tx = make_tx(counterparty_name="SBERBANK", amount=Decimal("-500.00"))
    rule = make_rule("composite", {"conditions": [
        {"type": "counterparty_contains", "value": "SBERBANK"},
        {"type": "amount_range", "min": 14000, "max": 15000},
    ]})
    assert RulesEngine.apply(tx, [rule]) is None

def test_priority_order():
    cat_low = uuid.uuid4()
    cat_high = uuid.uuid4()
    tx = make_tx(counterparty_name="ALBERT")
    rules = [
        make_rule("counterparty_contains", {"value": "albert"}, cat_low, priority=10),
        make_rule("counterparty_contains", {"value": "albert"}, cat_high, priority=200),
    ]
    result = RulesEngine.apply(tx, rules)
    assert result.category_id == cat_high

def test_disabled_rule_skipped():
    tx = make_tx(counterparty_name="ALBERT")
    rule = make_rule("counterparty_contains", {"value": "albert"})
    rule["enabled"] = False
    assert RulesEngine.apply(tx, [rule]) is None
