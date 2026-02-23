-- Migration: Add TOTP attempt tracking table for brute-force protection

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'totp_attempts') THEN
        CREATE TABLE totp_attempts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            jti VARCHAR(36) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX idx_totp_attempts_jti ON totp_attempts(jti);

        RAISE NOTICE 'totp_attempts table created successfully';
    ELSE
        RAISE NOTICE 'totp_attempts table already exists, skipping';
    END IF;
END $$;
