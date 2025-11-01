"""
Database initialization script.
Run this to create tables and seed initial data (admin user, credit settings, and credit transactions).
"""
import sys
import os

# Add server directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seeders.user_seeder import seed_admin_user
from seeders.credit_settings_seeder import seed_credit_settings
from seeders.credit_transaction_seeder import seed_credit_transactions


if __name__ == "__main__":
    print("Initializing database...")
    print()
    
    # Seed credit settings first (before users, as users might need credit settings)
    print("Seeding credit settings...")
    seed_credit_settings()
    print()
    
    # Seed admin user and sample users
    print("Seeding users...")
    seed_admin_user()
    print()
    
    # Seed credit transactions for users
    print("Seeding credit transactions...")
    seed_credit_transactions()
    print()
    
    print("Database initialization complete!")

