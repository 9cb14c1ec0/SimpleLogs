-- Migration: Convert logs.id from UUID to BIGINT (auto-increment)
-- This improves ORDER BY performance by using the primary key index
--
-- This migration only runs if the logs table has a UUID primary key.
-- Fresh installs will already have BIGINT from generate_schemas().

DO $$
BEGIN
    -- Check if the id column is UUID type (needs migration)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'logs' AND column_name = 'id' AND data_type = 'uuid'
    ) THEN
        -- 1. Add new BIGINT column with auto-increment
        ALTER TABLE logs ADD COLUMN new_id BIGSERIAL;

        -- 2. Reassign IDs in chronological order so older logs have lower IDs
        WITH ordered AS (
            SELECT id AS old_id, ROW_NUMBER() OVER (ORDER BY created_at ASC) AS rn
            FROM logs
        )
        UPDATE logs SET new_id = ordered.rn
        FROM ordered WHERE logs.id = ordered.old_id;

        -- 3. Reset the sequence to continue after the max ID
        PERFORM setval('logs_new_id_seq', COALESCE((SELECT MAX(new_id) FROM logs), 0) + 1, false);

        -- 4. Drop the old primary key constraint
        ALTER TABLE logs DROP CONSTRAINT logs_pkey;

        -- 5. Drop the old UUID column
        ALTER TABLE logs DROP COLUMN id;

        -- 6. Rename new column to id
        ALTER TABLE logs RENAME COLUMN new_id TO id;

        -- 7. Rename the sequence to match the column name
        ALTER SEQUENCE logs_new_id_seq RENAME TO logs_id_seq;

        -- 8. Add primary key constraint on new column
        ALTER TABLE logs ADD PRIMARY KEY (id);

        RAISE NOTICE 'Migrated logs.id from UUID to BIGINT';
    ELSE
        RAISE NOTICE 'logs.id is already BIGINT, skipping migration';
    END IF;

    -- 9. Add composite index if it doesn't exist (for both fresh and migrated)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_logs_team_id_id'
    ) THEN
        CREATE INDEX idx_logs_team_id_id ON logs(team_id, id DESC);
    END IF;
END $$;
