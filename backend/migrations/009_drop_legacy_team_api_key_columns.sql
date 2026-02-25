-- Migration: Drop leftover api_key columns from teams table
-- Migration 004 may have skipped the DROP COLUMN statements if the api_keys
-- table was already created by Tortoise's generate_schemas().

ALTER TABLE teams DROP COLUMN IF EXISTS api_key_hash;
ALTER TABLE teams DROP COLUMN IF EXISTS api_key_prefix;
