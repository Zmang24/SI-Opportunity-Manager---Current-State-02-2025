#!/usr/bin/env python
"""
Standalone test for Supabase storage integration.
This script doesn't depend on the app's initialization.
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
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "opportunity-files")

def test_supabase_storage():
    """Test basic file operations with Supabase storage."""
    print("Testing Supabase storage integration...")
    
    # Check if Supabase configuration is available
    if not SUPABASE_URL or not (SUPABASE_KEY or SUPABASE_SERVICE_KEY):
        print("❌ Error: Supabase URL and key must be set in environment variables")
        return False
    
    # Use service key if available, otherwise use anon key
    key = SUPABASE_SERVICE_KEY or SUPABASE_KEY
    print(f"Using Supabase URL: {SUPABASE_URL}")
    print(f"Using bucket: {SUPABASE_BUCKET}")
    
    try:
        # Create Supabase client
        print("\nConnecting to Supabase...")
        supabase = create_client(SUPABASE_URL, key)
        print("✅ Connected to Supabase")
        
        # Check if bucket exists
        print(f"\nChecking if bucket '{SUPABASE_BUCKET}' exists...")
        try:
            # List buckets
            buckets = supabase.storage.list_buckets()
            bucket_names = [bucket.name for bucket in buckets if hasattr(bucket, 'name')]
            
            if SUPABASE_BUCKET in bucket_names:
                print(f"✅ Bucket '{SUPABASE_BUCKET}' exists")
            else:
                print(f"❌ Bucket '{SUPABASE_BUCKET}' does not exist")
                print("Attempting to create bucket...")
                supabase.storage.create_bucket(SUPABASE_BUCKET)
                print(f"✅ Bucket '{SUPABASE_BUCKET}' created")
        except Exception as e:
            print(f"❌ Error checking/creating bucket: {e}")
            return False
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
            temp_path = temp.name
            temp.write(b"This is a test file for Supabase storage integration.")
        
        try:
            # Test file upload
            print("\n1. Testing file upload...")
            storage_path = "test_file.txt"
            
            with open(temp_path, "rb") as f:
                supabase.storage.from_(SUPABASE_BUCKET).upload(
                    path=storage_path,
                    file=f
                )
            print(f"✅ File uploaded successfully to: {storage_path}")
            
            # Test getting file URL
            print("\n2. Testing get file URL...")
            result = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(
                path=storage_path,
                expires_in=3600
            )
            
            if result and 'signedURL' in result:
                file_url = result['signedURL']
                print(f"✅ File URL (expires in 1 hour): {file_url}")
            else:
                print("❌ Failed to get file URL")
            
            # Test file existence check
            print("\n3. Testing file existence check...")
            files = supabase.storage.from_(SUPABASE_BUCKET).list()
            file_exists = any(f.get('name') == storage_path for f in files if hasattr(f, 'get'))
            
            if file_exists:
                print(f"✅ File exists check passed")
            else:
                print("❌ File exists check failed")
            
            # Test file download
            print("\n4. Testing file download...")
            download_path = os.path.join(tempfile.gettempdir(), "downloaded_test_file.txt")
            
            with open(download_path, 'wb') as f:
                res = supabase.storage.from_(SUPABASE_BUCKET).download(storage_path)
                f.write(res)
            
            print(f"✅ File downloaded to: {download_path}")
            
            # Verify file contents
            with open(download_path, 'rb') as f:
                content = f.read()
                if b"This is a test file for Supabase storage integration." in content:
                    print("✅ File content verification passed")
                else:
                    print("❌ File content verification failed")
            
            # Clean up downloaded file
            os.unlink(download_path)
            
            # Test file deletion
            print("\n5. Testing file deletion...")
            supabase.storage.from_(SUPABASE_BUCKET).remove([storage_path])
            print("✅ File deleted successfully")
            
            # Verify file no longer exists
            files = supabase.storage.from_(SUPABASE_BUCKET).list()
            file_exists = any(f.get('name') == storage_path for f in files if hasattr(f, 'get'))
            
            if not file_exists:
                print("✅ File existence check after deletion passed")
            else:
                print("❌ File still exists after deletion")
            
            return True
        
        except Exception as e:
            print(f"❌ Error during file operations: {e}")
            return False
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return False

if __name__ == "__main__":
    test_supabase_storage() 