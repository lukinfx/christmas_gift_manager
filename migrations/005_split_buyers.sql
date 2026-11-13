-- Split buying: remember everyone who shares the cost of a gift (equal parts).
-- Run in the Supabase SQL editor. Safe to re-run.

ALTER TABLE gifts ADD COLUMN IF NOT EXISTS split_buyers TEXT[] NOT NULL DEFAULT '{}';

-- Existing split gifts only knew one buyer: make that person the first participant.
UPDATE gifts
SET split_buyers = ARRAY[interested_buyer]
WHERE status = 'want_to_buy_shared'
  AND interested_buyer IS NOT NULL
  AND cardinality(split_buyers) = 0;
