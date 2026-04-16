"""Migrate accounts and rules from dev environment to production.

Reads DATABASE_URL from .env (source/dev) and .env.prod (destination/prod).
- Accounts are upserted first (by UUID); name/iban/bank/currency/is_active are updated.
- Categories are matched by ID (same seed UUIDs in both envs).
- Rules are upserted after accounts; account_id is preserved since UUIDs match.
- Existing records (same UUID) are updated in place (upsert).

Usage:
    cd backend
    python scripts/migrate_rules.py [--dry-run]
"""
import asyncio
import re
import sys
from pathlib import Path

import asyncpg

BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_ENV = BACKEND_DIR / ".env"
DST_ENV = BACKEND_DIR / ".env.prod"


def parse_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Z_]+)\s*=\s*(.*)$", line)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env


def asyncpg_url(url: str) -> str:
    """Convert SQLAlchemy asyncpg URL to plain asyncpg DSN."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def migrate_accounts(src: asyncpg.Connection, dst: asyncpg.Connection, dry_run: bool) -> None:
    accounts = await src.fetch(
        "SELECT id, name, bank, iban, currency, is_active, created_at FROM accounts ORDER BY created_at"
    )
    print(f"Found {len(accounts)} accounts in source")
    for acc in accounts:
        print(f"  {'[DRY] ' if dry_run else ''}Upserting account: '{acc['name']}' ({acc['bank']}, iban={acc['iban']})")
        if not dry_run:
            await dst.execute(
                """
                INSERT INTO accounts (id, name, bank, iban, currency, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    name      = EXCLUDED.name,
                    bank      = EXCLUDED.bank,
                    iban      = EXCLUDED.iban,
                    currency  = EXCLUDED.currency,
                    is_active = EXCLUDED.is_active
                """,
                acc["id"], acc["name"], acc["bank"], acc["iban"],
                acc["currency"], acc["is_active"], acc["created_at"],
            )
    print(f"Accounts {'would be ' if dry_run else ''}upserted: {len(accounts)}\n")


async def migrate_rules(src: asyncpg.Connection, dst: asyncpg.Connection, dry_run: bool) -> None:
    rules = await src.fetch("""
        SELECT id, name, priority, match_type, match_value,
               category_id, enabled, account_id, created_at
        FROM rules
        ORDER BY priority, created_at
    """)
    print(f"Found {len(rules)} rules in source")

    for rule in rules:
        print(
            f"  {'[DRY] ' if dry_run else ''}Upserting rule: "
            f"'{rule['name']}' (priority={rule['priority']}, "
            f"account={str(rule['account_id'])[:8] + '...' if rule['account_id'] else 'none'})"
        )
        if not dry_run:
            await dst.execute(
                """
                INSERT INTO rules (
                    id, name, priority, match_type, match_value,
                    category_id, enabled, account_id, hit_count, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 0, $9)
                ON CONFLICT (id) DO UPDATE SET
                    name        = EXCLUDED.name,
                    priority    = EXCLUDED.priority,
                    match_type  = EXCLUDED.match_type,
                    match_value = EXCLUDED.match_value,
                    category_id = EXCLUDED.category_id,
                    enabled     = EXCLUDED.enabled,
                    account_id  = EXCLUDED.account_id
                """,
                rule["id"], rule["name"], rule["priority"], rule["match_type"],
                rule["match_value"], rule["category_id"], rule["enabled"],
                rule["account_id"], rule["created_at"],
            )

    print(f"Rules {'would be ' if dry_run else ''}upserted: {len(rules)}\n")


async def run(dry_run: bool) -> None:
    src_env = parse_env(SRC_ENV)
    dst_env = parse_env(DST_ENV)

    src_url = asyncpg_url(src_env["DATABASE_URL"])
    dst_url = asyncpg_url(dst_env["DATABASE_URL"])

    print(f"Source : {SRC_ENV.name}")
    print(f"Dest   : {DST_ENV.name}")
    if dry_run:
        print("DRY RUN — no changes will be written\n")

    src = await asyncpg.connect(src_url)
    dst = await asyncpg.connect(dst_url)

    try:
        await migrate_accounts(src, dst, dry_run)
        await migrate_rules(src, dst, dry_run)
        print("Migration complete.")
    finally:
        await src.close()
        await dst.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run(dry_run))
