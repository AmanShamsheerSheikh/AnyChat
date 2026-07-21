CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_name VARCHAR(255) UNIQUE NOT NULL,
    api_key UUID DEFAULT gen_random_uuid() UNIQUE
);

CREATE TABLE IF NOT EXISTS jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(user_id),
    status      VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    gpu_id      VARCHAR(255),
    prompt      TEXT NOT NULL,
    result      TEXT,
    error       TEXT,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);