import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Account

router = APIRouter()

class AccountCreate(BaseModel):
    name: str
    bank: str
    currency: str = "CZK"
    iban: str | None = None

class AccountUpdate(BaseModel):
    name: str | None = None
    bank: str | None = None
    currency: str | None = None
    iban: str | None = None
    is_active: bool | None = None

class AccountOut(BaseModel):
    id: uuid.UUID
    name: str
    bank: str
    currency: str
    iban: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

@router.get("", response_model=list[AccountOut])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.is_active.is_(True)))
    return result.scalars().all()

@router.post("", response_model=AccountOut, status_code=201)
async def create_account(body: AccountCreate, db: AsyncSession = Depends(get_db)):
    account = Account(**body.model_dump())
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account

@router.get("/{account_id}", response_model=AccountOut)
async def get_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(account_id: uuid.UUID, body: AccountUpdate, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return account

@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_active = False
    await db.commit()
