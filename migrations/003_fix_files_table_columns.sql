-- Rename path column to storage_path
ALTER TABLE files RENAME COLUMN path TO storage_path;

-- Drop the data column as it's not used in the model
ALTER TABLE files DROP COLUMN data; 