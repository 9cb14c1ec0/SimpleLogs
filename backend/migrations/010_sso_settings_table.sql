-- Migration: Add OpenID Connect (SSO) settings, edited from the admin UI

CREATE TABLE IF NOT EXISTS sso_settings (
    id INT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    issuer VARCHAR(500) NOT NULL DEFAULT '',
    client_id VARCHAR(255) NOT NULL DEFAULT '',
    client_secret_encrypted TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
