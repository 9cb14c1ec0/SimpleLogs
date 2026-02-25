-- Migration: Add WebAuthn challenge storage table
-- Replaces in-memory challenge store for multi-worker compatibility

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'webauthn_challenges') THEN
        CREATE TABLE webauthn_challenges (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            challenge_key VARCHAR(255) NOT NULL,
            challenge BYTEA NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL
        );

        CREATE UNIQUE INDEX idx_webauthn_challenges_key ON webauthn_challenges(challenge_key);

        RAISE NOTICE 'webauthn_challenges table created successfully';
    ELSE
        RAISE NOTICE 'webauthn_challenges table already exists, skipping';
    END IF;
END $$;
