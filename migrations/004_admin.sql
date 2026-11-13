-- Admin flag: admins can use "Start new year". Safe to re-run.
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE app_users SET is_admin = TRUE WHERE username = 'lukas';

-- Make someone else an admin later with:
--   UPDATE app_users SET is_admin = TRUE WHERE username = 'verca';
