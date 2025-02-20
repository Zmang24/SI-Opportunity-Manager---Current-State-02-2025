-- First, drop existing foreign key constraints
ALTER TABLE opportunities DROP CONSTRAINT IF EXISTS opportunities_created_by_fkey;
ALTER TABLE opportunities DROP CONSTRAINT IF EXISTS opportunities_assigned_to_fkey;
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_user_id_fkey;
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_opportunity_id_fkey;
ALTER TABLE activity_log DROP CONSTRAINT IF EXISTS activity_log_user_id_fkey;
ALTER TABLE activity_log DROP CONSTRAINT IF EXISTS activity_log_opportunity_id_fkey;
ALTER TABLE files DROP CONSTRAINT IF EXISTS files_opportunity_id_fkey;
ALTER TABLE files DROP CONSTRAINT IF EXISTS files_uploader_id_fkey;

-- Add UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Update users table
ALTER TABLE users 
    ALTER COLUMN id DROP DEFAULT,
    ALTER COLUMN id SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN id SET DEFAULT uuid_generate_v4();

-- Update opportunities table
ALTER TABLE opportunities 
    ALTER COLUMN id DROP DEFAULT,
    ALTER COLUMN id SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN id SET DEFAULT uuid_generate_v4(),
    ALTER COLUMN created_by SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN assigned_to SET DATA TYPE UUID USING (uuid_generate_v4());

-- Update notifications table
ALTER TABLE notifications
    ALTER COLUMN id SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN user_id SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN opportunity_id SET DATA TYPE UUID USING (uuid_generate_v4());

-- Update activity_log table
ALTER TABLE activity_log
    ALTER COLUMN id SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN user_id SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN opportunity_id SET DATA TYPE UUID USING (uuid_generate_v4());

-- Update files table
ALTER TABLE files
    ALTER COLUMN id SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN opportunity_id SET DATA TYPE UUID USING (uuid_generate_v4()),
    ALTER COLUMN uploader_id SET DATA TYPE UUID USING (uuid_generate_v4());

-- Recreate foreign key constraints
ALTER TABLE opportunities 
    ADD CONSTRAINT opportunities_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id),
    ADD CONSTRAINT opportunities_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES users(id);

ALTER TABLE notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id),
    ADD CONSTRAINT notifications_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES opportunities(id);

ALTER TABLE activity_log
    ADD CONSTRAINT activity_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id),
    ADD CONSTRAINT activity_log_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES opportunities(id);

ALTER TABLE files
    ADD CONSTRAINT files_opportunity_id_fkey FOREIGN KEY (opportunity_id) REFERENCES opportunities(id),
    ADD CONSTRAINT files_uploader_id_fkey FOREIGN KEY (uploader_id) REFERENCES users(id); 