import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Transaction
from app.services.categorization_service import CategorizationService

router = APIRouter()

class RecategorizeRequest(BaseModel):
    transaction_ids: list[uuid.UUID] | None = None  # None = all uncategorized

class RecategorizeResult(BaseModel):
    categorized: int
    needs_review: int

@router.post("/batch", response_model=RecategorizeResult)
async def recategorize_batch(body: RecategorizeRequest, db: AsyncSession = Depends(get_db)):
    if body.transaction_ids:
        ids = body.transaction_ids
    else:
        result = await db.execute(
            select(Transaction.id).where(Transaction.category_id == None)
        )
        ids = [r[0] for r in result.all()]
    service = CategorizationService(db)
    return await service.run_batch(ids)
