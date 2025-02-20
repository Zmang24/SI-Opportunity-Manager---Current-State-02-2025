from sqlalchemy import create_engine, text
from app.models import SQLALCHEMY_DATABASE_URL

def reset_database():
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        # Connect and execute DROP commands
        with engine.connect() as connection:
            # Disable foreign key checks temporarily
            connection.execute(text("DROP SCHEMA public CASCADE;"))
            connection.execute(text("CREATE SCHEMA public;"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO neondb_owner;"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            
        print("Successfully reset database!")
        
    except Exception as e:
        print(f"Error resetting database: {str(e)}")
        raise

if __name__ == "__main__":
    reset_database() 