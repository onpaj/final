import csv
import io
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction
from app.db.session import get_db

router = APIRouter()


class TransactionOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    import_batch_id: uuid.UUID
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    counterparty_name: str | None
    counterparty_account: str | None
    description: str | None
    category_id: uuid.UUID | None
    categorization_source: str | None
    confidence: Decimal | None
    is_transfer: bool
    notes: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


@router.get("/export")
async def export_csv(
    account_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Transaction).order_by(Transaction.booking_date.desc())
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if date_from:
        q = q.where(Transaction.booking_date >= date_from)
    if date_to:
        q = q.where(Transaction.booking_date <= date_to)
    if category_id:
        q = q.where(Transaction.category_id == category_id)
    result = await db.execute(q)
    transactions = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "amount", "currency", "counterparty", "description",
                     "category_id", "source", "is_transfer"])
    for tx in transactions:
        writer.writerow([
            tx.booking_date, tx.amount, tx.currency,
            tx.counterparty_name or "", tx.description or "",
            tx.category_id or "", tx.categorization_source or "",
            tx.is_transfer,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    account_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    needs_review: bool | None = Query(None),
    is_transfer: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[TransactionOut]:
    query = select(Transaction)

    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if date_from is not None:
        query = query.where(Transaction.booking_date >= date_from)
    if date_to is not None:
        query = query.where(Transaction.booking_date <= date_to)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if needs_review is True:
        query = query.where(Transaction.category_id.is_(None))
        query = query.where(Transaction.is_transfer.is_(False))
    if is_transfer is not None:
        query = query.where(Transaction.is_transfer.is_(is_transfer))

    query = query.order_by(Transaction.booking_date.desc(), Transaction.id.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


class BulkCategorizeRequest(BaseModel):
    transaction_ids: Annotated[list[uuid.UUID], Field(min_length=1)]
    category_id: uuid.UUID


@router.patch("/bulk-categorize", status_code=204)
async def bulk_categorize(body: BulkCategorizeRequest, db: AsyncSession = Depends(get_db)):
    await db.execute(
        Transaction.__table__.update()
        .where(Transaction.id.in_(body.transaction_ids))
        .values(
            category_id=body.category_id,
            categorization_source="manual",
            confidence=None,
        )
    )
    await db.commit()
