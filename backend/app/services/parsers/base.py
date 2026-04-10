from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class TransactionRow:
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    counterparty_name: str | None
    counterparty_account: str | None
    description: str | None
    raw_reference: str | None
