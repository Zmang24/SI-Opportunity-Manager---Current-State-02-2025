-- Add started_at and work_time columns to opportunities table
ALTER TABLE opportunities
ADD COLUMN started_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN work_time INTERVAL; 