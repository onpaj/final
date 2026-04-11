from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self._db = db

    @staticmethod
    def _savings_rate(income: Decimal, expenses: Decimal) -> Decimal:
        if income == 0:
            return Decimal("0")
        saved = income + expenses  # expenses is negative
        return (saved / income).quantize(Decimal("0.01"))

    @staticmethod
    def _six_months_ago_ym(year: int, month: int) -> int:
        if month > 6:
            return year * 100 + (month - 6)
        else:
            return (year - 1) * 100 + (month + 6)

    async def monthly_summary(self, year: int, month: int, account_id: str | None = None) -> dict:
        account_filter = "AND t.account_id = :account_id" if account_id else ""
        sql = text(f"""
            SELECT
                cg.id AS group_id,
                cg.name AS group_name,
                cg.slug AS group_slug,
                cg.color AS group_color,
                cg.sort_order AS group_sort,
                c.name AS category_name,
                c.slug AS category_slug,
                c.is_income,
                c.id AS category_id,
                COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN category_groups cg ON c.group_id = cg.id
            WHERE
                t.is_transfer = false
                AND EXTRACT(YEAR FROM t.booking_date) = :year
                AND EXTRACT(MONTH FROM t.booking_date) = :month
                {account_filter}
            GROUP BY cg.id, cg.name, cg.slug, cg.color, cg.sort_order, c.id, c.name, c.slug, c.is_income
            ORDER BY cg.sort_order, c.name
        """)
        params: dict = {"year": year, "month": month}
        if account_id:
            params["account_id"] = account_id

        result = await self._db.execute(sql, params)
        rows = result.all()

        groups: dict[str, dict] = {}
        income = Decimal("0")
        expenses = Decimal("0")

        for row in rows:
            gid = str(row.group_id)
            if gid not in groups:
                groups[gid] = {
                    "name": row.group_name,
                    "group_slug": row.group_slug,
                    "color": row.group_color,
                    "total": Decimal("0"),
                    "categories": [],
                }
            groups[gid]["total"] += row.total
            groups[gid]["categories"].append({
                "id": str(row.category_id),
                "name": row.category_name,
                "category_slug": row.category_slug,
                "total": float(row.total),
                "is_income": row.is_income,
            })
            if row.is_income:
                income += row.total
            else:
                expenses += row.total

        return {
            "year": year,
            "month": month,
            "groups": list(groups.values()),
            "income": float(income),
            "expenses": float(expenses),
            "savings_rate": float(self._savings_rate(income, expenses)),
        }

    async def trends(self, from_year: int, from_month: int, to_year: int, to_month: int, account_id: str | None = None) -> list[dict]:
        account_filter = "AND t.account_id = :account_id" if account_id else ""
        sql = text(f"""
            SELECT
                EXTRACT(YEAR FROM t.booking_date)::int AS year,
                EXTRACT(MONTH FROM t.booking_date)::int AS month,
                c.name AS category_name,
                cg.id AS group_id,
                cg.name AS group_name,
                cg.slug AS group_slug,
                c.is_income,
                COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            JOIN category_groups cg ON c.group_id = cg.id
            WHERE
                t.is_transfer = false
                AND (EXTRACT(YEAR FROM t.booking_date) * 100 + EXTRACT(MONTH FROM t.booking_date))
                    BETWEEN :from_ym AND :to_ym
                {account_filter}
            GROUP BY year, month, c.id, c.name, cg.id, cg.name, cg.slug, c.is_income
            ORDER BY year, month, cg.name, c.name
        """)
        params: dict = {
            "from_ym": from_year * 100 + from_month,
            "to_ym": to_year * 100 + to_month,
        }
        if account_id:
            params["account_id"] = account_id

        result = await self._db.execute(sql, params)
        return [
            {
                "year": row.year, "month": row.month,
                "category": row.category_name, "group": row.group_name,
                "group_slug": row.group_slug,
                "is_income": row.is_income, "total": float(row.total),
            }
            for row in result.all()
        ]

    async def anomalies(self, year: int, month: int, account_id: str | None = None) -> list[dict]:
        account_filter = "AND t.account_id = :account_id" if account_id else ""
        sql = text(f"""
            WITH monthly_group AS (
                SELECT
                    EXTRACT(YEAR FROM t.booking_date)::int AS yr,
                    EXTRACT(MONTH FROM t.booking_date)::int AS mo,
                    cg.id AS group_id,
                    cg.name AS group_name,
                    SUM(ABS(t.amount)) AS total
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN category_groups cg ON c.group_id = cg.id
                WHERE
                    t.is_transfer = false
                    AND c.is_income = false
                    AND (EXTRACT(YEAR FROM t.booking_date) * 100 + EXTRACT(MONTH FROM t.booking_date))
                        BETWEEN :from_ym AND :to_ym
                    {account_filter}
                GROUP BY yr, mo, cg.id, cg.name
            ),
            trailing AS (
                SELECT group_id, group_name,
                    AVG(total) AS mean, STDDEV(total) AS stddev
                FROM monthly_group
                WHERE NOT (yr = :year AND mo = :month)
                GROUP BY group_id, group_name
            ),
            current_month AS (
                SELECT group_id, total AS current_total
                FROM monthly_group
                WHERE yr = :year AND mo = :month
            )
            SELECT t.group_name, c.current_total, t.mean, t.stddev
            FROM trailing t
            JOIN current_month c ON c.group_id = t.group_id
            WHERE t.stddev > 0 AND c.current_total > t.mean + 2 * t.stddev
        """)
        from_ym = self._six_months_ago_ym(year, month)
        params: dict = {"year": year, "month": month, "from_ym": from_ym, "to_ym": year * 100 + month}
        if account_id:
            params["account_id"] = account_id

        result = await self._db.execute(sql, params)
        return [
            {
                "group": row.group_name,
                "current": float(row.current_total),
                "mean": float(row.mean),
                "stddev": float(row.stddev),
            }
            for row in result.all()
        ]
