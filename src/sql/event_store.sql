-- Write database: the event store and what commands write in the same
-- transaction (unique keys, outbox), plus auth's own tables.
-- Safe to run more than once, on a new database or on the existing
-- pointage_db (where the old state tables stay until the import is checked).

-- Every domain event of every aggregate, never updated nor deleted.
CREATE TABLE IF NOT EXISTS events (
    id VARCHAR(64) PRIMARY KEY,                -- the event's own id
    global_position BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE,
    stream_type VARCHAR(64) NOT NULL,          -- e.g. identity.site
    stream_id VARCHAR(32) NOT NULL,            -- the aggregate id
    stream_version INTEGER NOT NULL,           -- 1, 2, 3… within the stream
    event_name VARCHAR(255) NOT NULL,          -- e.g. users.site.created
    payload JSONB NOT NULL,                    -- the event's data
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    version_id INTEGER DEFAULT 1 NOT NULL,
    -- Optimistic concurrency: two writers cannot both append version N.
    CONSTRAINT uq_events_stream_version UNIQUE (stream_id, stream_version)
);

CREATE INDEX IF NOT EXISTS ix_events_stream_type ON events (stream_type);
-- Lookups on payload values (employee_id, directory_id…): payload @> '{...}'.
CREATE INDEX IF NOT EXISTS ix_events_payload ON events USING GIN (payload jsonb_path_ops);

-- Values held by one stream at a time (an email, an employee number, the
-- principal site of a directory…), reserved in the same transaction as the
-- events that set them.
CREATE TABLE IF NOT EXISTS unique_keys (
    id VARCHAR(32) PRIMARY KEY,
    scope VARCHAR(64) NOT NULL,                -- e.g. identity.user.email
    key VARCHAR(255) NOT NULL,
    stream_id VARCHAR(32) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    version_id INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT uq_unique_keys_scope_key UNIQUE (scope, key)
);

-- Transactional outbox (unchanged, same definition as src/table.sql).
CREATE TABLE IF NOT EXISTS outbox (
    id VARCHAR(32) PRIMARY KEY,
    event_id VARCHAR(255) NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,
    flush_counter INTEGER DEFAULT 0,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_outbox_status ON outbox (status);

-- auth: refresh tokens (hashed, rotated per family) and email login codes.
-- They stay state tables (short-lived technical data, not event-sourced).
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,
    family_id VARCHAR(32) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    session_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash)
);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_family_id ON refresh_tokens (family_id);

CREATE TABLE IF NOT EXISTS login_codes (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    consumed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1 NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_login_codes_user_id ON login_codes (user_id);

-- On the existing pointage_db: users are no longer rows of `users` here
-- (they are streams), so auth's tables cannot reference that table anymore.
ALTER TABLE refresh_tokens DROP CONSTRAINT IF EXISTS refresh_tokens_user_id_fkey;
ALTER TABLE login_codes DROP CONSTRAINT IF EXISTS login_codes_user_id_fkey;
