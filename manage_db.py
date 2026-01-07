#!/usr/bin/env python3
"""Database initialization and management script."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.database.db import Database
from src.utils.logger import get_logger

logger = get_logger(__name__)


def init_database():
    """Initialize database with all required tables."""
    logger.info("Initializing database...")
    db = Database()
    logger.info("Database initialized successfully")


def reset_database():
    """Reset database (delete all data)."""
    import os
    from config.config import DB_PATH
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        logger.info(f"Database reset: {DB_PATH} deleted")
    
    init_database()


def show_stats():
    """Show database statistics."""
    db = Database()
    
    users = db.get_all_users()
    logger.info(f"\nDatabase Statistics:")
    logger.info(f"   Total users: {len(users)}")
    
    total_bookings = 0
    total_filters = 0
    
    for user in users:
        bookings = db.get_user_bookings(user.telegram_id)
        user_filter = db.get_filter(user.telegram_id)
        total_bookings += len(bookings)
        if user_filter:
            total_filters += 1
    
    logger.info(f"   Total bookings: {total_bookings}")
    logger.info(f"   Users with filters: {total_filters}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database management script")
    parser.add_argument("action", choices=["init", "reset", "stats"], 
                      help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "init":
        init_database()
    elif args.action == "reset":
        confirm = input(" Are you sure you want to reset the database? (yes/no): ")
        if confirm.lower() == "yes":
            reset_database()
        else:
            logger.info("Reset cancelled")
    elif args.action == "stats":
        show_stats()
