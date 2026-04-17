import csv
import io
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Category, LlmClassification, Rule, Transaction
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
    notes: str | None
    created_at: datetime
    llm_status: Literal["no_rule_no_llm", "llm_rejected", "llm_error"] | None = None
    llm_confidence: Decimal | None = None
    model_config = {"from_attributes": True}


class AccountRef(BaseModel):
    id: uuid.UUID
    name: str
    iban: str | None
    model_config = {"from_attributes": True}


class CategoryRef(BaseModel):
    id: uuid.UUID
    name: str
    model_config = {"from_attributes": True}


class RuleRef(BaseModel):
    id: uuid.UUID
    name: str
    model_config = {"from_attributes": True}


class TransferPairOut(BaseModel):
    id: uuid.UUID
    amount: Decimal
    booking_date: date
    account: AccountRef
    model_config = {"from_attributes": True}


class TransactionDetailOut(BaseModel):
    id: uuid.UUID
    booking_date: date
    value_date: date | None
    amount: Decimal
    currency: str
    counterparty_name: str | None
    counterparty_account: str | None
    description: str | None
    raw_reference: str | None
    transfer_pair_id: uuid.UUID | None
    categorization_source: str | None
    confidence: Decimal | None
    created_at: datetime
    import_batch_id: uuid.UUID
    account: AccountRef
    category: CategoryRef | None
    applied_rule: RuleRef | None
    transfer_pair: TransferPairOut | None
    model_config = {"from_attributes": True}


