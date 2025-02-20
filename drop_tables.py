from app.models import Base, engine

def drop_tables():
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    print("Successfully dropped all database tables!")

if __name__ == "__main__":
    drop_tables() 