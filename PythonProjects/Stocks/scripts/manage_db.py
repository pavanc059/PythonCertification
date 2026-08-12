"""
Database management utility script.

Usage:
    python scripts/manage_db.py init     # Initialize database
    python scripts/manage_db.py drop     # Drop all tables (CAUTION!)
    python scripts/manage_db.py reset    # Drop and recreate all tables
    python scripts/manage_db.py status   # Check database status
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text, inspect
import structlog

from stockiq.infrastructure.database import get_engine, init_db, drop_db
from stockiq.infrastructure.config import get_settings

logger = structlog.get_logger(__name__)


def check_database_connection():
    """Check if database connection is working."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        return False


def check_timescaledb_extension():
    """Check if TimescaleDB extension is installed."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM pg_extension WHERE extname = 'timescaledb';
            """))
            return result.rowcount > 0
    except Exception as e:
        logger.error("timescaledb_check_failed", error=str(e))
        return False


def list_tables():
    """List all tables in the database."""
    try:
        engine = get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return tables
    except Exception as e:
        logger.error("failed_to_list_tables", error=str(e))
        return []


def get_table_row_counts():
    """Get row counts for all tables."""
    engine = get_engine()
    tables = list_tables()
    counts = {}
    
    with engine.connect() as conn:
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                counts[table] = count
            except Exception as e:
                counts[table] = f"Error: {e}"
    
    return counts


def show_status():
    """Show database status."""
    print("\n" + "="*60)
    print("DATABASE STATUS")
    print("="*60)
    
    settings = get_settings()
    db_url = settings.database_url.split('@')[1] if '@' in settings.database_url else settings.database_url
    
    print(f"\nDatabase URL: {db_url}")
    
    # Check connection
    print("\n1. Connection Status:")
    if check_database_connection():
        print("   ✅ Connected successfully")
    else:
        print("   ❌ Connection failed")
        return
    
    # Check TimescaleDB
    print("\n2. TimescaleDB Extension:")
    if check_timescaledb_extension():
        print("   ✅ TimescaleDB installed")
    else:
        print("   ⚠️  TimescaleDB not installed")
    
    # List tables
    print("\n3. Tables:")
    tables = list_tables()
    if tables:
        print(f"   Found {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
    else:
        print("   No tables found")
    
    # Show row counts
    if tables:
        print("\n4. Row Counts:")
        counts = get_table_row_counts()
        for table, count in sorted(counts.items()):
            print(f"   {table}: {count}")
    
    print("\n" + "="*60)


def initialize_database():
    """Initialize the database."""
    print("\n🔧 Initializing database...")
    
    if not check_database_connection():
        print("❌ Cannot connect to database. Please check your configuration.")
        return False
    
    try:
        # Import and run init_db script
        from init_db import main as init_main
        init_main()
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


def drop_database():
    """Drop all tables."""
    print("\n⚠️  WARNING: This will delete ALL data from the database!")
    response = input("Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("Aborted.")
        return False
    
    print("\n🗑️  Dropping all tables...")
    
    try:
        drop_db()
        print("✅ All tables dropped successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")
        return False


def reset_database():
    """Drop and recreate all tables."""
    print("\n🔄 Resetting database...")
    
    if drop_database():
        return initialize_database()
    return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Database management utility")
    parser.add_argument(
        "command",
        choices=["init", "drop", "reset", "status"],
        help="Command to execute"
    )
    
    args = parser.parse_args()
    
    if args.command == "init":
        success = initialize_database()
        sys.exit(0 if success else 1)
    
    elif args.command == "drop":
        success = drop_database()
        sys.exit(0 if success else 1)
    
    elif args.command == "reset":
        success = reset_database()
        sys.exit(0 if success else 1)
    
    elif args.command == "status":
        show_status()
        sys.exit(0)


if __name__ == "__main__":
    main()
