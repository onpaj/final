"""Purge all category data and set all transactions to unassigned."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal


async def purge():
    async with AsyncSessionLocal() as db:
        # 1. Unassign all transactions
        r1 = await db.execute(text("UPDATE transactions SET category_id = NULL, categorization_source = NULL"))
        print(f"Transactions unassigned: {r1.rowcount}")

        # 2. Clear LLM classification suggestions
        r2 = await db.execute(text("UPDATE llm_classifications SET suggested_category_id = NULL"))
        print(f"LLM classifications cleared: {r2.rowcount}")

        # 3. Delete rules
        r3 = await db.execute(text("DELETE FROM rules"))
        print(f"Rules deleted: {r3.rowcount}")

        # 4. Delete all categories
        r4 = await db.execute(text("DELETE FROM categories"))
        print(f"Categories deleted: {r4.rowcount}")

        # 5. Delete all category groups
        r5 = await db.execute(text("DELETE FROM category_groups"))
        print(f"Category groups deleted: {r5.rowcount}")

        await db.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(purge())
