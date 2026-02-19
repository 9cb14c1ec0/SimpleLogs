-- Migration: Convert logs table to two-level partitioned structure
-- Level 1: LIST by team_id (isolates each team's data)
-- Level 2: RANGE by created_at monthly (enables instant retention via partition drops)
--
-- Idempotency: Checks if logs is already partitioned before running.
-- Recovery: If a previous run failed mid-migration, detects logs_old and rolls back.

DO $$
DECLARE
    rec RECORD;
    month_rec RECORD;
    team_hex TEXT;
    team_part TEXT;
    default_sub TEXT;
    monthly_part TEXT;
    start_date DATE;
    end_date DATE;
    max_id BIGINT;
BEGIN
    -- Recover from a partially-applied migration: if logs_old exists, the previous
    -- run renamed the original table but failed before completing. Undo that work
    -- so we can retry cleanly.
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'logs_old'
    ) THEN
        RAISE NOTICE 'Detected partial migration state (logs_old exists), recovering...';
        DROP TABLE IF EXISTS logs CASCADE;
        DROP SEQUENCE IF EXISTS logs_id_seq;
        ALTER TABLE logs_old RENAME TO logs;
        IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'logs_old_id_seq') THEN
            ALTER SEQUENCE logs_old_id_seq RENAME TO logs_id_seq;
        END IF;
        RAISE NOTICE 'Recovery complete, proceeding with migration';
    END IF;

    -- Check if logs is already partitioned — if so, skip entire migration
    IF EXISTS (
        SELECT 1 FROM pg_partitioned_table pt
        JOIN pg_class c ON c.oid = pt.partrelid
        WHERE c.relname = 'logs'
    ) THEN
        RAISE NOTICE 'logs table is already partitioned, skipping migration';
        RETURN;
    END IF;

    -- 1. Rename existing table
    ALTER TABLE logs RENAME TO logs_old;

    -- Drop indexes that would conflict with the new partitioned table
    DROP INDEX IF EXISTS idx_logs_team_id_id;

    -- Rename the sequence if it exists so we can reuse the name
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'logs_id_seq') THEN
        ALTER SEQUENCE logs_id_seq RENAME TO logs_old_id_seq;
    END IF;

    -- 2. Create partitioned parent table
    --    PK includes team_id and created_at since they are partition keys.
    --    id uses a shared sequence for global uniqueness.
    CREATE SEQUENCE logs_id_seq;

    CREATE TABLE logs (
        id BIGINT NOT NULL DEFAULT nextval('logs_id_seq'),
        team_id UUID NOT NULL,
        "timestamp" TIMESTAMPTZ NOT NULL,
        level VARCHAR(5) NOT NULL,
        message TEXT NOT NULL,
        metadata JSONB,
        source VARCHAR(255),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (id, team_id, created_at)
    ) PARTITION BY LIST (team_id);

    ALTER SEQUENCE logs_id_seq OWNED BY logs.id;

    -- Create indexes on the parent (inherited by all partitions)
    CREATE INDEX idx_logs_team_id_id ON logs (team_id, id DESC);
    CREATE INDEX idx_logs_timestamp ON logs ("timestamp");
    CREATE INDEX idx_logs_level ON logs (level);
    CREATE INDEX idx_logs_source ON logs (source);
    CREATE INDEX idx_logs_created_at ON logs (created_at);

    -- 3. Create top-level default partition (safety net, itself sub-partitioned)
    CREATE TABLE logs_default PARTITION OF logs DEFAULT
        PARTITION BY RANGE (created_at);
    CREATE TABLE logs_default_default PARTITION OF logs_default DEFAULT;

    -- 4. For each existing team, create partitions
    FOR rec IN SELECT id FROM teams LOOP
        team_hex := REPLACE(rec.id::TEXT, '-', '');
        team_part := 'logs_' || team_hex;
        default_sub := team_part || '_default';

        -- Create team partition (sub-partitioned by range on created_at)
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF logs FOR VALUES IN (%L) PARTITION BY RANGE (created_at)',
            team_part, rec.id::TEXT
        );

        -- Create default sub-partition (safety net)
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF %I DEFAULT',
            default_sub, team_part
        );

        -- Create monthly sub-partitions for each month that has data
        FOR month_rec IN
            SELECT DISTINCT date_trunc('month', created_at)::DATE AS month_start
            FROM logs_old
            WHERE team_id = rec.id
            ORDER BY month_start
        LOOP
            start_date := month_rec.month_start;
            end_date := (month_rec.month_start + INTERVAL '1 month')::DATE;
            monthly_part := team_part || '_' || to_char(start_date, 'YYYY_MM');

            EXECUTE format(
                'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                monthly_part, team_part, start_date, end_date
            );
        END LOOP;
    END LOOP;

    -- 5. Copy all data from old table
    INSERT INTO logs (id, team_id, "timestamp", level, message, metadata, source, created_at)
    SELECT id, team_id, "timestamp", level, message, metadata, source, created_at
    FROM logs_old;

    -- 6. Reset the sequence to continue after the max ID
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM logs;
    PERFORM setval('logs_id_seq', max_id + 1, false);

    -- 7. Drop the old table and its sequence
    DROP TABLE logs_old;
    IF EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'logs_old_id_seq') THEN
        DROP SEQUENCE logs_old_id_seq;
    END IF;

    RAISE NOTICE 'Successfully partitioned logs table by team_id and created_at';
END $$;
