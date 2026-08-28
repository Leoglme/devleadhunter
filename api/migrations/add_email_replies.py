"""
Migration: reply capture — ``email_logs.replied_at`` + ``email_replies`` table.

Prospect replies are received on the Resend inbound domain (``REPLY_CAPTURE_DOMAIN``)
and correlated back to the outbound send via a signed ``reply-<id>-<sig>@`` address.
``replied_at`` timestamps the first reply on the send; ``email_replies`` stores each
reply's content and how it was matched.

Run with:
    python migrations/add_email_replies.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

_EMAIL_REPLIES_DDL = """
CREATE TABLE IF NOT EXISTS email_replies (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  email_log_id INT NOT NULL,
  user_id INT NOT NULL,
  prospect_id INT NULL,
  from_email VARCHAR(255) NOT NULL,
  subject VARCHAR(500) NULL,
  body_text TEXT NULL,
  body_html TEXT NULL,
  resend_email_id VARCHAR(255) NOT NULL,
  message_id VARCHAR(255) NULL,
  matched_by VARCHAR(20) NOT NULL,
  is_auto_reply TINYINT(1) NOT NULL DEFAULT 0,
  received_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_email_replies_resend_email_id (resend_email_id),
  KEY ix_email_replies_email_log_id (email_log_id),
  KEY ix_email_replies_user_id (user_id),
  KEY ix_email_replies_prospect_id (prospect_id),
  KEY ix_email_replies_from_email (from_email),
  CONSTRAINT fk_email_replies_email_log
    FOREIGN KEY (email_log_id) REFERENCES email_logs (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def run_migration() -> None:
    print("Running migration: add_email_replies")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE email_logs ADD COLUMN IF NOT EXISTS replied_at DATETIME NULL AFTER clicked_at"))
        conn.execute(text(_EMAIL_REPLIES_DDL))
        conn.commit()
    print("  + email_logs.replied_at")
    print("  + email_replies table")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Reply capture (replied_at + email_replies)")
    print("=" * 60)
    run_migration()
