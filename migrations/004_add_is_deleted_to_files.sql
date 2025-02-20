-- Add is_deleted column to files table with default value of false
ALTER TABLE files ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT false; 