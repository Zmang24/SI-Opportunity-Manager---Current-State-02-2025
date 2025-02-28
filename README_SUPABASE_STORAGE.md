# Supabase Storage Integration

This document provides instructions for using Supabase as a file storage solution in the SI Opportunity Manager application.

## Overview

The application uses Supabase Storage for file management while maintaining its own authentication system. This integration allows for:

- Secure file uploads
- Controlled file access through signed URLs
- Reliable file storage independent of the application server

## Configuration

The Supabase storage integration requires the following environment variables in your `.env` file:

```
SUPABASE_URL=https://uizmncjqkjkuchzjckzn.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_BUCKET=opportunity-files
```

## Usage

### Uploading Files

To upload a file to Supabase storage:

```python
from app.services.supabase_storage import SupabaseStorageService

# Upload a file
file_path = "/path/to/local/file.pdf"
storage_path = SupabaseStorageService.store_file(file_path)

# Upload with a custom path
custom_path = "user_123/documents/file.pdf"
storage_path = SupabaseStorageService.store_file(file_path, custom_path=custom_path)
```

### Retrieving File URLs

To get a signed URL for accessing a file:

```python
from app.services.supabase_storage import SupabaseStorageService

# Get a file URL that expires in 1 hour (default)
file_url = SupabaseStorageService.get_file_url("path/to/file.pdf")

# Get a file URL with custom expiration (in seconds)
file_url = SupabaseStorageService.get_file_url("path/to/file.pdf", expires_in=86400)  # 24 hours
```

### Checking File Existence

To check if a file exists:

```python
from app.services.supabase_storage import SupabaseStorageService

exists = SupabaseStorageService.file_exists("path/to/file.pdf")
```

### Downloading Files

To download a file:

```python
from app.services.supabase_storage import SupabaseStorageService

# Download to a specific location
local_path = SupabaseStorageService.download_file("path/to/file.pdf", "/local/download/path.pdf")

# Download to a temporary file
temp_file_path = SupabaseStorageService.download_file("path/to/file.pdf")
```

### Opening Files

To open a file directly:

```python
from app.services.supabase_storage import SupabaseStorageService

# Open a file and get its content
with SupabaseStorageService.open_file("path/to/file.pdf") as file:
    content = file.read()
```

### Deleting Files

To delete a file:

```python
from app.services.supabase_storage import SupabaseStorageService

success = SupabaseStorageService.delete_file("path/to/file.pdf")
```

## Migrating Existing Files

A migration script is provided to move existing files from local storage to Supabase:

```bash
# Perform a dry run (no actual uploads)
python migrate_files_to_supabase.py --dry-run

# Migrate all files
python migrate_files_to_supabase.py

# Migrate a limited number of files
python migrate_files_to_supabase.py --limit 100

# Enable verbose output
python migrate_files_to_supabase.py --verbose
```

### Migration Notes

- The migration script automatically converts Windows-style backslashes (`\`) to forward slashes (`/`) for compatibility with Supabase storage paths.
- Files are uploaded with the same relative path structure as they have in the local storage.
- The migration process logs all activities to `migration.log` for reference.
- All 6 PDF files from the local storage have been successfully migrated to Supabase.

## Path Handling

When working with Supabase storage paths:

- Always use forward slashes (`/`) in storage paths, even on Windows systems
- The `SupabaseStorageService.store_file` method automatically converts backslashes to forward slashes
- When referencing files directly, ensure paths are normalized (e.g., `2025/02/file.pdf` not `2025\02\file.pdf`)

## Security Considerations

- The application uses Supabase's service role key to manage files, bypassing RLS policies
- File access is controlled through signed URLs with expiration times
- Keep your service role key secure and never expose it to clients
- Consider implementing additional access controls in your application logic

## Troubleshooting

### Common Issues

1. **File Upload Fails**
   - Check that your Supabase bucket exists
   - Verify that your service role key has the correct permissions
   - Ensure the file exists and is readable
   - Make sure paths use forward slashes, not backslashes

2. **Cannot Access Files**
   - Verify that you're using a valid signed URL
   - Check if the URL has expired
   - Ensure the file exists in the bucket
   - Confirm that the path is correctly formatted with forward slashes

3. **Migration Script Errors**
   - Check the migration.log file for detailed error messages
   - Verify that your local storage directory is correctly configured
   - Run with the `--verbose` flag for more detailed output

## Testing

To test the Supabase storage integration:

```bash
# Run the standalone test
python test_supabase_standalone.py

# Run the application integration test
python test_app_supabase_integration.py
``` 