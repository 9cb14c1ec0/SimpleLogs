-- Migration: Add TOTP two-factor authentication support
-- Adds totp columns to users, creates recovery_codes table

DO $$
BEGIN
    -- Add TOTP columns to users table
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'totp_secret_encrypted'
    ) THEN
        ALTER TABLE users ADD COLUMN totp_secret_encrypted TEXT NULL;
        ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;
        RAISE NOTICE 'Added TOTP columns to users table';
    ELSE
        RAISE NOTICE 'TOTP columns already exist on users table, skipping';
    END IF;

    -- Create recovery_codes table
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'recovery_codes') THEN
        CREATE TABLE recovery_codes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code_hash VARCHAR(255) NOT NULL,
            used BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX idx_recovery_codes_user_id ON recovery_codes(user_id);

        RAISE NOTICE 'recovery_codes table created successfully';
    ELSE
        RAISE NOTICE 'recovery_codes table already exists, skipping';
    END IF;
END $$;
