from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/monthly")
async def monthly(
    year: int = Query(...),
    month: int = Query(...),
    account_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.monthly_summary(year, month, account_id)


@router.get("/trends")
async def trends(
    from_year: int = Query(...),
    from_month: int = Query(...),
    to_year: int = Query(...),
    to_month: int = Query(...),
    account_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.trends(from_year, from_month, to_year, to_month, account_id)


@router.get("/anomalies")
async def anomalies(
    year: int = Query(...),
    month: int = Query(...),
    account_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = AnalyticsService(db)
    return await service.anomalies(year, month, account_id)
