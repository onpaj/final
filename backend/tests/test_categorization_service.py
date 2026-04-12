import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.categorization_service import CategorizationService
from app.services.anthropic_client import AnthropicClassificationError

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


async def test_llm_error_writes_classification_row():
    """When AnthropicClassificationError is raised, an LlmClassification row with reasoning='error' must be saved."""
    tx = MagicMock()
    tx.id = uuid.uuid4()
    tx.counterparty_name = "UNKNOWN"
    tx.description = ""
    tx.amount = Decimal("-100.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
    added_rows = []
    mock_db.add = MagicMock(side_effect=added_rows.append)

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        MockLLM.return_value.classify.side_effect = AnthropicClassificationError("timeout")
        service = CategorizationService(mock_db)
        await service._categorize_one(tx, [], [])

    assert tx.category_id is None
    assert len(added_rows) == 1
    row = added_rows[0]
    assert row.transaction_id == tx.id
    assert row.accepted is False
    assert row.reasoning == "error"
    assert row.confidence is None


async def test_rules_only_categorizes_on_match():
    """_categorize_one_rules_only sets category when a rule matches."""
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
    mock_rule_obj = MagicMock()
    mock_rule_obj.hit_count = 0
    mock_db.get = AsyncMock(return_value=mock_rule_obj)

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        service = CategorizationService(mock_db)
        await service._categorize_one_rules_only(tx, [rule])
        MockLLM.return_value.classify.assert_not_called()

    assert tx.category_id == groceries_id
    assert tx.categorization_source == "rule"
    assert tx.confidence == Decimal("1.0")
    assert mock_rule_obj.hit_count == 1
    assert mock_rule_obj.last_hit_at is not None


async def test_rules_only_leaves_uncategorized_when_no_match():
    """_categorize_one_rules_only does nothing when no rule matches."""
    tx = MagicMock()
    tx.counterparty_name = "UNKNOWN SHOP"
    tx.description = ""
    tx.amount = Decimal("-100.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_db = AsyncMock()

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        service = CategorizationService(mock_db)
        await service._categorize_one_rules_only(tx, [])
        MockLLM.return_value.classify.assert_not_called()

    assert tx.category_id is None


async def test_rules_only_handles_deleted_rule_gracefully():
    """_categorize_one_rules_only still categorizes even if the rule no longer exists in DB."""
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
    mock_db.get = AsyncMock(return_value=None)  # rule deleted from DB

    service = CategorizationService(mock_db)
    await service._categorize_one_rules_only(tx, [rule])

    # Transaction is still categorized — missing rule object doesn't block categorization
    assert tx.category_id == groceries_id
    assert tx.categorization_source == "rule"


async def test_llm_only_skips_rules_and_categorizes():
    """_categorize_one_llm_only calls LLM and sets category when confidence is high."""
    from app.services.anthropic_client import CONFIDENCE_THRESHOLD

    groceries_id = uuid.uuid4()

    tx = MagicMock()
    tx.id = uuid.uuid4()
    tx.counterparty_name = "ALBERT SUPERMARKET"
    tx.description = ""
    tx.amount = Decimal("-250.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_category = MagicMock()
    mock_category.id = groceries_id

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=lambda: MagicMock(first=lambda: mock_category))
    )
    added_rows = []
    mock_db.add = MagicMock(side_effect=added_rows.append)

    llm_result = MagicMock()
    llm_result.category_name = "Groceries"
    llm_result.confidence = CONFIDENCE_THRESHOLD  # exactly at threshold = accepted
    llm_result.reasoning = "supermarket"
    llm_result.model = "claude-haiku-4-5"
    llm_result.prompt_tokens = 100
    llm_result.completion_tokens = 50

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM, \
         patch("app.services.categorization_service.RulesEngine") as MockRules:
        MockLLM.return_value.classify.return_value = llm_result
        service = CategorizationService(mock_db)
        await service._categorize_one_llm_only(tx, [("Food", "Groceries", None)])
        MockRules.apply.assert_not_called()

    assert tx.category_id == groceries_id
    assert tx.categorization_source == "llm"
    assert len(added_rows) == 1  # LlmClassification log written


async def test_llm_only_error_writes_classification_row():
    """_categorize_one_llm_only on LLM error writes error log, leaves uncategorized."""
    tx = MagicMock()
    tx.id = uuid.uuid4()
    tx.counterparty_name = "UNKNOWN"
    tx.description = ""
    tx.amount = Decimal("-100.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_db = AsyncMock()
    added_rows = []
    mock_db.add = MagicMock(side_effect=added_rows.append)

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        MockLLM.return_value.classify.side_effect = AnthropicClassificationError("timeout")
        service = CategorizationService(mock_db)
        await service._categorize_one_llm_only(tx, [("Food", "Groceries", None)])

    assert tx.category_id is None
    assert len(added_rows) == 1
    assert added_rows[0].reasoning == "error"
    assert added_rows[0].accepted is False


async def test_run_batch_rules_mode_does_not_call_llm():
    """run_batch with mode='rules' never calls LLM even when no rule matches."""
    tx = MagicMock()
    tx.id = uuid.uuid4()
    tx.counterparty_name = "UNKNOWN"
    tx.description = ""
    tx.amount = Decimal("-100.00")
    tx.category_id = None
    tx.booking_date = date(2026, 1, 1)
    tx.value_date = None
    tx.currency = "CZK"
    tx.counterparty_account = None
    tx.raw_reference = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [tx]))
    )
    mock_db.commit = AsyncMock()

    with patch("app.services.categorization_service.AnthropicClient") as MockLLM:
        service = CategorizationService(mock_db)
        service._load_rules = AsyncMock(return_value=[])
        service._load_categories = AsyncMock(return_value=[])
        result = await service.run_batch([tx.id], mode="rules")
        MockLLM.return_value.classify.assert_not_called()

    assert result["needs_review"] == 1
    assert result["categorized"] == 0
