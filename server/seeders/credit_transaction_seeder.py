"""
Credit transaction seeder to create initial credit transactions for users.
"""
from sqlalchemy.orm import Session

from core.database import get_db, init_db
from models.user import User
from models.credit_settings import CreditSettings
from services.credit_service import credit_service, TransactionType


def seed_credit_transactions() -> None:
    """
    Create credit transactions for existing users.
    
    This function:
    1. Gives free credits on signup to all users (based on credit_settings)
    2. Adds some sample purchase transactions for test users
    """
    # Initialize database tables
    init_db()
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Get credit settings to know how many free credits to give
        credit_settings = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
        free_credits = credit_settings.free_credits_on_signup if credit_settings else 15
        
        # Get all users
        users = db.query(User).all()
        
        if not users:
            print("[INFO] No users found. Please run user seeder first.")
            return
        
        transactions_created = 0
        
        for user in users:
            # Skip admin users (they have unlimited credits)
            if user.role == "ADMIN":
                print(f"[SKIP] Admin user {user.email} has unlimited credits")
                continue
            
            # Check if user already has transactions
            existing_transactions = credit_service.get_user_transactions(db, user.id, limit=1)
            if existing_transactions:
                print(f"[SKIP] User {user.email} already has transactions")
                continue
            
            # Give free credits on signup
            credit_service.add_credits(
                db=db,
                user_id=user.id,
                amount=free_credits,
                description=f"Free credits on signup ({free_credits} credits)",
                transaction_type=TransactionType.FREE_GIFT
            )
            transactions_created += 1
            print(f"[OK] Added {free_credits} free credits to {user.email}")
            
            # Add a sample purchase for some users (randomly)
            if user.id % 2 == 0:  # Every other user gets a purchase
                purchase_amount = 200
                credit_service.add_credits(
                    db=db,
                    user_id=user.id,
                    amount=purchase_amount,
                    description=f"Credit purchase ({purchase_amount} credits for €{purchase_amount * 0.10:.2f})",
                    transaction_type=TransactionType.PURCHASE
                )
                transactions_created += 1
                print(f"[OK] Added {purchase_amount} purchased credits to {user.email}")
        
        if transactions_created > 0:
            print(f"[OK] Created {transactions_created} credit transactions")
        else:
            print("[OK] Credit transactions already exist for all users")
    
    except Exception as e:
        print(f"[ERROR] Failed to seed credit transactions: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_credit_transactions()

