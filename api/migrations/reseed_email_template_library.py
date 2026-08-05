"""Cut the admin's cold-email library over to the canonical 12 templates.

The seeder is append-only (it skips a template that already exists by name), so it
cannot rewrite the body/subject of the 17 rows already seeded on prod, nor retire
the angles we dropped. This migration is the real prod cut-over:

  - upsert every template of ``EMAIL_TEMPLATE_LIBRARY`` on the admin account
    (rewritten copy, ``{prix}`` variable, nude endings, per-angle ``theme``);
  - archive (``is_active = 0``) every older admin template no longer in the set —
    nothing is hard-deleted, so a dropped angle stays recoverable from the UI.

On a fresh database the admin user does not exist yet (the user seeder runs after
migrations), so this no-ops and the seeder performs the initial seed instead.

Idempotent: re-running upserts identical rows and re-archives the same leftovers.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sqlalchemy import bindparam, text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.config import settings
from core.database import engine
from seeders.email_template_seeder import EMAIL_TEMPLATE_LIBRARY

_VARIABLE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _variables_json(subject: str, body_html: str) -> str:
    """Serialise the sorted, unique {variable} names of a template, like the seeder does."""
    return json.dumps(sorted(set(_VARIABLE_RE.findall(f"{subject} {body_html}"))))


def run_migration() -> None:
    with engine.connect() as conn:
        admin_id = conn.execute(
            text("SELECT id FROM users WHERE email = :email"), {"email": settings.admin_email}
        ).scalar()
        if admin_id is None:
            print(f"[SKIP] Admin user {settings.admin_email!r} not found — seeder will do the initial seed")
            return

        for template in EMAIL_TEMPLATE_LIBRARY:
            params = {
                "user_id": admin_id,
                "name": str(template["name"]),
                "subject": str(template["subject"]),
                "body_html": str(template["body_html"]),
                "variables": _variables_json(str(template["subject"]), str(template["body_html"])),
                "category": str(template["category"]),
                "sort_order": int(template["sort_order"]),  # type: ignore[arg-type]
                "theme": str(template["theme"]),
            }
            existing_id = conn.execute(
                text("SELECT id FROM email_templates WHERE user_id = :user_id AND name = :name"),
                {"user_id": admin_id, "name": params["name"]},
            ).scalar()
            if existing_id is not None:
                conn.execute(
                    text(
                        """
                        UPDATE email_templates
                        SET subject = :subject, body_html = :body_html, variables = :variables,
                            category = :category, sort_order = :sort_order, theme = :theme, is_active = 1
                        WHERE id = :id
                        """
                    ),
                    {**params, "id": existing_id},
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO email_templates
                            (user_id, name, subject, body_html, variables, is_active, category, sort_order, theme)
                        VALUES
                            (:user_id, :name, :subject, :body_html, :variables, 1, :category, :sort_order, :theme)
                        """
                    ),
                    params,
                )

        canonical_names = [str(template["name"]) for template in EMAIL_TEMPLATE_LIBRARY]
        archive_stmt = text(
            "UPDATE email_templates SET is_active = 0 WHERE user_id = :user_id AND name NOT IN :names"
        ).bindparams(bindparam("names", expanding=True))
        conn.execute(archive_stmt, {"user_id": admin_id, "names": canonical_names})
        conn.commit()
        print(f"[OK] Reseeded {len(EMAIL_TEMPLATE_LIBRARY)} templates for admin {admin_id}; older ones archived.")


if __name__ == "__main__":
    run_migration()
