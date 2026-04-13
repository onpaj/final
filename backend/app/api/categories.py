import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Category, CategoryGroup, Transaction, Rule, LlmClassification

router = APIRouter()


class CategoryOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    name: str
    is_income: bool
    is_ignored: bool
    is_system: bool
    color: str | None
    sort_order: int
    hint: str | None
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
    is_ignored: bool = False
    hint: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    is_income: bool | None = None
    is_ignored: bool | None = None
    hint: str | None = None


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
    cat_ids_result = await db.execute(select(Category.id).where(Category.group_id == group_id))
    cat_ids = cat_ids_result.scalars().all()
    if cat_ids:
        await db.execute(
            update(Transaction).where(Transaction.category_id.in_(cat_ids)).values(category_id=None, categorization_source=None)
        )
        await db.execute(
            update(LlmClassification).where(LlmClassification.suggested_category_id.in_(cat_ids)).values(suggested_category_id=None)
        )
        await db.execute(sql_delete(Rule).where(Rule.category_id.in_(cat_ids)))
        await db.execute(sql_delete(Category).where(Category.group_id == group_id))
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
    # NOTE: items are not validated to belong to the same group.
    # The frontend always sends same-group items; cross-group reorder may produce undefined sort_order overlap.
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


@router.delete("/all", status_code=204)
async def clear_all_categories(db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Transaction).values(category_id=None, categorization_source=None)
    )
    await db.execute(sql_delete(Rule))
    await db.execute(sql_delete(Category).where(Category.is_system == False))
    await db.commit()


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID,
    replacement_category_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    if cat.is_system:
        raise HTTPException(400, "System categories cannot be deleted")
    if replacement_category_id:
        replacement = await db.get(Category, replacement_category_id)
        if not replacement:
            raise HTTPException(404, "Replacement category not found")
        await db.execute(
            update(Transaction)
            .where(Transaction.category_id == category_id)
            .values(category_id=replacement_category_id)
        )
        await db.execute(
            update(LlmClassification)
            .where(LlmClassification.suggested_category_id == category_id)
            .values(suggested_category_id=replacement_category_id)
        )
    else:
        await db.execute(
            update(Transaction)
            .where(Transaction.category_id == category_id)
            .values(category_id=None, categorization_source=None)
        )
        await db.execute(
            update(LlmClassification)
            .where(LlmClassification.suggested_category_id == category_id)
            .values(suggested_category_id=None)
        )
    await db.execute(sql_delete(Rule).where(Rule.category_id == category_id))
    await db.delete(cat)
    await db.commit()
