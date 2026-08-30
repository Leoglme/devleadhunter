"""
Migration: ``user_modules`` table — per-user activation of tool modules.

The websites module is the always-on base tenant; other modules (Apple Wallet, and
future ones) are toggled per user. One row per (user, module).

Run with:
    python migrations/add_user_modules.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

_USER_MODULES_DDL = """
CREATE TABLE IF NOT EXISTS user_modules (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  module VARCHAR(32) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  activated_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  UNIQUE KEY uq_user_modules_user_module (user_id, module),
  KEY ix_user_modules_user_id (user_id),
  KEY ix_user_modules_module (module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def run_migration() -> None:
    print("Running migration: add_user_modules")
    with engine.connect() as conn:
        conn.execute(text(_USER_MODULES_DDL))
        conn.commit()
    print("  + user_modules table")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: user_modules table")
    print("=" * 60)
    run_migration()
