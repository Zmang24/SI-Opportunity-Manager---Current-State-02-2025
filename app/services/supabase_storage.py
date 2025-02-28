import os
import hashlib
from typing import Optional, Any, List, Dict
import mimetypes
import tempfile
import platform
import subprocess
from app.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, SUPABASE_BUCKET

from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseStorageService:
    """Service for interacting with Supabase Storage"""
    
    @staticmethod
    def get_supabase_client() -> Client:
        """
        Get a Supabase client using the service role key.
        
        Returns:
            Supabase client
        """
        # Check if Supabase URL and key are configured
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase URL and service key must be configured")
            
        # Always use the service role key for admin operations
        return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Hex digest of the hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def store_file(source_path: str, custom_path: Optional[str] = None) -> Optional[str]:
        """
        Store a file in Supabase storage.
        
        Args:
            source_path: Path to the source file
            custom_path: Optional custom path to use in storage
            
        Returns:
            Storage path if successful, None otherwise
        """
        try:
            # Get file info
            file_name = os.path.basename(source_path)
            file_hash = SupabaseStorageService.calculate_file_hash(source_path)
            
            # Determine storage path
            if custom_path:
                # Normalize path (replace backslashes with forward slashes)
                storage_path = custom_path.replace('\\', '/')
            else:
                # Use hash-based path to avoid duplicates
                file_ext = os.path.splitext(file_name)[1]
                storage_path = f"{file_hash}{file_ext}"
            
            # Upload file to Supabase
            supabase = SupabaseStorageService.get_supabase_client()
            with open(source_path, "rb") as f:
                # Upload without file_options to avoid type errors
                supabase.storage.from_(SUPABASE_BUCKET).upload(
                    path=storage_path,
                    file=f
                )
            
            return storage_path
        except Exception as e:
            print(f"Error storing file: {e}")
            return None
    
    @staticmethod
    def get_file_url(storage_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a URL for a file in Supabase storage.
        
        Args:
            storage_path: Path to the file in storage
            expires_in: Expiration time in seconds (default: 1 hour)
            
        Returns:
            File URL if successful, None otherwise
        """
        try:
            supabase = SupabaseStorageService.get_supabase_client()
            
            # Get signed URL with expiration
            result = supabase.storage.from_(SUPABASE_BUCKET).create_signed_url(
                path=storage_path,
                expires_in=expires_in
            )
            
            if result and 'signedURL' in result:
                return result['signedURL']
            return None
        except Exception as e:
            print(f"Error getting file URL: {e}")
            return None
    
    @staticmethod
    def file_exists(storage_path: str) -> bool:
        """
        Check if a file exists in Supabase storage.
        
        Args:
            storage_path: Path to the file in storage
            
        Returns:
            True if the file exists, False otherwise
        """
        try:
            supabase = SupabaseStorageService.get_supabase_client()
            
            # List files in the directory
            path_parts = storage_path.split('/')
            directory = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ''
            filename = path_parts[-1]
            
            files = supabase.storage.from_(SUPABASE_BUCKET).list(directory)
            
            # Check if the file exists
            for file in files:
                if file and hasattr(file, 'get') and file.get('name') == filename:
                    return True
                
            return False
        except Exception as e:
            print(f"Error checking if file exists: {e}")
            return False
    
    @staticmethod
    def download_file(storage_path: str, destination_path: Optional[str] = None) -> Optional[str]:
        """
        Download a file from Supabase storage.
        
        Args:
            storage_path: Path to the file in storage
            destination_path: Optional destination path
            
        Returns:
            Path to the downloaded file if successful, None otherwise
        """
        try:
            supabase = SupabaseStorageService.get_supabase_client()
            
            # Create a temporary file if no destination path is provided
            if not destination_path:
                file_ext = os.path.splitext(storage_path)[1]
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
                destination_path = temp_file.name
                temp_file.close()
            
            # Download the file
            with open(destination_path, 'wb') as f:
                res = supabase.storage.from_(SUPABASE_BUCKET).download(storage_path)
                f.write(res)
            
            return destination_path
        except Exception as e:
            print(f"Error downloading file: {e}")
            return None
    
    @staticmethod
    def open_file(storage_path: str) -> bool:
        """
        Open a file from Supabase storage with the default application.
        
        Args:
            storage_path: Path to the file in storage
            
        Returns:
            True if the file was opened successfully, False otherwise
        """
        try:
            # Download the file to a temporary location
            temp_path = SupabaseStorageService.download_file(storage_path)
            if not temp_path:
                return False
            
            # Open the file with the default application based on the OS
            system = platform.system()
            if system == 'Windows':
                os.startfile(temp_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', temp_path], check=True)
            else:  # Linux and other Unix-like
                subprocess.run(['xdg-open', temp_path], check=True)
            
            return True
        except Exception as e:
            print(f"Error opening file: {e}")
            return False
    
    @staticmethod
    def delete_file(storage_path: str) -> bool:
        """
        Delete a file from Supabase storage.
        
        Args:
            storage_path: Path to the file in storage
            
        Returns:
            True if the file was deleted successfully, False otherwise
        """
        try:
            supabase = SupabaseStorageService.get_supabase_client()
            # Delete the file
            supabase.storage.from_(SUPABASE_BUCKET).remove([storage_path])
            return True
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False 