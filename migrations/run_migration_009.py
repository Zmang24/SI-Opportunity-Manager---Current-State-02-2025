import os
import psycopg2
from dotenv import load_dotenv

def run_migration():
    """Run the migration to add tracking fields to vehicles table"""
    load_dotenv()
    
    # Get database connection details from environment variables
    db_url = os.getenv("DATABASE_URL")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Read and execute the migration SQL
        with open(os.path.join(os.path.dirname(__file__), '009_update_vehicles_tracking.sql'), 'r') as f:
            migration_sql = f.read()
            cur.execute(migration_sql)
        
        # Commit the changes
        conn.commit()
        print("Migration 009 completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration() 