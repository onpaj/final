import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ImportBatch, Transaction
from app.services.parsers.base import TransactionRow
from app.services.parsers.generic_csv import GenericCsvParser
from app.services.parsers.partners import PartnersParser



class ImportService:

    @staticmethod
    def compute_hash_key(account_id: uuid.UUID, row: TransactionRow) -> str:
        raw = f"{account_id}|{row.booking_date}|{row.amount.normalize()}|{row.counterparty_name or ''}|{row.description or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    async def process_batch(
        db: AsyncSession,
        batch: ImportBatch,
        account: Account,
        file_bytes: bytes,
        column_mapping: dict | None = None,
    ) -> None:
        """Parse and insert transactions into an existing batch. Updates batch status in-place."""
        imported = 0
        duplicates = 0
        new_ids = []
        try:
            if account.bank == "partners":
                rows = PartnersParser().parse(file_bytes)
            else:
                if not column_mapping:
                    column_mapping = batch.column_mapping
                if not column_mapping:
                    batch.status = "failed"
                    batch.error_message = "column_mapping required for generic CSV accounts"
                    await db.commit()
                    return
                rows = GenericCsvParser.parse(file_bytes, column_mapping)
                if not batch.column_mapping:
                    batch.column_mapping = column_mapping
            batch.row_count = len(rows)
            for row in rows:
                hash_key = ImportService.compute_hash_key(batch.account_id, row)
                exists = await db.execute(
                    select(Transaction).where(Transaction.hash_key == hash_key)
                )
                if exists.scalar_one_or_none():
                    duplicates += 1
                    continue
                tx = Transaction(
                    account_id=batch.account_id,
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
                await db.flush()
                new_ids.append(tx.id)
                imported += 1
            batch.imported_count = imported
            batch.duplicate_count = duplicates
            batch.status = "completed"
            await db.commit()
        except Exception as exc:
            batch.status = "failed"
            batch.error_message = str(exc)
            await db.commit()
            return

        # Categorization is OUTSIDE the try/except — its failures don't affect batch status
        if new_ids:
            from app.services.categorization_service import CategorizationService
            cat_service = CategorizationService(db)
            await cat_service.run_batch(new_ids)
