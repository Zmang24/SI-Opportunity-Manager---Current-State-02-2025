-- Convert existing timestamps to be timezone-aware
UPDATE opportunities 
SET 
    created_at = CASE WHEN created_at IS NOT NULL THEN created_at::TIMESTAMP AT TIME ZONE 'UTC' ELSE CURRENT_TIMESTAMP END,
    updated_at = CASE WHEN updated_at IS NOT NULL THEN updated_at::TIMESTAMP AT TIME ZONE 'UTC' ELSE CURRENT_TIMESTAMP END,
    completed_at = CASE WHEN completed_at IS NOT NULL THEN completed_at::TIMESTAMP AT TIME ZONE 'UTC' ELSE NULL END;

-- Ensure future timestamps will be timezone-aware and not null
ALTER TABLE opportunities 
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN updated_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP; 