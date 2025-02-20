from sqlalchemy import create_engine, text
from app.models import SQLALCHEMY_DATABASE_URL

def inspect_database():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Get all tables and their columns
            result = connection.execute(text("""
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """))
            
            for row in result:
                print(f"Table: {row[0]}, Column: {row[1]}, Type: {row[2]}, Default: {row[3]}")
            
    except Exception as e:
        print(f"Error inspecting database: {str(e)}")

if __name__ == "__main__":
    inspect_database() 