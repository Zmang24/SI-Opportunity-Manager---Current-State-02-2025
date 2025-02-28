#!/usr/bin/env python
"""
Test Supabase connectivity and file operations.
"""
import os
from dotenv import load_dotenv
from supabase import create_client
import tempfile

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "opportunity-files")

def main():
    """Test Supabase connectivity and file operations."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Supabase URL and key must be set in environment variables")
        return False
    
    try:
        # Create Supabase client
        print(f"Connecting to Supabase at {SUPABASE_URL}...")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # List all buckets
        print("Listing buckets...")
        try:
            buckets = supabase.storage.list_buckets()
            print(f"✅ Found {len(buckets)} buckets:")
            for bucket in buckets:
                print(f"  - {bucket.get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ Error listing buckets: {e}")
        
        # Check if our bucket exists
        print(f"Checking if bucket '{SUPABASE_BUCKET}' exists...")
        bucket_exists = False
        try:
            # Try to list files in the bucket to check if it exists
            files = supabase.storage.from_(SUPABASE_BUCKET).list()
            bucket_exists = True
            print(f"✅ Bucket '{SUPABASE_BUCKET}' exists")
            print(f"Found {len(files)} files in the bucket")
        except Exception as e:
            print(f"❌ Bucket '{SUPABASE_BUCKET}' does not exist or is not accessible: {e}")
        
        # Test file upload if bucket exists
        if bucket_exists:
            print("Testing file upload...")
            try:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
                    temp_path = temp.name
                    temp.write(b"Hello, Supabase!")
                
                # Upload the file
                file_path = "test/test_file.txt"
                with open(temp_path, "rb") as f:
                    supabase.storage.from_(SUPABASE_BUCKET).upload(
                        path=file_path,
                        file=f,
                        file_options={"content_type": "text/plain"}
                    )
                print(f"✅ File uploaded to {file_path}")
                
                # Get the file URL
                file_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_path)
                print(f"✅ File URL: {file_url}")
                
                # Clean up
                os.unlink(temp_path)
                
                # Try to delete the test file
                try:
                    supabase.storage.from_(SUPABASE_BUCKET).remove([file_path])
                    print(f"✅ Test file deleted")
                except Exception as e:
                    print(f"❌ Error deleting test file: {e}")
            
            except Exception as e:
                print(f"❌ Error testing file upload: {e}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    main() 