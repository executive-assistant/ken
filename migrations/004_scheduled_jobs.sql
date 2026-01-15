-- Scheduled jobs table for Orchestrator-scheduled worker execution
-- Run this after 003_workers.sql

CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255) NOT NULL,
    worker_id INTEGER REFERENCES workers(id) ON DELETE SET NULL,
    name VARCHAR(255),
    task TEXT NOT NULL,                  -- Concrete task description
    flow TEXT NOT NULL,                  -- Execution flow with conditions/loops
    due_time TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    cron VARCHAR(100),                   -- NULL = one-off, or cron expression (e.g., "0 9 * * *")
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    result TEXT                          -- Output from worker execution
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_due_time ON scheduled_jobs(due_time) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_user_id ON scheduled_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_thread_id ON scheduled_jobs(thread_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_worker_id ON scheduled_jobs(worker_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_status ON scheduled_jobs(status);

-- Comments for documentation
COMMENT ON TABLE scheduled_jobs IS 'Scheduled jobs that execute worker agents at specific times';
COMMENT ON COLUMN scheduled_jobs.worker_id IS 'Reference to the worker that executes this job';
COMMENT ON COLUMN scheduled_jobs.task IS 'Concrete task description (e.g., "Check Amazon price for B08X12345")';
COMMENT ON COLUMN scheduled_jobs.flow IS 'Execution flow (e.g., "fetch price → if < $100 notify, else log")';
COMMENT ON COLUMN scheduled_jobs.cron IS 'NULL for one-off, or cron expression for recurring jobs';
COMMENT ON COLUMN scheduled_jobs.result IS 'Output text from worker execution';
