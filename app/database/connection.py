import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import time

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Create engine with enhanced configuration for Neon
engine = create_engine(
    DATABASE_URL,
    # Note: sslmode is included in the connection string, not in connect_args
    pool_size=5,  # Maximum number of connections in the pool
    max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
    pool_timeout=30,  # Timeout for getting a connection from the pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True  # Enable connection health checks
)

# Add event listeners for connection debugging
@event.listens_for(engine, 'connect')
def receive_connect(dbapi_connection, connection_record):
    print('New connection established')

@event.listens_for(engine, 'checkout')
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    print('Connection retrieved from pool')

@event.listens_for(engine, 'checkin')
def receive_checkin(dbapi_connection, connection_record):
    print('Connection returned to pool')

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        # Test the connection with proper text() wrapper
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def get_db_with_retry(max_retries=3, delay=1):
    """Get a database session with retry logic"""
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Test the connection with proper text() wrapper
            db.execute(text("SELECT 1"))
            return db
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {str(e)}")
            if db:
                db.close()
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise 