import os
import sqlite3
from config import DATABASE_PATH

def reset_database():
    """
    Reset the database by deleting it and recreating the tables.
    This is useful for development when the schema changes.
    """
    # Delete the database file if it exists
    if os.path.exists(DATABASE_PATH):
        print(f"Deleting existing database at {DATABASE_PATH}")
        os.remove(DATABASE_PATH)
    else:
        print(f"No existing database found at {DATABASE_PATH}")
    
    # Create the database directory if it doesn't exist
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Created database directory at {db_dir}")
    
    # Import app to trigger database initialization
    print("Initializing new database...")
    import app
    
    print("Database reset complete!")

if __name__ == "__main__":
    # Confirm with the user before proceeding
    confirm = input("This will delete all data in the database. Are you sure? (y/n): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("Database reset cancelled.")
