import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.categorization_service import CategorizationService

async def test_rule_match_does_not_call_llm():
    groceries_id = uuid.uuid4()
    rule = {
        "id": uuid.uuid4(),
        "match_type": "counterparty_contains",
        "match_value": {"value": "ALBERT"},
        "category_id": groceries_id,
        "priority": 100,
        "enabled": True,
    }
    tx = MagicMock()
    tx.counterparty_name = "ALBERT SUPERMARKET"
    tx.description = ""
    tx.amount = Decimal("-250.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [MagicMock(**rule)])))

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        service = CategorizationService(mock_db)
        await service._categorize_one(tx, [rule], [])
        MockLLM.return_value.classify.assert_not_called()

    assert tx.category_id == groceries_id
    assert tx.categorization_source == "rule"
    assert tx.confidence == Decimal("1.0")
