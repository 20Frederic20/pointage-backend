-- Assisted punch and manager punch.
-- Idempotent: safe to run more than once. Applies to EXISTING read databases;
-- a new read database gets the same columns from src/sql/read_model.sql.

-- time_entries: validation status, assistant, selfie, optional location.
ALTER TABLE time_entries ALTER COLUMN location DROP NOT NULL;
ALTER TABLE time_entries ADD COLUMN IF NOT EXISTS assisted_by_user_id character varying(32);
ALTER TABLE time_entries ADD COLUMN IF NOT EXISTS photo_key character varying(255);
ALTER TABLE time_entries ADD COLUMN IF NOT EXISTS validation_status character varying(16) DEFAULT 'COUNTED' NOT NULL;
