import os

# Base directory of the application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Storage configuration
STORAGE_DIR = os.path.join(BASE_DIR, 'storage', 'files')

# Ensure storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True) 