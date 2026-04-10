import hashlib
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ImportBatch, Transaction
from app.services.parsers.base import TransactionRow


PARSER_REGISTRY: dict = {}  # populated when parsers are implemented (PartnersParser in Task 4)


@dataclass
class ImportResult:
    batch_id: uuid.UUID
    imported: int
    duplicates: int


class ImportService:

    @staticmethod
    def compute_hash_key(account_id: uuid.UUID, row: TransactionRow) -> str:
        raw = f"{account_id}|{row.booking_date}|{row.amount.normalize()}|{row.counterparty_name or ''}|{row.description or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _select_parser(bank: str):
        parser = PARSER_REGISTRY.get(bank)
        if parser is None:
            raise ValueError(f"No parser for bank '{bank}'. Use generic CSV mapper.")
        return parser

    @classmethod
    async def import_file(
        cls,
        db: AsyncSession,
        account: Account,
        file_bytes: bytes,
        filename: str,
    ) -> ImportResult:
        parser = cls._select_parser(account.bank)
        rows = parser.parse(file_bytes)

        batch = ImportBatch(
            account_id=account.id,
            filename=filename,
            parser_used=account.bank,
            row_count=len(rows),
            status="processing",
        )
        db.add(batch)
        await db.flush()  # get batch.id

        try:
            # Compute hash keys
            hash_map = {cls.compute_hash_key(account.id, row): row for row in rows}

            # Find existing duplicates
            existing_result = await db.execute(
                select(Transaction.hash_key).where(
                    Transaction.hash_key.in_(list(hash_map.keys()))
                )
            )
            existing_keys = {r[0] for r in existing_result.all()}

            new_rows = {k: v for k, v in hash_map.items() if k not in existing_keys}

            # Insert new transactions
            for hash_key, row in new_rows.items():
                tx = Transaction(
                    account_id=account.id,
                    import_batch_id=batch.id,
                    booking_date=row.booking_date,
                    value_date=row.value_date,
                    amount=row.amount,
                    currency=row.currency,
                    counterparty_name=row.counterparty_name,
                    counterparty_account=row.counterparty_account,
                    description=row.description,
                    raw_reference=row.raw_reference,
                    hash_key=hash_key,
                )
                db.add(tx)

            batch.imported_count = len(new_rows)
            batch.duplicate_count = len(rows) - len(new_rows)
            batch.status = "completed"

            await db.commit()
            return ImportResult(
                batch_id=batch.id,
                imported=batch.imported_count,
                duplicates=batch.duplicate_count,
            )
        except Exception as exc:
            batch.status = "failed"
            batch.error_message = str(exc)
            await db.commit()
            raise

    @classmethod
    async def get_batches(cls, db: AsyncSession) -> list[ImportBatch]:
        result = await db.execute(
            select(ImportBatch).order_by(ImportBatch.imported_at.desc())
        )
        return result.scalars().all()
