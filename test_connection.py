from app.models import engine, User, Opportunity
from sqlalchemy import inspect

def test_connection():
    try:
        # Create an inspector
        inspector = inspect(engine)
        
        # Get all table names
        tables = inspector.get_table_names()
        print("Successfully connected to NeonTech PostgreSQL!")
        print("\nAvailable tables:")
        for table in tables:
            print(f"- {table}")
            # Get columns for each table
            columns = inspector.get_columns(table)
            for column in columns:
                print(f"  • {column['name']} ({column['type']})")

    except Exception as e:
        print(f"Error connecting to database: {str(e)}")

if __name__ == "__main__":
    test_connection() 