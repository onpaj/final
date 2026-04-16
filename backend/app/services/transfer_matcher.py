import re
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Category, Transaction
from app.services.iban_utils import account_identifiers, normalize_iban, normalize_local_cz

AMOUNT_TOLERANCE = Decimal("0.01")
DATE_TOLERANCE_DAYS = 2

_IBAN_PREFIX_RE = re.compile(r'^[A-Za-z]{2}\d{2}')


class TransferMatcher:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._internal_transfer_category_id: uuid.UUID | None = None
        self._account_identifiers: dict[uuid.UUID, set[str]] = {}

    async def _get_internal_transfer_category(self) -> uuid.UUID | None:
        if self._internal_transfer_category_id:
            return self._internal_transfer_category_id
        result = await self._db.execute(
            select(Category).where(Category.name == "Internal Transfer", Category.is_system == True)
        )
        cat = result.scalar_one_or_none()
        if cat:
            self._internal_transfer_category_id = cat.id
        return self._internal_transfer_category_id

    async def _load_account_identifiers(self) -> None:
        result = await self._db.execute(
            select(Account).where(Account.iban.isnot(None))
        )
        accounts = result.scalars().all()
        self._account_identifiers = {
            acct.id: account_identifiers(acct.iban)
            for acct in accounts
        }

    def _normalize_counterparty(self, value: str | None) -> str | None:
        if not value:
            return None
        stripped = value.strip()
        if _IBAN_PREFIX_RE.match(stripped):
            return normalize_iban(stripped)
        return normalize_local_cz(stripped)

    async def _find_match(self, debit: Transaction) -> Transaction | None:
        if debit.account_id not in self._account_identifiers:
            return None

        debit_abs = abs(debit.amount)
        date_min = debit.booking_date - timedelta(days=DATE_TOLERANCE_DAYS)
        date_max = debit.booking_date + timedelta(days=DATE_TOLERANCE_DAYS)
        result = await self._db.execute(
            select(Transaction).where(
                and_(
                    Transaction.account_id != debit.account_id,
                    Transaction.amount >= debit_abs - AMOUNT_TOLERANCE,
                    Transaction.amount <= debit_abs + AMOUNT_TOLERANCE,
                    Transaction.booking_date >= date_min,
                    Transaction.booking_date <= date_max,
                    Transaction.categorization_source.is_(None),
                )
            )
        )
        candidates = result.scalars().all()

        debit_identifiers = self._account_identifiers[debit.account_id]

        for credit in candidates:
            if credit.account_id not in self._account_identifiers:
                continue
            credit_identifiers = self._account_identifiers[credit.account_id]

            debit_counterparty = self._normalize_counterparty(debit.counterparty_account)
            if debit_counterparty not in credit_identifiers:
                continue

            credit_counterparty = self._normalize_counterparty(credit.counterparty_account)
            if credit_counterparty not in debit_identifiers:
                continue

            return credit

        return None

    async def match_batch(self, transaction_ids: list[uuid.UUID]) -> int:
        await self._load_account_identifiers()

        result = await self._db.execute(
            select(Transaction).where(
                Transaction.id.in_(transaction_ids),
                Transaction.amount < 0,
                Transaction.categorization_source.is_(None),
            )
        )
        debits = result.scalars().all()

        internal_cat_id = await self._get_internal_transfer_category()
        matched = 0
        for debit in debits:
            credit = await self._find_match(debit)
            if credit:
                pair_id = uuid.uuid4()
                debit.categorization_source = "transfer"
                debit.transfer_pair_id = pair_id
                debit.category_id = internal_cat_id
                credit.categorization_source = "transfer"
                credit.transfer_pair_id = pair_id
                credit.category_id = internal_cat_id
                matched += 1

        await self._db.commit()
        return matched
