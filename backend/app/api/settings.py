from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

router = APIRouter()

@router.get("/llm-cost")
async def llm_cost(db: AsyncSession = Depends(get_db)):
    sql = text("""
        SELECT
            EXTRACT(YEAR FROM created_at)::int AS year,
            EXTRACT(MONTH FROM created_at)::int AS month,
            model,
            COUNT(*) AS calls,
            SUM(prompt_tokens) AS prompt_tokens,
            SUM(completion_tokens) AS completion_tokens
        FROM llm_classifications
        GROUP BY year, month, model
        ORDER BY year DESC, month DESC, model
    """)
    result = await db.execute(sql)
    rows = result.all()
    return [
        {
            "year": r.year, "month": r.month, "model": r.model,
            "calls": r.calls,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            # Rough cost estimate based on Anthropic pricing (as of 2026-04):
            # Haiku: $0.25/1M input, $1.25/1M output
            # Sonnet: $3/1M input, $15/1M output
            "estimated_cost_usd": round(
                (r.prompt_tokens or 0) / 1_000_000 * (0.25 if "haiku" in r.model else 3.0) +
                (r.completion_tokens or 0) / 1_000_000 * (1.25 if "haiku" in r.model else 15.0),
                4
            ),
        }
        for r in rows
    ]
