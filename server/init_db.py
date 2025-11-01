"""
Database initialization script.
Run this to create tables and seed admin user.
"""
import sys
import os

# Add server directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seeders.user_seeder import seed_admin_user


if __name__ == "__main__":
    print("Initializing database...")
    seed_admin_user()
    print("Database initialization complete!")

