import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.database.connection import engine

def run_migration():
    # Read the migration file
    with open('migrations/007_fix_timezone_awareness.sql', 'r') as f:
        migration_sql = f.read()
    
    # Split into individual statements
    statements = migration_sql.split(';')
    
    # Execute each statement
    with engine.connect() as conn:
        try:
            for statement in statements:
                if statement.strip():  # Skip empty statements
                    print(f"Executing: {statement.strip()}")
                    conn.execute(text(statement))
            conn.commit()
            print("Migration completed successfully!")
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            conn.rollback()
            raise

if __name__ == "__main__":
    run_migration() 