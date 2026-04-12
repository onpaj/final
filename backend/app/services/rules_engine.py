import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID
from app.services.parsers.base import TransactionRow

_logger = logging.getLogger(__name__)

@dataclass
class RuleMatch:
    rule_id: UUID
    category_id: UUID

class RulesEngine:

    @staticmethod
    def _matches_single(tx: TransactionRow, match_type: str, match_value: dict) -> bool:
        if match_type == "counterparty_contains":
            return match_value["value"].lower() in (tx.counterparty_name or "").lower()
        if match_type == "counterparty_regex":
            return bool(re.search(match_value["pattern"], tx.counterparty_name or "", re.IGNORECASE))
        if match_type == "description_contains":
            return match_value["value"].lower() in (tx.description or "").lower()
        if match_type == "amount_range":
            amt = abs(tx.amount)
            return Decimal(str(match_value["min"])) <= amt <= Decimal(str(match_value["max"]))
        if match_type == "counterparty_account_equals":
            return (tx.counterparty_account or "").lower() == match_value["account"].lower()
        _logger.warning("Unknown match_type %r — rule will never match", match_type)
        return False

    @classmethod
    def _matches(cls, tx: TransactionRow, rule: dict) -> bool:
        if not rule.get("enabled", True):
            return False
        match_type = rule["match_type"]
        match_value = rule["match_value"]
        if match_type == "composite":
            return all(
                cls._matches_single(tx, c["type"], c)
                for c in match_value["conditions"]
            )
        return cls._matches_single(tx, match_type, match_value)

    @classmethod
    def apply(cls, tx: TransactionRow, rules: list[dict]) -> RuleMatch | None:
        sorted_rules = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)
        for rule in sorted_rules:
            if cls._matches(tx, rule):
                return RuleMatch(rule_id=rule["id"], category_id=rule["category_id"])
        return None
