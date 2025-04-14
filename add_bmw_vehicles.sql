-- Add BMW vehicles to the database
INSERT INTO vehicles (id, year, make, model, is_custom, created_at)
VALUES 
(gen_random_uuid(), '2025', 'BMW', 'X5', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2025', 'BMW', 'X3', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2025', 'BMW', '3 Series', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2025', 'BMW', '5 Series', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2025', 'BMW', '7 Series', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2024', 'BMW', 'X5', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2024', 'BMW', 'X3', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2024', 'BMW', '3 Series', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2024', 'BMW', '5 Series', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2024', 'BMW', '7 Series', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2023', 'BMW', 'X5', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2023', 'BMW', 'X3', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2023', 'BMW', '3 Series', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2023', 'BMW', '5 Series', false, CURRENT_TIMESTAMP),
(gen_random_uuid(), '2023', 'BMW', '7 Series', false, CURRENT_TIMESTAMP); 