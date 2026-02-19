-- Migration: Multiple API keys per team
-- Creates api_keys table, migrates existing keys from teams, drops old columns

-- Idempotent: skip if api_keys table already exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'api_keys') THEN
        RAISE NOTICE 'api_keys table already exists, skipping migration';
        RETURN;
    END IF;

    -- Create the api_keys table
    CREATE TABLE api_keys (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
        label VARCHAR(255) NOT NULL DEFAULT '',
        api_key_hash VARCHAR(255) NOT NULL UNIQUE,
        api_key_prefix VARCHAR(20) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX idx_api_keys_team_id ON api_keys(team_id);
    CREATE INDEX idx_api_keys_hash ON api_keys(api_key_hash);

    -- Migrate existing keys from teams table
    INSERT INTO api_keys (id, team_id, label, api_key_hash, api_key_prefix, created_at)
    SELECT gen_random_uuid(), id, 'default', api_key_hash, api_key_prefix, created_at
    FROM teams
    WHERE api_key_hash IS NOT NULL;

    -- Drop old columns from teams
    ALTER TABLE teams DROP COLUMN IF EXISTS api_key_hash;
    ALTER TABLE teams DROP COLUMN IF EXISTS api_key_prefix;

    RAISE NOTICE 'api_keys table created and data migrated successfully';
END $$;
