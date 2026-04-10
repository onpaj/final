import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ImportBatch
from app.db.session import AsyncSessionLocal, get_db
from app.services.import_service import ImportService

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "uploads"

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


async def _run_import(batch_id: uuid.UUID, file_bytes: bytes, column_mapping: dict | None = None) -> None:
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
        await ImportService.process_batch(db, batch, account, file_bytes, column_mapping=column_mapping)


@router.post("", response_model=ImportInitiated, status_code=202)
async def start_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    account_id: uuid.UUID = Form(...),
    column_mapping: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> ImportInitiated:
    account = await db.get(Account, account_id)
    if not account or not account.is_active:
        raise HTTPException(status_code=404, detail="Account not found")

    parsed_mapping: dict | None = None
    if column_mapping:
        try:
            parsed_mapping = json.loads(column_mapping)
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=422, detail="column_mapping must be valid JSON")

    file_bytes = await file.read()
    filename = file.filename or "upload.csv"

    batch = ImportBatch(
        account_id=account_id,
        filename=filename,
        parser_used=account.bank,
        status="processing",
        column_mapping=parsed_mapping,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOADS_DIR / f"{batch.id}.csv").write_bytes(file_bytes)

    background_tasks.add_task(_run_import, batch.id, file_bytes, parsed_mapping)
    return ImportInitiated(batch_id=batch.id, message="Import started")


@router.post("/{batch_id}/retry", response_model=ImportInitiated, status_code=202)
async def retry_batch(
    batch_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ImportInitiated:
    batch = await db.get(ImportBatch, batch_id)
    if not batch or batch.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed batches can be retried")
    upload_path = UPLOADS_DIR / f"{batch_id}.csv"
    if not upload_path.exists():
        raise HTTPException(status_code=409, detail="Original file not found; please re-upload")
    batch.status = "processing"
    batch.error_message = None
    await db.commit()
    background_tasks.add_task(_run_import, batch.id, upload_path.read_bytes(), batch.column_mapping)
    return ImportInitiated(batch_id=batch.id, message="Retry started")


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
