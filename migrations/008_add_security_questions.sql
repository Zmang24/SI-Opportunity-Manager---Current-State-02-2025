-- Add security question fields to users table
ALTER TABLE users 
ADD COLUMN security_question_1 VARCHAR(255),
ADD COLUMN security_answer_1 VARCHAR(255),
ADD COLUMN security_question_2 VARCHAR(255),
ADD COLUMN security_answer_2 VARCHAR(255); 