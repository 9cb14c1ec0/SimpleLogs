-- Migration: Multiple API keys per team
-- Creates api_keys table, migrates existing keys from teams, drops old columns

DO $$
BEGIN
    -- Create api_keys table if it doesn't exist yet
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'api_keys') THEN
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
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'teams' AND column_name = 'api_key_hash') THEN
            INSERT INTO api_keys (id, team_id, label, api_key_hash, api_key_prefix, created_at)
            SELECT gen_random_uuid(), id, 'default', api_key_hash, api_key_prefix, created_at
            FROM teams
            WHERE api_key_hash IS NOT NULL;
        END IF;

        RAISE NOTICE 'api_keys table created and data migrated successfully';
    END IF;

    -- Always drop old columns from teams if they still exist
    ALTER TABLE teams DROP COLUMN IF EXISTS api_key_hash;
    ALTER TABLE teams DROP COLUMN IF EXISTS api_key_prefix;
END $$;
