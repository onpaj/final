import re
import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Category, Transaction
from app.services.iban_utils import account_identifiers, normalize_iban, normalize_local_cz

_IBAN_PREFIX_RE = re.compile(r'^[A-Za-z]{2}\d{2}')


class TransferMatcher:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._internal_transfer_category_id: uuid.UUID | None = None
        self._account_identifiers: dict[uuid.UUID, set[str]] = {}
        # flat map: normalized identifier -> account_id
        self._identifier_to_account: dict[str, uuid.UUID] = {}

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
        self._identifier_to_account = {
            ident: acct_id
            for acct_id, identifiers in self._account_identifiers.items()
            for ident in identifiers
        }

    def _normalize_counterparty(self, value: str | None) -> str | None:
        if not value:
            return None
        stripped = value.strip()
        if _IBAN_PREFIX_RE.match(stripped):
            return normalize_iban(stripped)
        return normalize_local_cz(stripped)

    async def _find_partner(self, txn: Transaction, counterparty_account_id: uuid.UUID) -> Transaction | None:
        """Find an already-imported but unmatched transaction on the counterparty account
        whose counterparty points back to txn's account."""
        if txn.account_id not in self._account_identifiers:
            return None
        own_identifiers = self._account_identifiers[txn.account_id]
        result = await self._db.execute(
            select(Transaction).where(
                and_(
                    Transaction.account_id == counterparty_account_id,
                    Transaction.categorization_source.is_(None),
                )
            )
        )
        candidates = result.scalars().all()
        for candidate in candidates:
            cp = self._normalize_counterparty(candidate.counterparty_account)
            if cp in own_identifiers:
                return candidate
        return None

    async def match_batch(self, transaction_ids: list[uuid.UUID]) -> int:
        await self._load_account_identifiers()

        result = await self._db.execute(
            select(Transaction).where(
                Transaction.id.in_(transaction_ids),
                Transaction.categorization_source.is_(None),
            )
        )
        transactions = result.scalars().all()

        internal_cat_id = await self._get_internal_transfer_category()
        matched = 0
        for txn in transactions:
            counterparty = self._normalize_counterparty(txn.counterparty_account)
            if not counterparty:
                continue
            counterparty_account_id = self._identifier_to_account.get(counterparty)
            if counterparty_account_id is None:
                continue

            partner = await self._find_partner(txn, counterparty_account_id)
            pair_id = (partner.transfer_pair_id if partner and partner.transfer_pair_id else None) or uuid.uuid4()

            txn.categorization_source = "transfer"
            txn.transfer_pair_id = pair_id
            txn.category_id = internal_cat_id

            if partner:
                partner.categorization_source = "transfer"
                partner.transfer_pair_id = pair_id
                partner.category_id = internal_cat_id

            matched += 1

        await self._db.commit()
        return matched
