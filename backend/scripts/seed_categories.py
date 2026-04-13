"""Seed category_groups and categories from CSV files."""
import asyncio
import csv
import uuid
from pathlib import Path

from sqlalchemy import text
from app.db.session import engine

REPO_ROOT = Path(__file__).resolve().parents[2]
GROUPS_CSV = REPO_ROOT / "category_groups.csv"
CATEGORIES_CSV = REPO_ROOT / "categories.csv"


def parse_bool(val: str) -> bool:
    return val.strip().lower() == "true"


async def seed() -> None:
    async with engine.begin() as conn:
        # --- category_groups ---
        with GROUPS_CSV.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            await conn.execute(
                text("""
                    INSERT INTO category_groups (id, name, sort_order, color, slug)
                    VALUES (:id, :name, :sort_order, :color, :slug)
                    ON CONFLICT (id) DO UPDATE
                      SET name       = EXCLUDED.name,
                          sort_order = EXCLUDED.sort_order,
                          color      = EXCLUDED.color,
                          slug       = EXCLUDED.slug
                """),
                {
                    "id": uuid.UUID(row["id"]),
                    "name": row["name"],
                    "sort_order": int(row["sort_order"]),
                    "color": row["color"] or None,
                    "slug": row["slug"] or None,
                },
            )
        print(f"Upserted {len(rows)} category_groups")

        # --- categories ---
        with CATEGORIES_CSV.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        for row in rows:
            await conn.execute(
                text("""
                    INSERT INTO categories (id, group_id, name, is_income, color, sort_order, is_system, slug)
                    VALUES (:id, :group_id, :name, :is_income, :color, :sort_order, :is_system, :slug)
                    ON CONFLICT (id) DO UPDATE
                      SET group_id   = EXCLUDED.group_id,
                          name       = EXCLUDED.name,
                          is_income  = EXCLUDED.is_income,
                          color      = EXCLUDED.color,
                          sort_order = EXCLUDED.sort_order,
                          is_system  = EXCLUDED.is_system,
                          slug       = EXCLUDED.slug
                """),
                {
                    "id": uuid.UUID(row["id"]),
                    "group_id": uuid.UUID(row["group_id"]),
                    "name": row["name"],
                    "is_income": parse_bool(row["is_income"]),
                    "color": row["color"] or None,
                    "sort_order": int(row["sort_order"]),
                    "is_system": parse_bool(row["is_system"]),
                    "slug": row["slug"] or None,
                },
            )
        print(f"Upserted {len(rows)} categories")



if __name__ == "__main__":
    asyncio.run(seed())
