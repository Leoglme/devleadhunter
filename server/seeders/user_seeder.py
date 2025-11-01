"""
User seeder to create initial admin user.
"""
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db, init_db
from models.user import User
from services.auth_service import get_password_hash, get_user_by_email
from enums.user_role import UserRole


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
        existing_admin = get_user_by_email(db, settings.admin_email)
        if existing_admin:
            print(f"[OK] Admin user already exists: {settings.admin_email}")
            return
        
        # Create admin user
        admin_user = User(
            name="Admin User",
            email=settings.admin_email,
            hashed_password=get_password_hash(settings.admin_password),
            role=UserRole.ADMIN,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"[OK] Admin user created: {settings.admin_email}")
        
    except Exception as e:
        print(f"[ERROR] Failed to create admin user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin_user()

