from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from app.services.analytics_service import AnalyticsService


async def test_monthly_summary_structure():
    mock_db = AsyncMock()

    mock_row = MagicMock()
    mock_row.group_name = "Living"
    mock_row.group_color = "#4CAF50"
    mock_row.category_name = "Groceries"
    mock_row.is_income = False
    mock_row.total = Decimal("-3500.00")

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]

    mock_unclassified_row = MagicMock()
    mock_unclassified_row.cnt = 0
    mock_unclassified_row.total = Decimal("0")
    mock_unclassified_result = MagicMock()
    mock_unclassified_result.one.return_value = mock_unclassified_row

    mock_db.execute.side_effect = [mock_result, mock_unclassified_result]

    service = AnalyticsService(mock_db)
    summary = await service.monthly_summary(2026, 4)

    assert "groups" in summary
    assert "income" in summary
    assert "expenses" in summary
    assert "savings_rate" in summary


async def test_savings_rate_calculation():
    service = AnalyticsService(AsyncMock())
    rate = service._savings_rate(income=Decimal("50000"), expenses=Decimal("-30000"))
    assert rate == Decimal("0.40")


async def test_savings_rate_zero_income():
    service = AnalyticsService(AsyncMock())
    rate = service._savings_rate(income=Decimal("0"), expenses=Decimal("-1000"))
    assert rate == Decimal("0")
