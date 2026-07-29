"""Migration — delete the demo accounts the old seeder used to generate.

The user seeder used to create ten Faker accounts per run. Random emails never
collide, so every deploy added ten more. The generator is gone; this removes what
it already produced, everywhere.

Kept: the configured admin, and any account holding the ADMIN role — so a real
administrator is never wiped by a stale ``ADMIN_EMAIL``.

Rows owned by a purged account are deleted explicitly: six columns pointing at
``users`` carry no foreign key at all and would leave orphans behind. Whatever a
RESTRICT key protects is cleared first, and that dependency graph is **read from the
live schema** — production and development were created years apart and do not carry
the same delete rules, so any hard-coded order is wrong on one of the two.

Idempotent: a second run finds nothing left to delete.

Run with:
    python migrations/purge_demo_users.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import bindparam, text

from core.config import settings
from core.database import engine

# (table, column) owned by a user, ordered children-first so no delete is refused.
# Tables not listed here hang off one of these by a CASCADE key (campaign_prospects,
# campaign_follow_ups, acquisition_run_items…) and go with their parent.
_OWNED_ROWS: list[tuple[str, str]] = [
    ("prospect_enrichments", "user_id"),
    ("prospect_interactions", "user_id"),
    ("email_queue", "user_id"),
    ("email_logs", "user_id"),
    ("campaigns", "user_id"),
    ("demo_sites", "user_id"),
    ("presenter_videos", "user_id"),
    ("orders", "user_id"),
    ("acquisition_runs", "user_id"),
    ("scraper_diagnostics", "user_id"),
    ("send_policies", "user_id"),
    ("email_templates", "user_id"),
    ("email_signatures", "user_id"),
    ("email_accounts", "user_id"),
    ("payment_accounts", "user_id"),
    ("resend_config", "user_id"),
    ("support_messages", "sender_id"),
    ("support_tickets", "user_id"),
    ("organization_members", "user_id"),
    ("organizations", "owner_user_id"),
    ("prospects", "user_id"),
    ("credit_transactions", "user_id"),
]

# Deep enough for this schema (attachment → message → ticket); a deeper chain means
# a cycle or an unexpected model, and must fail loudly rather than loop.
_MAX_DEPENDENCY_DEPTH: int = 6

# Columns merely *pointing* at a purged user, blanked instead of deleted: an
# unsubscribe record must outlive the account, and a ticket must keep its history.
_DETACHED_REFERENCES: list[tuple[str, str]] = [
    ("email_unsubscribes", "user_id"),
    ("support_tickets", "assigned_admin_id"),
]


def _table_exists(conn, table: str) -> bool:
    """Return True when ``table`` exists in the current schema."""
    result = conn.execute(
        text("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"),
        {"t": table},
    ).scalar()
    return bool(result)


def _restricting_children(conn, table: str) -> list[tuple[str, str]]:
    """
    Tables holding a foreign key to ``table`` that would refuse its deletion.

    Read from the live schema rather than hard-coded: production and development
    databases were created years apart and do not carry the same delete rules
    (``support_messages.ticket_id`` is RESTRICT in production, CASCADE locally).
    CASCADE and SET NULL children are left out — the database handles those.

    Args:
        conn: Open connection.
        table: Table about to be deleted from.

    Returns:
        (child table, child column) pairs to clear first.
    """
    rows = conn.execute(
        text(
            "SELECT k.TABLE_NAME, k.COLUMN_NAME "
            "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE k "
            "JOIN INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS r "
            "  ON r.CONSTRAINT_NAME = k.CONSTRAINT_NAME AND r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA "
            "WHERE k.TABLE_SCHEMA = DATABASE() AND k.REFERENCED_TABLE_NAME = :t "
            "  AND r.DELETE_RULE NOT IN ('CASCADE', 'SET NULL')"
        ),
        {"t": table},
    ).all()
    # A self-reference cannot be resolved by a subquery on the same table (MySQL 1093).
    return [(row[0], row[1]) for row in rows if row[0] != table]


def _purge_table(conn, table: str, where_sql: str, target_ids: list[int], depth: int = 0) -> None:
    """
    Delete the rows of ``table`` matched by ``where_sql``, children first.

    Args:
        conn: Open connection.
        table: Table to delete from.
        where_sql: Condition selecting the rows to delete, using the ``:ids`` parameter.
        target_ids: Identifiers of the accounts being purged.
        depth: Current recursion depth.

    Raises:
        RuntimeError: When the dependency chain is deeper than expected.
    """
    if depth > _MAX_DEPENDENCY_DEPTH:
        raise RuntimeError(f"Dependency chain too deep at {table} — cycle or unexpected schema")

    for child_table, child_column in _restricting_children(conn, table):
        _purge_table(
            conn,
            child_table,
            f"{child_column} IN (SELECT id FROM {table} WHERE {where_sql})",
            target_ids,
            depth + 1,
        )

    statement = text(f"DELETE FROM {table} WHERE {where_sql}").bindparams(bindparam("ids", expanding=True))
    deleted = conn.execute(statement, {"ids": target_ids}).rowcount
    if deleted:
        print(f"  - {'  ' * depth}{table}: {deleted} row(s)")


def run_migration() -> None:
    """Delete every non-admin account and everything it owns."""
    print("Running migration: purge_demo_users")

    with engine.begin() as conn:
        target_ids = [
            row[0]
            for row in conn.execute(
                text("SELECT id FROM users WHERE role <> 'ADMIN' AND email <> :admin_email"),
                {"admin_email": settings.admin_email},
            ).all()
        ]

        if not target_ids:
            print("  ~ no demo account left to purge")
            print("Migration completed successfully.")
            return

        print(f"  > {len(target_ids)} demo account(s) to purge")

        for table, column in _DETACHED_REFERENCES:
            if not _table_exists(conn, table):
                continue
            statement = text(f"UPDATE {table} SET {column} = NULL WHERE {column} IN :ids").bindparams(
                bindparam("ids", expanding=True)
            )
            detached = conn.execute(statement, {"ids": target_ids}).rowcount
            if detached:
                print(f"  ~ {table}.{column}: {detached} row(s) detached")

        for table, column in _OWNED_ROWS:
            if not _table_exists(conn, table):
                continue
            _purge_table(conn, table, f"{column} IN :ids", target_ids)

        _purge_table(conn, "users", "id IN :ids", target_ids)

    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Purge demo users")
    print("=" * 60)
    run_migration()
