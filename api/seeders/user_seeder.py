"""
User seeder to create the initial admin user.

Demo accounts used to be generated here with Faker. They are gone: random emails
never collide, so every run created ten more accounts, and cleaning them up in one
environment did nothing for the next run. The ``purge_demo_users`` migration
removes the ones already created.
"""

from core.config import settings
from core.database import get_db, init_db
from enums.user_role import UserRole
from models.user import User
from services.auth_service import AuthService


def seed_admin_user() -> None:
    """
    Create admin user if it doesn't exist.

    This function creates an admin user with credentials from environment variables.
    """
    # Initialize database tables
    init_db()

    # Get database session
    db = next(get_db())

    try:
        # Check if admin user already exists
        existing_admin = AuthService.get_user_by_email(db, settings.admin_email)
        if existing_admin:
            print(f"[OK] Admin user already exists: {settings.admin_email}")
        else:
            # Create admin user
            admin_user = User(
                name="Léo Guillaume",
                email=settings.admin_email,
                hashed_password=AuthService.hash_password(settings.admin_password),
                role=UserRole.ADMIN.value,
                is_active=True,
            )

            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

            print(f"[OK] Admin user created: {settings.admin_email}")

    except Exception as e:
        print(f"[ERROR] Failed to seed users: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin_user()
