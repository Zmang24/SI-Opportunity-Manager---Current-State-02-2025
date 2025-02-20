from app.models import Base, engine
from app.models.models import User, Opportunity, Vehicle, AdasSystem

def create_tables():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Successfully created all database tables!")

if __name__ == "__main__":
    create_tables() 