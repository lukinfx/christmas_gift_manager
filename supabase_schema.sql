-- Create gift_lists table
CREATE TABLE gift_lists (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    recipients TEXT[] NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create gifts table
CREATE TABLE gifts (
    id BIGSERIAL PRIMARY KEY,
    list_id BIGINT NOT NULL REFERENCES gift_lists(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    added_by TEXT NOT NULL,
    status TEXT DEFAULT 'available',
    interested_buyer TEXT,
    bought_by TEXT,
    bought_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create gift_comments table
CREATE TABLE gift_comments (
    id BIGSERIAL PRIMARY KEY,
    gift_id BIGINT NOT NULL REFERENCES gifts(id) ON DELETE CASCADE,
    comment TEXT NOT NULL,
    username TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (optional, for production)
ALTER TABLE gift_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE gifts ENABLE ROW LEVEL SECURITY;
ALTER TABLE gift_comments ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all operations for now, adjust as needed)
CREATE POLICY "Enable all operations for gift_lists" ON gift_lists FOR ALL USING (true);
CREATE POLICY "Enable all operations for gifts" ON gifts FOR ALL USING (true);
CREATE POLICY "Enable all operations for gift_comments" ON gift_comments FOR ALL USING (true);

-- Create indexes for better performance
CREATE INDEX idx_gifts_list_id ON gifts(list_id);
CREATE INDEX idx_gift_comments_gift_id ON gift_comments(gift_id);
