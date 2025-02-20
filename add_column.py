from app.database.connection import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Add the column
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS icon_theme VARCHAR DEFAULT 'Rainbow Animation'"))
    db.commit()
    print("Successfully added icon_theme column")
except Exception as e:
    db.rollback()
    print(f"Error adding column: {str(e)}")
finally:
    db.close() 