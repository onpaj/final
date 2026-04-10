import uuid
from decimal import Decimal
from datetime import date
from app.services.import_service import ImportService
from app.services.parsers.base import TransactionRow


def make_row(**kwargs):
    defaults = dict(
        booking_date=date(2026, 1, 15),
        value_date=None,
        amount=Decimal("-250.00"),
        currency="CZK",
        counterparty_name="ALBERT",
        counterparty_account=None,
        description="Nákup",
        raw_reference="REF001",
    )
    return TransactionRow(**{**defaults, **kwargs})


def test_hash_key_is_deterministic():
    row = make_row()
    account_id = uuid.uuid4()
    h1 = ImportService.compute_hash_key(account_id, row)
    h2 = ImportService.compute_hash_key(account_id, row)
    assert h1 == h2


def test_hash_key_differs_for_different_amounts():
    account_id = uuid.uuid4()
    r1 = make_row(amount=Decimal("-100.00"))
    r2 = make_row(amount=Decimal("-200.00"))
    assert ImportService.compute_hash_key(account_id, r1) != ImportService.compute_hash_key(account_id, r2)


def test_hash_key_differs_for_different_accounts():
    row = make_row()
    assert ImportService.compute_hash_key(uuid.uuid4(), row) != ImportService.compute_hash_key(uuid.uuid4(), row)


def test_hash_key_differs_for_different_counterparties():
    account_id = uuid.uuid4()
    r1 = make_row(counterparty_name="ALBERT")
    r2 = make_row(counterparty_name="KAUFLAND")
    assert ImportService.compute_hash_key(account_id, r1) != ImportService.compute_hash_key(account_id, r2)
