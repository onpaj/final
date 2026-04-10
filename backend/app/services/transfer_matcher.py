import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Category, Transaction

AMOUNT_TOLERANCE = Decimal("0.01")
DATE_TOLERANCE_DAYS = 2


class TransferMatcher:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._internal_transfer_category_id: uuid.UUID | None = None

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

    async def _find_match(self, debit: Transaction) -> Transaction | None:
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
                    Transaction.is_transfer == False,
                )
            )
        )
        candidates = result.scalars().all()
        return candidates[0] if candidates else None

    async def match_batch(self, transaction_ids: list[uuid.UUID]) -> int:
        result = await self._db.execute(
            select(Transaction).where(
                Transaction.id.in_(transaction_ids),
                Transaction.amount < 0,
                Transaction.is_transfer == False,
            )
        )
        debits = result.scalars().all()

        internal_cat_id = await self._get_internal_transfer_category()
        matched = 0
        for debit in debits:
            credit = await self._find_match(debit)
            if credit:
                pair_id = uuid.uuid4()
                debit.is_transfer = True
                debit.transfer_pair_id = pair_id
                debit.category_id = internal_cat_id
                credit.is_transfer = True
                credit.transfer_pair_id = pair_id
                credit.category_id = internal_cat_id
                matched += 1

        await self._db.commit()
        return matched
