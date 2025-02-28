#!/usr/bin/env python
"""
Check if the Supabase bucket exists and create it if needed.
"""
import os
from dotenv import load_dotenv
from supabase import create_client
from typing import Dict, List, Any

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "opportunity-files")

def main():
    """Check if the Supabase bucket exists and create it if needed."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Supabase URL and key must be set in environment variables")
        return False
    
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # List all buckets
        buckets = supabase.storage.list_buckets()
        bucket_names = []
        for bucket in buckets:
            if isinstance(bucket, Dict) and 'name' in bucket:
                bucket_names.append(bucket['name'])
        
        if SUPABASE_BUCKET in bucket_names:
            print(f"✅ Bucket '{SUPABASE_BUCKET}' already exists")
            return True
        
        # Create bucket if it doesn't exist
        print(f"Creating bucket '{SUPABASE_BUCKET}'...")
        supabase.storage.create_bucket(SUPABASE_BUCKET, options={'public': True})
        print(f"✅ Bucket '{SUPABASE_BUCKET}' created successfully")
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    main() 