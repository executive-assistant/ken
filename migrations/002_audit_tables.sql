-- User registry tables for tracking ownership across threads, files, and DuckDB data
-- These tables support merge/remove operations and provide audit history

-- Conversations table (metadata)
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    channel VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    message_count INT DEFAULT 0,
    summary TEXT,
    status VARCHAR(20) DEFAULT 'active'  -- active, removed, archived
);

-- Messages table (audit log)
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    message_id VARCHAR(255),  -- Channel-specific message ID
    role VARCHAR(20) NOT NULL,  -- human, assistant, system, tool
    content TEXT NOT NULL,
    metadata JSONB,  -- Channel-specific data, tool calls, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    token_count INT  -- For cost tracking
);

-- File paths ownership tracking
CREATE TABLE IF NOT EXISTS file_paths (
    thread_id VARCHAR(255) PRIMARY KEY,  -- Sanitized thread_id used as directory name
    user_id VARCHAR(255),  -- NULL until merge, then set to merged user_id
    channel VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- DuckDB database ownership tracking
CREATE TABLE IF NOT EXISTS duckdb_paths (
    thread_id VARCHAR(255) PRIMARY KEY,  -- Thread identifier
    db_path VARCHAR(512) NOT NULL,  -- Path to the DuckDB database file
    user_id VARCHAR(255),  -- NULL until merge, then set to merged user_id
    channel VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(channel);
CREATE INDEX IF NOT EXISTS idx_file_paths_user ON file_paths(user_id);
CREATE INDEX IF NOT EXISTS idx_duckdb_paths_user ON duckdb_paths(user_id);
CREATE INDEX IF NOT EXISTS idx_duckdb_paths_thread ON duckdb_paths(thread_id);

-- Trigger to update conversation updated_at and message_count
CREATE OR REPLACE FUNCTION update_conversation_timestamp() RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET updated_at = NOW(),
        message_count = message_count + 1
    WHERE conversation_id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_conversation ON messages;
CREATE TRIGGER trigger_update_conversation
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_timestamp();

-- Comments
COMMENT ON TABLE conversations IS 'Conversation metadata for audit and analytics';
COMMENT ON TABLE messages IS 'Message log for audit, compliance, and record keeping';
COMMENT ON TABLE file_paths IS 'File path ownership tracking for merge/remove operations';
COMMENT ON TABLE duckdb_paths IS 'DuckDB database ownership tracking for merge/remove operations';
