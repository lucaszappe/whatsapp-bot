CREATE TABLE user_sessions (
    phone           TEXT PRIMARY KEY
                    REFERENCES subscribers(phone) ON DELETE CASCADE,
    last_response_id TEXT NOT NULL,
    last_seen_utc    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);