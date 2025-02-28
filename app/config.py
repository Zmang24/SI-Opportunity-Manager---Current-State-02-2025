import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory of the application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Storage configuration
STORAGE_DIR = os.path.join(BASE_DIR, 'storage', 'files')

# Ensure storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "opportunity-files")

# Application settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-in-production")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL") 