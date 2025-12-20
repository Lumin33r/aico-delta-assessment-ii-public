-- =============================================================================
-- AI Personal Tutor - PostgreSQL Initialization Script
-- =============================================================================
-- This script runs automatically when the PostgreSQL container starts
-- for the first time. It creates the necessary tables and indexes.
-- =============================================================================

-- Podcasts table: Logs all podcast generation events
CREATE TABLE IF NOT EXISTS podcasts (
    id SERIAL PRIMARY KEY,
    source_url TEXT NOT NULL,
    title TEXT,
    audio_path TEXT,
    status VARCHAR(50) DEFAULT 'created',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_podcasts_url ON podcasts(source_url);
CREATE INDEX IF NOT EXISTS idx_podcasts_status ON podcasts(status);
CREATE INDEX IF NOT EXISTS idx_podcasts_created ON podcasts(created_at DESC);

-- Grant permissions (if connecting with different user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aitutor;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO aitutor;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'AI Tutor database initialized successfully at %', NOW();
END $$;
