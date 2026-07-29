"""Migration — delete the demo accounts the old seeder used to generate.

The user seeder used to create ten Faker accounts per run. Random emails never
collide, so every deploy added ten more. The generator is gone; this removes what
it already produced, everywhere.

Kept: the configured admin, and any account holding the ADMIN role — so a real
administrator is never wiped by a stale ``ADMIN_EMAIL``.

Rows owned by a purged account are deleted explicitly, child-first. Relying on the
foreign keys would not do: seven of them are RESTRICT (they would abort the deploy),
and six columns pointing at ``users`` carry no constraint at all (they would leave
orphans behind). Grandchildren guarded by a RESTRICT key (a support attachment, a
follow-up bound to a template) are cleared first, for the same reason.

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

# Grandchildren: they hang off a row above by a RESTRICT key, so they must go
# first or the parent delete is refused. (child, child column, parent, user column)
_DEPENDENT_ROWS: list[tuple[str, str, str, str]] = [
    ("support_attachments", "message_id", "support_messages", "sender_id"),
    ("support_attachments", "ticket_id", "support_tickets", "user_id"),
    ("campaign_follow_ups", "template_id", "email_templates", "user_id"),
]

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

        for child, child_column, parent, user_column in _DEPENDENT_ROWS:
            if not _table_exists(conn, child) or not _table_exists(conn, parent):
                continue
            statement = text(
                f"DELETE FROM {child} WHERE {child_column} IN (SELECT id FROM {parent} WHERE {user_column} IN :ids)"
            ).bindparams(bindparam("ids", expanding=True))
            deleted = conn.execute(statement, {"ids": target_ids}).rowcount
            if deleted:
                print(f"  - {child} (via {parent}): {deleted} row(s)")

        for table, column in _OWNED_ROWS:
            if not _table_exists(conn, table):
                continue
            statement = text(f"DELETE FROM {table} WHERE {column} IN :ids").bindparams(bindparam("ids", expanding=True))
            deleted = conn.execute(statement, {"ids": target_ids}).rowcount
            if deleted:
                print(f"  - {table}: {deleted} row(s)")

        purge_users = text("DELETE FROM users WHERE id IN :ids").bindparams(bindparam("ids", expanding=True))
        purged = conn.execute(purge_users, {"ids": target_ids}).rowcount
        print(f"  - users: {purged} account(s)")

    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Purge demo users")
    print("=" * 60)
    run_migration()
