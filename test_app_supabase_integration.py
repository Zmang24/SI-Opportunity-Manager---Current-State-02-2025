#!/usr/bin/env python
"""
Test the Supabase storage integration with the application.
"""
import os
import tempfile
from app.services.supabase_storage import SupabaseStorageService

def test_file_operations():
    """Test basic file operations with Supabase storage."""
    print("Testing Supabase storage integration...")
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
        temp_path = temp.name
        temp.write(b"This is a test file for Supabase storage integration.")
    
    try:
        # Test file upload
        print("\n1. Testing file upload...")
        storage_path = SupabaseStorageService.store_file(temp_path)
        if storage_path:
            print(f"✅ File uploaded successfully to: {storage_path}")
        else:
            print("❌ File upload failed")
            return False
        
        # Test getting file URL
        print("\n2. Testing get file URL...")
        file_url = SupabaseStorageService.get_file_url(storage_path, expires_in=3600)
        if file_url:
            print(f"✅ File URL (expires in 1 hour): {file_url}")
        else:
            print("❌ Failed to get file URL")
        
        # Test file existence check
        print("\n3. Testing file existence check...")
        exists = SupabaseStorageService.file_exists(storage_path)
        if exists:
            print(f"✅ File exists check passed")
        else:
            print("❌ File exists check failed")
        
        # Test file download
        print("\n4. Testing file download...")
        download_path = SupabaseStorageService.download_file(storage_path)
        if download_path:
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
        else:
            print("❌ File download failed")
        
        # Test file deletion
        print("\n5. Testing file deletion...")
        deleted = SupabaseStorageService.delete_file(storage_path)
        if deleted:
            print("✅ File deleted successfully")
        else:
            print("❌ File deletion failed")
        
        # Verify file no longer exists
        exists = SupabaseStorageService.file_exists(storage_path)
        if not exists:
            print("✅ File existence check after deletion passed")
        else:
            print("❌ File still exists after deletion")
        
        return True
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    test_file_operations() 