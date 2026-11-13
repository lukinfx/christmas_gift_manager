-- Phase 2: family members allowed to sign in with Google.
-- Run in the Supabase SQL editor. Safe to re-run.
-- `username` stays the key used in gifts.added_by / interested_buyer / bought_by /
-- gift_comments.username / gift_lists.recipients, so all old data stays linked.
-- Emails are NOT stored here (this file is committed). See seed_users.local.sql.

CREATE TABLE IF NOT EXISTS app_users (
    username     TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE CHECK (email = lower(email))
);

ALTER TABLE app_users ENABLE ROW LEVEL SECURITY;
