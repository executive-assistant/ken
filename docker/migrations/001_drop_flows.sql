-- Drop flows and mini-agents tables
-- Migration: 001_drop_flows
-- Date: 2026-02-11
-- Description: Remove mini agents & flows feature database tables

-- Drop scheduled_flows table (if exists)
DROP TABLE IF EXISTS scheduled_flows CASCADE;

-- Drop agent_registry table (if exists)
DROP TABLE IF EXISTS agent_registry CASCADE;

-- Drop flow_projects table (if exists) - may not exist in all installations
DROP TABLE IF EXISTS flow_projects CASCADE;

-- Note: scheduled_flows had indexes that will be automatically dropped:
-- - idx_scheduled_flows_due_time
-- - idx_scheduled_flows_thread_id
-- - idx_scheduled_flows_status
