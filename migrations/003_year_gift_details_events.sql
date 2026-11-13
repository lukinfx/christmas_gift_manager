-- Phase 3: year archive, gift link/price/image, activity events.
-- Additive only: no existing data is changed except backfilling gift_lists.year.
-- Run in the Supabase SQL editor. Safe to re-run.

-- 1) Year archive ----------------------------------------------------------
ALTER TABLE gift_lists ADD COLUMN IF NOT EXISTS year INT;
-- Old lists get the year they were created in (last year's data -> 2025).
UPDATE gift_lists SET year = EXTRACT(YEAR FROM created_at)::int WHERE year IS NULL;
-- New lists default to the current year.
ALTER TABLE gift_lists ALTER COLUMN year SET DEFAULT EXTRACT(YEAR FROM now())::int;
ALTER TABLE gift_lists ALTER COLUMN year SET NOT NULL;
ALTER TABLE gift_lists ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_gift_lists_year ON gift_lists(year);

-- 2) Gift details ----------------------------------------------------------
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS url        TEXT;
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS price      NUMERIC(10,2) CHECK (price IS NULL OR price >= 0);
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS image_url  TEXT;
ALTER TABLE gifts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_gifts_updated_at ON gifts;
CREATE TRIGGER trg_gifts_updated_at BEFORE UPDATE ON gifts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 3) Activity events (feed, "new since last visit", notifications) ---------
-- gift_name is copied so events still read well after a gift is deleted.
CREATE TABLE IF NOT EXISTS gift_events (
    id         BIGSERIAL PRIMARY KEY,
    list_id    BIGINT NOT NULL REFERENCES gift_lists(id) ON DELETE CASCADE,
    gift_id    BIGINT REFERENCES gifts(id) ON DELETE SET NULL,
    gift_name  TEXT,
    actor      TEXT NOT NULL,
    kind       TEXT NOT NULL,   -- gift_added | want_to_buy | want_to_buy_shared | bought | comment | released
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_gift_events_list_created ON gift_events(list_id, created_at DESC);
ALTER TABLE gift_events ENABLE ROW LEVEL SECURITY;  -- no policy: service_role only

-- 4) Remember when each person last looked, for the "new activity" badge ----
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
