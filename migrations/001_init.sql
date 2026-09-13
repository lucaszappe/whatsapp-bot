-- 001_init.sql

-- Subscribers table
CREATE TABLE IF NOT EXISTS subscribers (
    phone TEXT PRIMARY KEY,
    plan  TEXT NOT NULL,
    monthly_token_limit INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage log
CREATE TABLE IF NOT EXISTS usage_log (
    id BIGSERIAL PRIMARY KEY,
    phone_fk TEXT REFERENCES subscribers(phone),
    ts TIMESTAMPTZ DEFAULT NOW(),
    prompt_tokens INT,
    completion_tokens INT
);

-- Monthly usage view
CREATE OR REPLACE VIEW usage_tokens_month AS
SELECT phone_fk,
       SUM(prompt_tokens + completion_tokens) AS tokens_month
FROM usage_log
WHERE date_trunc('month', ts) = date_trunc('month', CURRENT_DATE)
GROUP BY phone_fk;