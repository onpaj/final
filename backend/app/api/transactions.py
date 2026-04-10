import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
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
    transaction_ids: list[uuid.UUID]
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
