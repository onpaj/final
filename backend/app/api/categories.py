import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Category, CategoryGroup

router = APIRouter()


class CategoryOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    name: str
    is_income: bool
    is_system: bool
    color: str | None
    sort_order: int
    model_config = {"from_attributes": True}


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    color: str | None
    sort_order: int
    categories: list[CategoryOut]
    model_config = {"from_attributes": True}


GroupOut.model_rebuild()


class GroupCreate(BaseModel):
    name: str
    color: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class CategoryCreate(BaseModel):
    group_id: uuid.UUID
    name: str
    color: str | None = None
    is_income: bool = False


class CategoryUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    is_income: bool | None = None


class ReorderItem(BaseModel):
    id: uuid.UUID
    sort_order: int


# ── Group routes ─────────────────────────────────────────────────────────────

@router.get("/groups", response_model=list[GroupOut])
async def list_groups(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CategoryGroup).order_by(CategoryGroup.sort_order))
    groups = result.scalars().all()
    for g in groups:
        await db.refresh(g, ["categories"])
    return groups


@router.post("/groups", response_model=GroupOut, status_code=201)
async def create_group(body: GroupCreate, db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(select(func.count()).select_from(CategoryGroup))
    count = count_result.scalar() or 0
    group = CategoryGroup(**body.model_dump(), sort_order=count)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    await db.refresh(group, ["categories"])
    return group


# NOTE: /groups/reorder must be defined before /groups/{group_id}
@router.patch("/groups/reorder", response_model=list[GroupOut])
async def reorder_groups(items: list[ReorderItem], db: AsyncSession = Depends(get_db)):
    for item in items:
        group = await db.get(CategoryGroup, item.id)
        if group:
            group.sort_order = item.sort_order
    await db.commit()
    result = await db.execute(select(CategoryGroup).order_by(CategoryGroup.sort_order))
    groups = result.scalars().all()
    for g in groups:
        await db.refresh(g, ["categories"])
    return groups


@router.patch("/groups/{group_id}", response_model=GroupOut)
async def update_group(group_id: uuid.UUID, body: GroupUpdate, db: AsyncSession = Depends(get_db)):
    group = await db.get(CategoryGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(group, f, v)
    await db.commit()
    await db.refresh(group)
    await db.refresh(group, ["categories"])
    return group


@router.delete("/groups/{group_id}", status_code=204)
async def delete_group(group_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    group = await db.get(CategoryGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    await db.delete(group)
    await db.commit()


# ── Category routes ───────────────────────────────────────────────────────────

@router.get("", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return result.scalars().all()


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    count_result = await db.execute(
        select(func.count()).select_from(Category).where(Category.group_id == body.group_id)
    )
    count = count_result.scalar() or 0
    category = Category(**body.model_dump(), sort_order=count)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# NOTE: /reorder must be defined before /{category_id}
@router.patch("/reorder", response_model=list[CategoryOut])
async def reorder_categories(items: list[ReorderItem], db: AsyncSession = Depends(get_db)):
    for item in items:
        cat = await db.get(Category, item.id)
        if cat:
            cat.sort_order = item.sort_order
    await db.commit()
    result = await db.execute(select(Category).order_by(Category.sort_order))
    return result.scalars().all()


@router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(category_id: uuid.UUID, body: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(cat, f, v)
    await db.commit()
    await db.refresh(cat)
    return cat


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    await db.delete(cat)
    await db.commit()
