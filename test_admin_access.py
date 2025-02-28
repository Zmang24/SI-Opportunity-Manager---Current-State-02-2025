#!/usr/bin/env python
"""
Test Supabase admin access using service role key.
This script demonstrates how to bypass RLS policies for admin operations.
"""
import os
import tempfile
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # anon key
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # service role key
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "opportunity-files")

def test_admin_access():
    """Test admin access to Supabase storage using service role key."""
    if not SUPABASE_URL:
        print("Error: Supabase URL must be set in environment variables")
        return False
    
    # Check if service role key is available
    if not SUPABASE_SERVICE_KEY:
        print("⚠️ Warning: SUPABASE_SERVICE_KEY is not set in your .env file")
        print("You need to get your service role key from the Supabase dashboard:")
        print("1. Go to Project Settings > API")
        print("2. Copy the 'service_role' key")
        print("3. Add it to your .env file as SUPABASE_SERVICE_KEY=your-key")
        print("\nUsing anonymous key instead, which may result in permission errors.")
        client_key = SUPABASE_KEY
    else:
        print("✅ Using service role key for admin access")
        client_key = SUPABASE_SERVICE_KEY
    
    try:
        # Create Supabase client with appropriate key
        print(f"Connecting to Supabase at {SUPABASE_URL}...")
        supabase = create_client(SUPABASE_URL, client_key)
        print("✅ Connected to Supabase")
        
        # Check if our bucket exists
        print(f"Checking if bucket '{SUPABASE_BUCKET}' exists...")
        try:
            # List buckets (requires admin access)
            buckets = supabase.storage.list_buckets()
            bucket_exists = any(bucket.get('name') == SUPABASE_BUCKET for bucket in buckets)
            
            if not bucket_exists:
                print(f"❌ Bucket '{SUPABASE_BUCKET}' does not exist")
                
                # Try to create the bucket (requires admin access)
                if SUPABASE_SERVICE_KEY:
                    print(f"Attempting to create bucket '{SUPABASE_BUCKET}'...")
                    supabase.storage.create_bucket(SUPABASE_BUCKET, {'public': False})
                    print(f"✅ Bucket '{SUPABASE_BUCKET}' created successfully")
                    bucket_exists = True
            else:
                print(f"✅ Bucket '{SUPABASE_BUCKET}' exists")
            
            if bucket_exists:
                # List files in the bucket
                files = supabase.storage.from_(SUPABASE_BUCKET).list()
                print(f"Found {len(files)} files in the bucket")
                
                # Test file upload with a temporary file
                print("\nTesting file upload as admin...")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
                    temp_path = temp.name
                    temp.write(b"This is a test file uploaded with admin privileges.")
                
                try:
                    # Upload the file
                    file_path = "admin/test_file.txt"
                    with open(temp_path, "rb") as f:
                        supabase.storage.from_(SUPABASE_BUCKET).upload(
                            path=file_path,
                            file=f
                        )
                    print(f"✅ File uploaded to {file_path}")
                    
                    # Get a signed URL for the file
                    response = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(
                        path=file_path,
                        expires_in=3600  # 1 hour expiration
                    )
                    
                    if response and 'signedURL' in response:
                        signed_url = response['signedURL']
                        print(f"✅ Signed URL for uploaded file (expires in 1 hour):")
                        print(f"   {signed_url}")
                        print("\nThis URL can be shared with authenticated users.")
                    else:
                        print(f"❌ Failed to create signed URL for uploaded file")
                    
                    # Clean up
                    os.unlink(temp_path)
                    
                    # Try to delete the test file
                    print("\nDeleting test file...")
                    supabase.storage.from_(SUPABASE_BUCKET).remove([file_path])
                    print(f"✅ Test file deleted")
                
                except Exception as e:
                    print(f"❌ Error during file operations: {e}")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
        
        except Exception as e:
            print(f"❌ Error accessing storage: {e}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_admin_access() 