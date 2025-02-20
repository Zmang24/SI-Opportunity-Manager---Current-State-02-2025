import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def test_connection():
    try:
        # Get the DATABASE_URL from environment
        db_url = os.getenv('DATABASE_URL')
        print(f"Attempting to connect with URL: {db_url}")
        
        # Connect to the database
        conn = psycopg2.connect(db_url)
        print("Successfully connected to the database!")
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a simple query
        cur.execute('SELECT version();')
        
        # Fetch the result
        version = cur.fetchone()
        print(f"PostgreSQL version: {version[0]}")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_connection() 