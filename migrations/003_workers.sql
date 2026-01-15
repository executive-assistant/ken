-- Workers table for Orchestrator-spawned worker agents
-- Run this after 002_reminders.sql

CREATE TABLE IF NOT EXISTS workers (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    tools TEXT[] NOT NULL,              -- Array of tool names assigned to this worker
    prompt TEXT NOT NULL,               -- System prompt for the worker
    status VARCHAR(20) DEFAULT 'active', -- active, archived, deleted
    created_at TIMESTAMP DEFAULT NOW(),
    archived_at TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_workers_user_id ON workers(user_id);
CREATE INDEX IF NOT EXISTS idx_workers_thread_id ON workers(thread_id);
CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status);

-- Comments for documentation
COMMENT ON TABLE workers IS 'Worker agents spawned by Orchestrator for specific tasks';
COMMENT ON COLUMN workers.tools IS 'Array of tool names (e.g., ["web_search", "execute_python"])';
COMMENT ON COLUMN workers.prompt IS 'System prompt that defines the worker''s behavior';
COMMENT ON COLUMN workers.status IS 'active = in use, archived = no longer needed, deleted = removed';
