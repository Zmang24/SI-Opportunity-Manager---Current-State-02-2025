-- Add original_name column to files table
ALTER TABLE files ADD COLUMN original_name VARCHAR(255) NOT NULL DEFAULT '';

-- Remove the default after adding the column
ALTER TABLE files ALTER COLUMN original_name DROP DEFAULT; 