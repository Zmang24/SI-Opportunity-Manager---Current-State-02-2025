# Supabase Setup Instructions for File Storage

## Overview

This guide will help you set up Supabase as a file storage solution for your application. Your application will continue to use its existing authentication system, and Supabase will be used solely for file storage.

## 1. Create a Supabase Account and Project

1. Go to [https://app.supabase.com/](https://app.supabase.com/) and sign up or log in
2. Create a new project with a name of your choice
3. Choose a strong database password and save it securely
4. Select a region closest to your users
5. Wait for your project to be created (this may take a few minutes)

## 2. Get Your API Keys

1. Once your project is created, go to the project dashboard
2. In the left sidebar, click on "Project Settings" and then "API"
3. You'll find two types of API keys:
   - **anon/public key**: For client-side operations with limited permissions
   - **service_role key**: For server-side operations with full admin access
4. Copy both keys and your Supabase URL for the next step

## 3. Create a Storage Bucket

1. In the left sidebar, click on "Storage"
2. Click the "New Bucket" button
3. Enter "opportunity-files" as the bucket name
4. Select "Private" to restrict access to authenticated requests
5. Click "Create bucket"

## 4. Configure Your Environment

1. Update your `.env` file with the following Supabase configuration:
   ```
   SUPABASE_URL=your-supabase-url
   SUPABASE_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-role-key
   SUPABASE_BUCKET=opportunity-files
   ```

2. Make sure to keep your service role key secure and never expose it in client-side code

## 5. Install Dependencies

Run the following command to install the required dependencies:

```bash
pip install supabase
```

## 6. Test Your Setup

Run the test script to verify that your Supabase storage integration is working correctly:

```bash
python test_app_supabase_integration.py
```

If all tests pass, your Supabase storage integration is working correctly.

## 7. Understanding the Implementation

The `SupabaseStorageService` class in `app/services/supabase_storage.py` provides the following functionality:

- **File Upload**: Store files in Supabase storage
- **File Download**: Download files from Supabase storage
- **File URL Generation**: Generate signed URLs for file access
- **File Existence Check**: Check if a file exists in storage
- **File Deletion**: Delete files from storage

The service uses the service role key to perform these operations, which means it has full admin access to your Supabase storage. This is appropriate since your application is handling authentication separately.

## 8. Security Considerations

- The service role key has full admin access to your Supabase project, so keep it secure
- Files are stored with private access, meaning they can only be accessed via signed URLs
- Signed URLs expire after a specified time (default: 1 hour)
- Your application is responsible for determining who can access which files

## 9. Troubleshooting

If you encounter issues:

1. Check that your Supabase URL and keys are correctly set in your `.env` file
2. Verify that the "opportunity-files" bucket exists in your Supabase project
3. Ensure that the Supabase service is running and accessible
4. Check the console output for specific error messages

## 10. Next Steps

Now that Supabase storage is set up, you can:

1. Migrate existing files to Supabase using the `migrate_files_to_supabase.py` script
2. Update your application code to use the `SupabaseStorageService` for file operations
3. Test the integration thoroughly with your application

Your application will now store files in Supabase, providing more reliable storage that's independent of your application server's file system. 