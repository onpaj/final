"""Reassign transactions from one account to another by name."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal

OLD_ACCOUNT_ID = "2bd25200-c760-4b00-973d-2d41615f42dd"
TARGET_ACCOUNT_NAME = "Partners - Ondra"


async def reassign():
    async with AsyncSessionLocal() as db:
        # Find the target account
        result = await db.execute(
            text("SELECT id, name FROM accounts WHERE name = :name"),
            {"name": TARGET_ACCOUNT_NAME},
        )
        row = result.fetchone()
        if row is None:
            print(f"ERROR: No account found with name '{TARGET_ACCOUNT_NAME}'")
            print("Available accounts:")
            all_accounts = await db.execute(text("SELECT id, name FROM accounts"))
            for a in all_accounts.fetchall():
                print(f"  {a.id}  {a.name}")
            return

        new_account_id = row.id
        print(f"Target account: {row.name} ({new_account_id})")

        if str(new_account_id) == OLD_ACCOUNT_ID:
            print("Source and target are the same account — nothing to do.")
            return

        # Reassign transactions
        r1 = await db.execute(
            text("UPDATE transactions SET account_id = :new_id WHERE account_id = :old_id"),
            {"new_id": new_account_id, "old_id": OLD_ACCOUNT_ID},
        )
        print(f"Transactions reassigned: {r1.rowcount}")

        # Reassign import_batches
        r2 = await db.execute(
            text("UPDATE import_batches SET account_id = :new_id WHERE account_id = :old_id"),
            {"new_id": new_account_id, "old_id": OLD_ACCOUNT_ID},
        )
        print(f"Import batches reassigned: {r2.rowcount}")

        await db.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(reassign())
