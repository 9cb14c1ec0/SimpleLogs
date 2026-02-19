-- Migration: Add user_id column to logs
-- Allows first-class filtering by user identifier instead of relying on metadata JSONB

DO $$
BEGIN
    -- Add user_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'logs' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE logs ADD COLUMN user_id VARCHAR(255);
        RAISE NOTICE 'Added user_id column to logs';
    ELSE
        RAISE NOTICE 'user_id column already exists, skipping';
    END IF;

    -- Add composite index for per-team user filtering
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_logs_team_id_user_id'
    ) THEN
        CREATE INDEX idx_logs_team_id_user_id ON logs (team_id, user_id);
        RAISE NOTICE 'Created index idx_logs_team_id_user_id';
    ELSE
        RAISE NOTICE 'Index idx_logs_team_id_user_id already exists, skipping';
    END IF;
END $$;
