from sqlalchemy import create_engine, inspect
from app.database.connection import SessionLocal
from app.models.models import User

# Create inspector
db = SessionLocal()
engine = db.get_bind()
inspector = inspect(engine)

try:
    # Get columns for users table
    columns = inspector.get_columns('users')
    print("\nUsers table columns:")
    print("-------------------")
    for column in columns:
        print(f"Name: {column['name']}, Type: {column['type']}, Nullable: {column.get('nullable', True)}")
finally:
    db.close() 