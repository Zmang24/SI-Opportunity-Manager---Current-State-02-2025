import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def check_tables():
    try:
        # Connect to the database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        # Get list of tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        
        print("Database Tables:")
        print("----------------")
        
        # For each table, get its columns
        for table in tables:
            table_name = table[0]
            print(f"\n{table_name}:")
            
            cur.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            
            columns = cur.fetchall()
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_tables() 