-- Phase 2 hardening. Run ONLY AFTER switching SUPABASE_KEY to the service_role key
-- (Supabase > Settings > API > service_role) in .env and Streamlit Cloud secrets,
-- and after confirming the app still works with it. Otherwise the app loses access.
--
-- service_role bypasses RLS; the public anon key (easy to extract) gets nothing.

DROP POLICY IF EXISTS "Enable all operations for gift_lists" ON gift_lists;
DROP POLICY IF EXISTS "Enable all operations for gifts" ON gifts;
DROP POLICY IF EXISTS "Enable all operations for gift_comments" ON gift_comments;

ALTER TABLE gift_lists    ENABLE ROW LEVEL SECURITY;
ALTER TABLE gifts         ENABLE ROW LEVEL SECURITY;
ALTER TABLE gift_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_users     ENABLE ROW LEVEL SECURITY;
-- No policies = anon/authenticated roles are denied everything.
