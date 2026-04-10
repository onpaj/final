import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Rule

router = APIRouter()

class RuleCreate(BaseModel):
    name: str
    priority: int = 100
    match_type: str
    match_value: dict
    category_id: uuid.UUID

class RuleUpdate(BaseModel):
    name: str | None = None
    priority: int | None = None
    match_type: str | None = None
    match_value: dict | None = None
    category_id: uuid.UUID | None = None
    enabled: bool | None = None

class RuleOut(BaseModel):
    id: uuid.UUID
    name: str
    priority: int
    match_type: str
    match_value: dict
    category_id: uuid.UUID
    enabled: bool
    hit_count: int
    model_config = {"from_attributes": True}

@router.get("", response_model=list[RuleOut])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).order_by(Rule.priority.desc()))
    return result.scalars().all()

@router.post("", response_model=RuleOut, status_code=201)
async def create_rule(body: RuleCreate, db: AsyncSession = Depends(get_db)):
    rule = Rule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.patch("/{rule_id}", response_model=RuleOut)
async def update_rule(rule_id: uuid.UUID, body: RuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(rule, f, v)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()
