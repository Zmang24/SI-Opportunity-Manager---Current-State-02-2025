-- Add tracking fields to vehicles table
ALTER TABLE vehicles
ADD COLUMN created_by_id UUID REFERENCES users(id),
ADD COLUMN last_modified_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN last_modified_by_id UUID REFERENCES users(id),
ADD COLUMN notes VARCHAR; 