#!/usr/bin/env python
"""
Migrate existing files from local storage to Supabase.

This script will:
1. Scan the local storage directory for files
2. Upload each file to Supabase
3. Optionally perform a dry run without actually uploading
4. Limit the number of files to migrate if needed
"""
import os
import sys
import argparse
import logging
from typing import List, Tuple, Optional
from tqdm import tqdm

# Add the current directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.config import STORAGE_DIR, SUPABASE_BUCKET
    from app.services.supabase_storage import SupabaseStorageService
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("migration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("migration")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Migrate files from local storage to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without uploading files")
    parser.add_argument("--limit", type=int, help="Limit the number of files to migrate")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()

def normalize_path(path: str) -> str:
    """Convert backslashes to forward slashes for Supabase storage paths."""
    return path.replace('\\', '/')

def main() -> None:
    """Main migration function."""
    args = parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    logger.info(f"Starting migration from {STORAGE_DIR} to Supabase bucket '{SUPABASE_BUCKET}'")
    logger.info(f"Dry run: {args.dry_run}")
    
    if args.limit:
        logger.info(f"Limiting to {args.limit} files")
    
    # Check if storage directory exists
    if not os.path.exists(STORAGE_DIR):
        logger.error(f"Storage directory {STORAGE_DIR} does not exist")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Absolute path to storage dir: {os.path.abspath(STORAGE_DIR)}")
        sys.exit(1)
    
    # Collect all files to migrate
    file_paths: List[Tuple[str, str]] = []
    try:
        for root, _, files in os.walk(STORAGE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                # Get the relative path from the storage directory
                rel_path = os.path.relpath(file_path, STORAGE_DIR)
                # Normalize path for Supabase (use forward slashes)
                normalized_rel_path = normalize_path(rel_path)
                file_paths.append((file_path, normalized_rel_path))
    except Exception as e:
        logger.error(f"Error scanning storage directory: {str(e)}")
        sys.exit(1)
    
    # Limit the number of files if specified
    if args.limit:
        file_paths = file_paths[:args.limit]
    
    logger.info(f"Found {len(file_paths)} files to migrate.")
    
    if len(file_paths) == 0:
        logger.warning(f"No files found in {STORAGE_DIR}")
        sys.exit(0)
    
    if args.dry_run:
        logger.info("Dry run mode. No files will be uploaded.")
        for file_path, rel_path in file_paths:
            logger.info(f"Would upload {file_path} to {rel_path}")
        return
    
    # Perform the actual migration
    success_count = 0
    error_count = 0
    
    for file_path, rel_path in tqdm(file_paths, desc="Uploading files"):
        try:
            if args.verbose:
                logger.debug(f"Uploading {file_path} to {rel_path}")
            
            # Upload file to Supabase
            storage_path: Optional[str] = SupabaseStorageService.store_file(file_path, custom_path=rel_path)
            
            if storage_path:
                logger.info(f"Successfully uploaded {rel_path} to Supabase")
                success_count += 1
            else:
                logger.error(f"Failed to upload {rel_path}")
                error_count += 1
        except Exception as e:
            logger.error(f"Error uploading {rel_path}: {str(e)}")
            error_count += 1
    
    logger.info(f"Migration completed. {success_count} files uploaded successfully, {error_count} errors.")

if __name__ == "__main__":
    main() 