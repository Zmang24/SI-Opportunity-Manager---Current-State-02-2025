from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Import models after Base is defined
from .models import User, Opportunity, Vehicle, AdasSystem

# Make all models available at the package level
__all__ = [
    'Base',
    'SessionLocal',
    'engine',
    'User',
    'Opportunity',
    'Vehicle',
    'AdasSystem'
]

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 