import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ImportBatch
from app.db.session import AsyncSessionLocal, get_db
from app.services.import_service import ImportService

router = APIRouter()


class ImportInitiated(BaseModel):
    batch_id: uuid.UUID
    message: str


class BatchOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    filename: str
    parser_used: str
    row_count: int
    imported_count: int
    duplicate_count: int
    status: str
    error_message: str | None
    imported_at: datetime
    model_config = {"from_attributes": True}


async def _run_import(batch_id: uuid.UUID, file_bytes: bytes) -> None:
    async with AsyncSessionLocal() as db:
        batch = await db.get(ImportBatch, batch_id)
        if not batch:
            return
        account = await db.get(Account, batch.account_id)
        if not account:
            batch.status = "failed"
            batch.error_message = "Account not found"
            await db.commit()
            return
        await ImportService.process_batch(db, batch, account, file_bytes)


@router.post("", response_model=ImportInitiated, status_code=202)
async def start_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    account_id: uuid.UUID = Form(...),
    db: AsyncSession = Depends(get_db),
) -> ImportInitiated:
    account = await db.get(Account, account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=404, detail="Account not found")

    file_bytes = await file.read()
    filename = file.filename or "upload.csv"
    parser_key = account.bank

    batch = ImportBatch(
        account_id=account_id,
        filename=filename,
        parser_used=parser_key,
        status="processing",
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    background_tasks.add_task(_run_import, batch.id, file_bytes)
    return ImportInitiated(batch_id=batch.id, message="Import started")


@router.get("", response_model=list[BatchOut])
async def list_imports(
    account_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[BatchOut]:
    query = select(ImportBatch).order_by(ImportBatch.imported_at.desc())
    if account_id is not None:
        query = query.where(ImportBatch.account_id == account_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{batch_id}", response_model=BatchOut)
async def get_import(batch_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> BatchOut:
    batch = await db.get(ImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    return batch
