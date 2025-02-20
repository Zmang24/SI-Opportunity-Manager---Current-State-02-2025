from sqlalchemy import create_engine
from sqlalchemy.sql import text

# Database connection string
db_url = "postgresql://neondb_owner:npg_PjA2IbceDVn3@ep-restless-tree-aakkf9mc-pooler.westus3.azure.neon.tech/neondb?sslmode=require"

# Create engine
engine = create_engine(db_url)

# SQL to add the comments column
sql = """
ALTER TABLE opportunities 
ADD COLUMN IF NOT EXISTS comments JSONB DEFAULT '[]';
"""

try:
    with engine.connect() as connection:
        connection.execute(text(sql))
        connection.commit()
        print("Migration applied successfully!")
except Exception as e:
    print(f"Error applying migration: {str(e)}") 