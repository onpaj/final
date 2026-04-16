"""Migrate all rules from test environment to production.

Reads DATABASE_URL from .env.test (source) and .env (destination).
- Categories are matched by ID (same seed UUIDs in both envs).
- Accounts are matched by IBAN, then by name — rules with an account_id
  that cannot be matched in the destination are migrated without account scope
  and a warning is printed.
- Existing rules (same UUID) are updated in place (upsert).

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
SRC_ENV = BACKEND_DIR / ".env.test"
DST_ENV = BACKEND_DIR / ".env"


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


async def fetch_accounts(conn: asyncpg.Connection) -> dict[str, str]:
    """Return {iban: id, name: id} for all accounts."""
    rows = await conn.fetch("SELECT id, name, iban FROM accounts")
    mapping: dict[str, str] = {}
    for r in rows:
        if r["iban"]:
            mapping[r["iban"]] = str(r["id"])
        mapping[r["name"]] = str(r["id"])
    return mapping


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
        # --- load account mapping from destination ---
        dst_accounts = await fetch_accounts(dst)

        # --- load source account lookup (id → iban/name) ---
        src_account_rows = await src.fetch("SELECT id, name, iban FROM accounts")
        src_account_map: dict[str, dict] = {str(r["id"]): dict(r) for r in src_account_rows}

        # --- fetch all rules from source ---
        rules = await src.fetch("""
            SELECT r.id, r.name, r.priority, r.match_type, r.match_value,
                   r.category_id, r.enabled, r.account_id, r.created_at
            FROM rules r
            ORDER BY r.priority, r.created_at
        """)

        print(f"Found {len(rules)} rules in source\n")

        migrated = 0
        skipped_account = 0

        for rule in rules:
            rule_id = str(rule["id"])
            account_id_dst = None

            if rule["account_id"]:
                src_acc = src_account_map.get(str(rule["account_id"]))
                if src_acc:
                    # try IBAN first, then name
                    account_id_dst = (
                        dst_accounts.get(src_acc["iban"])
                        if src_acc["iban"]
                        else None
                    ) or dst_accounts.get(src_acc["name"])

                if not account_id_dst:
                    skipped_account += 1
                    src_label = (
                        src_acc["name"] if src_acc else str(rule["account_id"])
                    )
                    print(
                        f"  WARNING: rule '{rule['name']}' (id={rule_id}) "
                        f"references account '{src_label}' not found in dest — "
                        f"migrating without account scope"
                    )

            print(
                f"  {'[DRY] ' if dry_run else ''}Upserting rule: "
                f"'{rule['name']}' (priority={rule['priority']}, "
                f"account={'mapped' if account_id_dst else 'none'})"
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
                    rule["id"],
                    rule["name"],
                    rule["priority"],
                    rule["match_type"],
                    rule["match_value"],
                    rule["category_id"],
                    rule["enabled"],
                    account_id_dst,
                    rule["created_at"],
                )

            migrated += 1

        print(f"\nDone. {migrated} rules {'would be ' if dry_run else ''}upserted.")
        if skipped_account:
            print(f"       {skipped_account} rules had unresolved account references (migrated without account scope).")

    finally:
        await src.close()
        await dst.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run(dry_run))
