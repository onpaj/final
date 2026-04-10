import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ImportBatch, Transaction
from app.services.parsers.base import TransactionRow
from app.services.parsers.partners import PartnersParser


PARSER_REGISTRY: dict = {
    "partners": PartnersParser,
}


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
    ) -> None:
        """Parse and insert transactions into an existing batch. Updates batch status in-place."""
        parser_cls = PARSER_REGISTRY.get(batch.parser_used)
        if parser_cls is None:
            batch.status = "failed"
            batch.error_message = f"No parser for file type: {batch.parser_used}"
            await db.commit()
            return

        imported = 0
        duplicates = 0
        try:
            parser = parser_cls()
            rows = parser.parse(file_bytes)
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
                imported += 1
            batch.imported_count = imported
            batch.duplicate_count = duplicates
            batch.status = "completed"
        except Exception as exc:
            batch.status = "failed"
            batch.error_message = str(exc)
        await db.commit()
