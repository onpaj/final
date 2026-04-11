import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Category, CategoryGroup

router = APIRouter()

class CategoryOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    name: str
    slug: str | None = None
    is_income: bool
    is_system: bool
    color: str | None
    model_config = {"from_attributes": True}

class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str | None = None
    color: str | None
    sort_order: int
    categories: list[CategoryOut]
    model_config = {"from_attributes": True}

GroupOut.model_rebuild()

@router.get("/groups", response_model=list[GroupOut])
async def list_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CategoryGroup).order_by(CategoryGroup.sort_order)
    )
    groups = result.scalars().all()
    for g in groups:
        await db.refresh(g, ["categories"])
    return groups

@router.get("", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return result.scalars().all()
