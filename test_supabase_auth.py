#!/usr/bin/env python
"""
Test Supabase authentication and private file access.
"""
import os
import tempfile
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "opportunity-files")

def test_auth_and_file_access():
    """Test authentication and private file access with Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Supabase URL and key must be set in environment variables")
        return False
    
    try:
        # Create Supabase client
        print(f"Connecting to Supabase at {SUPABASE_URL}...")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Check if our bucket exists
        print(f"Checking if bucket '{SUPABASE_BUCKET}' exists...")
        try:
            # Try to list files in the bucket to check if it exists
            files = supabase.storage.from_(SUPABASE_BUCKET).list()
            print(f"✅ Bucket '{SUPABASE_BUCKET}' exists")
            print(f"Found {len(files)} files in the bucket")
            
            # If files exist, try to get a signed URL for the first file
            if files:
                first_file = files[0]
                file_path = first_file.get('name', '')
                if file_path:
                    # Create a signed URL with a 60-second expiration
                    print(f"Creating signed URL for file: {file_path}")
                    response = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(
                        path=file_path,
                        expires_in=60
                    )
                    
                    if response and 'signedURL' in response:
                        signed_url = response['signedURL']
                        print(f"✅ Signed URL created (expires in 60 seconds): {signed_url}")
                        print("\nThis URL will only work for authenticated users and will expire after 60 seconds.")
                    else:
                        print(f"❌ Failed to create signed URL: {response}")
            
            # Test file upload with a temporary file
            print("\nTesting file upload to private bucket...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
                temp_path = temp.name
                temp.write(b"This is a test file for private Supabase storage.")
            
            try:
                # Upload the file
                file_path = "test/private_test_file.txt"
                with open(temp_path, "rb") as f:
                    supabase.storage.from_(SUPABASE_BUCKET).upload(
                        path=file_path,
                        file=f
                    )
                print(f"✅ File uploaded to {file_path}")
                
                # Get a signed URL for the file
                response = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(
                    path=file_path,
                    expires_in=60
                )
                
                if response and 'signedURL' in response:
                    signed_url = response['signedURL']
                    print(f"✅ Signed URL for uploaded file: {signed_url}")
                else:
                    print(f"❌ Failed to create signed URL for uploaded file")
                
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
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        except Exception as e:
            print(f"❌ Bucket '{SUPABASE_BUCKET}' does not exist or is not accessible: {e}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_auth_and_file_access() 