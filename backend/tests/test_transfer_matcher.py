import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.services.iban_utils import account_identifiers
from app.services.transfer_matcher import TransferMatcher

IBAN_A = "CZ6503000000000001234567"  # bank=0300, account=1234567, no prefix
IBAN_B = "CZ6508000000192000145399"  # bank=0800, account=2000145399, prefix=19


def make_tx(amount, booking_date, account_id=None, tx_id=None, counterparty_account=None):
    tx = MagicMock()
    tx.id = tx_id or uuid.uuid4()
    tx.amount = Decimal(str(amount))
    tx.booking_date = booking_date
    tx.account_id = account_id or uuid.uuid4()
    tx.is_transfer = False
    tx.transfer_pair_id = None
    tx.category_id = None
    tx.counterparty_account = counterparty_account
    return tx


def make_matcher_with_accounts(mock_db, acct_a, iban_a, acct_b, iban_b):
    matcher = TransferMatcher(mock_db)
    matcher._account_identifiers = {
        acct_a: account_identifiers(iban_a),
        acct_b: account_identifiers(iban_b),
    }
    return matcher


# --- IBAN <-> IBAN ---

@pytest.mark.asyncio
async def test_match_iban_to_iban():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is not None
    assert result.id == credit.id


# --- IBAN <-> local (cross-format) ---

@pytest.mark.asyncio
async def test_match_iban_to_local():
    # Debit side exports IBAN for counterparty, credit side exports local format
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account="1234567/0300")

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is not None
    assert result.id == credit.id


# --- local <-> local ---

@pytest.mark.asyncio
async def test_match_local_to_local():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account="19-2000145399/0800")
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account="1234567/0300")

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is not None
    assert result.id == credit.id


# --- No match: debit account has no IBAN ---

@pytest.mark.asyncio
async def test_no_match_debit_account_has_no_iban():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = TransferMatcher(mock_db)
    # Only acct_b has IBAN, acct_a does not
    matcher._account_identifiers = {acct_b: account_identifiers(IBAN_B)}
    result = await matcher._find_match(debit)
    assert result is None


# --- No match: credit account has no IBAN ---

@pytest.mark.asyncio
async def test_no_match_credit_account_has_no_iban():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = TransferMatcher(mock_db)
    # Only acct_a has IBAN, acct_b does not
    matcher._account_identifiers = {acct_a: account_identifiers(IBAN_A)}
    result = await matcher._find_match(debit)
    assert result is None


# --- No match: counterparty points to wrong account ---

@pytest.mark.asyncio
async def test_no_match_wrong_counterparty_account():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    wrong_iban = "CZ6503000000000009999999"
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=wrong_iban)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is None


# --- No match: counterparty_account is None ---

@pytest.mark.asyncio
async def test_no_match_null_counterparty_account():
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=None)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": [credit]}
    ))

    matcher = make_matcher_with_accounts(mock_db, acct_a, IBAN_A, acct_b, IBAN_B)
    result = await matcher._find_match(debit)
    assert result is None


# --- No match: amount mismatch (empty candidate list from DB) ---

@pytest.mark.asyncio
async def test_no_match_different_amount():
    acct_a = uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=MagicMock(
        **{"scalars.return_value.all.return_value": []}
    ))

    matcher = TransferMatcher(mock_db)
    matcher._account_identifiers = {acct_a: account_identifiers(IBAN_A)}
    result = await matcher._find_match(debit)
    assert result is None
