import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from app.services.transfer_matcher import TransferMatcher


def make_tx(amount, booking_date, account_id=None, tx_id=None):
    tx = MagicMock()
    tx.id = tx_id or uuid.uuid4()
    tx.amount = Decimal(str(amount))
    tx.booking_date = booking_date
    tx.account_id = account_id or uuid.uuid4()
    tx.is_transfer = False
    tx.transfer_pair_id = None
    tx.category_id = None
    return tx


@pytest.mark.asyncio
async def test_matching_debit_credit_pair():
    acct_a = uuid.uuid4()
    acct_b = uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a)
    credit = make_tx(5000, date(2026, 1, 16), acct_b)  # within 2 days

    mock_db = AsyncMock()

    async def fake_execute(q):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [credit]
        return mock_result

    mock_db.execute = fake_execute

    matcher = TransferMatcher(mock_db)
    result = await matcher._find_match(debit)
    assert result is not None
    assert result.id == credit.id


@pytest.mark.asyncio
async def test_no_match_different_amount():
    acct_a = uuid.uuid4()
    acct_b = uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a)

    mock_db = AsyncMock()

    async def fake_execute(q):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        return mock_result

    mock_db.execute = fake_execute

    matcher = TransferMatcher(mock_db)
    result = await matcher._find_match(debit)
    assert result is None
