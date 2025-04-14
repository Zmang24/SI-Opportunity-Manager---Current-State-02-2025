-- Check if VIN column exists in opportunities table
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM 
    information_schema.columns 
WHERE 
    table_name = 'opportunities' 
AND 
    column_name = 'vin'; 