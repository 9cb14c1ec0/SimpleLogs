-- Migration: Add WebAuthn passkey credentials table
-- Stores registered passkeys for passwordless authentication

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'passkey_credentials') THEN
        CREATE TABLE passkey_credentials (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            credential_id BYTEA NOT NULL,
            public_key BYTEA NOT NULL,
            sign_count BIGINT NOT NULL DEFAULT 0,
            transports TEXT NULL,
            name VARCHAR(255) NOT NULL DEFAULT 'Passkey',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMPTZ NULL
        );

        CREATE UNIQUE INDEX idx_passkey_credentials_credential_id ON passkey_credentials(credential_id);
        CREATE INDEX idx_passkey_credentials_user_id ON passkey_credentials(user_id);

        RAISE NOTICE 'passkey_credentials table created successfully';
    ELSE
        RAISE NOTICE 'passkey_credentials table already exists, skipping';
    END IF;
END $$;
