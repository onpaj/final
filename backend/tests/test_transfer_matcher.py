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
    tx.categorization_source = None
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
    matcher._identifier_to_account = {
        ident: acct_a for ident in account_identifiers(iban_a)
    } | {
        ident: acct_b for ident in account_identifiers(iban_b)
    }
    return matcher


def _make_match_batch_mock_db(acct_a, acct_b, transactions, partner_candidates, internal_cat_id):
    """Build a mock_db for match_batch tests."""
    cat = MagicMock()
    cat.id = internal_cat_id

    call_count = 0

    async def mock_execute(query):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # _load_account_identifiers
            acc_a = MagicMock(); acc_a.id = acct_a; acc_a.iban = IBAN_A
            acc_b = MagicMock(); acc_b.id = acct_b; acc_b.iban = IBAN_B
            return MagicMock(**{"scalars.return_value.all.return_value": [acc_a, acc_b]})
        elif call_count == 2:  # fetch transactions from batch
            return MagicMock(**{"scalars.return_value.all.return_value": transactions})
        elif call_count == 3:  # _get_internal_transfer_category
            return MagicMock(scalar_one_or_none=MagicMock(return_value=cat))
        else:  # _find_partner queries (one per matched transaction)
            return MagicMock(**{"scalars.return_value.all.return_value": partner_candidates})

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=mock_execute)
    mock_db.commit = AsyncMock()
    return mock_db


# --- IBAN <-> IBAN ---

@pytest.mark.asyncio
async def test_match_iban_to_iban():
    """Debit with IBAN counterparty pointing to a known account is marked as transfer."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    internal_cat_id = uuid.uuid4()
    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [debit], [credit], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([debit.id])

    assert matched == 1
    assert debit.categorization_source == "transfer"
    assert debit.category_id == internal_cat_id
    assert debit.transfer_pair_id is not None
    assert credit.categorization_source == "transfer"
    assert debit.transfer_pair_id == credit.transfer_pair_id


# --- IBAN <-> local (cross-format) ---

@pytest.mark.asyncio
async def test_match_iban_to_local():
    """Counterparty in IBAN format matches account registered under local CZ format."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    # debit on acct_a, counterparty is IBAN_B
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account="1234567/0300")

    internal_cat_id = uuid.uuid4()
    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [debit], [credit], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([debit.id])

    assert matched == 1
    assert debit.categorization_source == "transfer"
    assert credit.categorization_source == "transfer"
    assert debit.transfer_pair_id == credit.transfer_pair_id


# --- local <-> local ---

@pytest.mark.asyncio
async def test_match_local_to_local():
    """Both sides use local CZ format for counterparty."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account="19-2000145399/0800")
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account="1234567/0300")

    internal_cat_id = uuid.uuid4()
    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [debit], [credit], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([debit.id])

    assert matched == 1
    assert debit.categorization_source == "transfer"
    assert credit.categorization_source == "transfer"


# --- Amount and date do NOT matter ---

@pytest.mark.asyncio
async def test_different_amounts_still_match():
    """Transactions are matched as transfers even when amounts differ."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(4999, date(2026, 1, 15), acct_b, counterparty_account=IBAN_A)

    internal_cat_id = uuid.uuid4()
    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [debit], [credit], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([debit.id])

    assert matched == 1
    assert debit.categorization_source == "transfer"


@pytest.mark.asyncio
async def test_far_apart_dates_still_match():
    """Transactions are matched as transfers regardless of date difference."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    debit = make_tx(-5000, date(2026, 1, 1), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 3, 31), acct_b, counterparty_account=IBAN_A)

    internal_cat_id = uuid.uuid4()
    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [debit], [credit], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([debit.id])

    assert matched == 1
    assert debit.categorization_source == "transfer"


# --- No match cases ---

@pytest.mark.asyncio
async def test_no_match_external_counterparty():
    """Transaction with a counterparty that is NOT a known account is not a transfer."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    external_iban = "CZ6503000000000009999999"
    txn = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=external_iban)

    internal_cat_id = uuid.uuid4()
    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [txn], [], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([txn.id])

    assert matched == 0
    assert txn.categorization_source is None


@pytest.mark.asyncio
async def test_no_match_null_counterparty():
    """Transaction with no counterparty_account is not a transfer."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    txn = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=None)

    internal_cat_id = uuid.uuid4()
    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [txn], [], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([txn.id])

    assert matched == 0
    assert txn.categorization_source is None


# --- One side imported, other side missing ---

@pytest.mark.asyncio
async def test_credit_only_still_marked_as_transfer():
    """Credit transaction is marked as transfer even without a matching debit in DB."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    credit = make_tx(286, date(2026, 3, 31), acct_a, counterparty_account=IBAN_B)

    internal_cat_id = uuid.uuid4()
    # No partner found in DB
    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [credit], [], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([credit.id])

    assert matched == 1
    assert credit.categorization_source == "transfer"
    assert credit.category_id == internal_cat_id
    assert credit.transfer_pair_id is not None


# --- match_batch sets categorization_source and pair_id ---

@pytest.mark.asyncio
async def test_match_batch_sets_categorization_source():
    """match_batch sets categorization_source='transfer' on both sides."""
    acct_a, acct_b = uuid.uuid4(), uuid.uuid4()
    internal_cat_id = uuid.uuid4()

    debit = make_tx(-5000, date(2026, 1, 15), acct_a, counterparty_account=IBAN_B)
    credit = make_tx(5000, date(2026, 1, 16), acct_b, counterparty_account=IBAN_A)

    mock_db = _make_match_batch_mock_db(acct_a, acct_b, [debit, credit], [credit], internal_cat_id)

    matcher = TransferMatcher(mock_db)
    matched = await matcher.match_batch([debit.id, credit.id])

    assert matched >= 1
    assert debit.categorization_source == "transfer"
    assert debit.category_id == internal_cat_id
    assert debit.transfer_pair_id is not None