@router.get("/export")
async def export_csv(
    account_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    needs_review: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Transaction).order_by(Transaction.booking_date.desc(), Transaction.id.desc())
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if date_from:
        q = q.where(Transaction.booking_date >= date_from)
    if date_to:
        q = q.where(Transaction.booking_date <= date_to)
    if category_id is not None:
        q = q.where(Transaction.category_id == category_id)
    if needs_review is True:
        q = q.where(Transaction.category_id.is_(None))
        q = q.where(
            (Transaction.categorization_source.is_(None)) |
            (Transaction.categorization_source != "transfer")
        )
    result = await db.execute(q)
    transactions = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "amount", "currency", "counterparty", "description",
                     "category_id", "source"])
    for tx in transactions:
        writer.writerow([
            tx.booking_date, tx.amount, tx.currency,
            tx.counterparty_name or "", tx.description or "",
            tx.category_id or "", tx.categorization_source or "",
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
    categorization_source: str | None = Query(None),
    include_llm_status: bool = Query(False),
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
        query = query.where(
            (Transaction.categorization_source.is_(None)) |
            (Transaction.categorization_source != "transfer")
        )
    if categorization_source is not None:
        if categorization_source == "none":
            query = query.where(Transaction.categorization_source.is_(None))
        else:
            query = query.where(Transaction.categorization_source == categorization_source)

    query = query.order_by(Transaction.booking_date.desc(), Transaction.id.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    transactions = result.scalars().all()

    if not include_llm_status:
        return transactions  # type: ignore[return-value]

    # Fetch the most recent LlmClassification per transaction (second query, merged in Python)
    tx_ids = [tx.id for tx in transactions]
    classifications: dict[uuid.UUID, LlmClassification] = {}
    if tx_ids:
        cls_result = await db.execute(
            select(LlmClassification)
            .where(LlmClassification.transaction_id.in_(tx_ids))
            .order_by(LlmClassification.transaction_id, LlmClassification.created_at.desc())
            .distinct(LlmClassification.transaction_id)
        )
        for cls in cls_result.scalars().all():
            classifications[cls.transaction_id] = cls

    out: list[TransactionOut] = []
    for tx in transactions:
        tx_out = TransactionOut.model_validate(tx)
        cls = classifications.get(tx.id)
        if cls is None:
            tx_out.llm_status = "no_rule_no_llm"
        elif cls.reasoning == "error":
            tx_out.llm_status = "llm_error"
        else:
            tx_out.llm_status = "llm_rejected"
            tx_out.llm_confidence = cls.confidence
        out.append(tx_out)

    return out


class BulkCategorizeRequest(BaseModel):
    transaction_ids: Annotated[list[uuid.UUID], Field(min_length=1)]
    category_id: uuid.UUID | None


@router.patch("/bulk-categorize", status_code=204)
async def bulk_categorize(body: BulkCategorizeRequest, db: AsyncSession = Depends(get_db)):
    if body.category_id is not None:
        values = dict(
            category_id=body.category_id,
            categorization_source="manual",
            confidence=None,
        )
        await db.execute(
            Transaction.__table__.update()
            .where(Transaction.id.in_(body.transaction_ids))
            .values(**values)
        )
    else:
        # Collect transfer_pair_ids before clearing so we can reset the paired side too
        pair_result = await db.execute(
            select(Transaction.transfer_pair_id)
            .where(Transaction.id.in_(body.transaction_ids))
            .where(Transaction.transfer_pair_id.is_not(None))
        )
        pair_ids = [row[0] for row in pair_result.all()]

        await db.execute(
            Transaction.__table__.update()
            .where(Transaction.id.in_(body.transaction_ids))
            .values(
                category_id=None,
                categorization_source=None,
                confidence=None,
                transfer_pair_id=None,
            )
        )

        if pair_ids:
            await db.execute(
                Transaction.__table__.update()
                .where(Transaction.id.in_(pair_ids))
                .values(
                    category_id=None,
                    categorization_source=None,
                    confidence=None,
                    transfer_pair_id=None,
                )
            )
    await db.commit()


@router.get("/{transaction_id}/details", response_model=TransactionDetailOut)
async def get_transaction_details(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TransactionDetailOut:
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    tx = result.scalars().first()
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    result = await db.execute(select(Account).where(Account.id == tx.account_id))
    account = result.scalars().first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found for transaction")

    category = None
    if tx.category_id is not None:
        result = await db.execute(select(Category).where(Category.id == tx.category_id))
        category = result.scalars().first()

    applied_rule = None
    if tx.applied_rule_id is not None:
        result = await db.execute(select(Rule).where(Rule.id == tx.applied_rule_id))
        applied_rule = result.scalars().first()

    transfer_pair = None
    if tx.categorization_source == "transfer" and tx.transfer_pair_id is not None:
        result = await db.execute(select(Transaction).where(Transaction.id == tx.transfer_pair_id))
        pair_tx = result.scalars().first()
        if pair_tx is not None:
            result = await db.execute(select(Account).where(Account.id == pair_tx.account_id))
            pair_account = result.scalars().first()
            if pair_account is None:
                raise HTTPException(status_code=404, detail="Account not found for transfer pair")
            transfer_pair = TransferPairOut(
                id=pair_tx.id,
                amount=pair_tx.amount,
                booking_date=pair_tx.booking_date,
                account=AccountRef(
                    id=pair_account.id,
                    name=pair_account.name,
                    iban=pair_account.iban,
                ),
            )

    return TransactionDetailOut(
        id=tx.id,
        booking_date=tx.booking_date,
        value_date=tx.value_date,
        amount=tx.amount,
        currency=tx.currency,
        counterparty_name=tx.counterparty_name,
        counterparty_account=tx.counterparty_account,
        description=tx.description,
        raw_reference=tx.raw_reference,
        transfer_pair_id=tx.transfer_pair_id,
        categorization_source=tx.categorization_source,
        confidence=tx.confidence,
        created_at=tx.created_at,
        import_batch_id=tx.import_batch_id,
        account=AccountRef(id=account.id, name=account.name, iban=account.iban),
        category=CategoryRef(id=category.id, name=category.name) if category else None,
        applied_rule=RuleRef(id=applied_rule.id, name=applied_rule.name) if applied_rule else None,
        transfer_pair=transfer_pair,
    )
