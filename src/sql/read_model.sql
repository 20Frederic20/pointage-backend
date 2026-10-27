-- Read database: the read models (one table per aggregate), fed by the
-- projection runner from the event store of the write database.
-- Query handlers read here; nothing else writes here.
-- Run once, on an empty read database (docker runs it on a new volume).
--
-- Same tables and columns as the state tables of src/table.sql (the
-- historical single-database schema), generated from it, plus the
-- projection checkpoint. To rebuild every read model from the events:
--   TRUNCATE <every read-model table below> CASCADE;
--   TRUNCATE projection_failures;
--   UPDATE projection_checkpoints SET position = 0;
-- and the runner replays the whole event store.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS absence_types (
    id character varying(32) NOT NULL,
    name character varying(100) NOT NULL,
    paid boolean NOT NULL,
    counts_as_work_time boolean NOT NULL,
    deducts_balance boolean NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS absences (
    id character varying(32) NOT NULL,
    employee_id character varying(32) NOT NULL,
    absence_type_id character varying(32) NOT NULL,
    start_at timestamp with time zone NOT NULL,
    end_at timestamp with time zone NOT NULL,
    reason character varying(512) NOT NULL,
    status character varying(32) NOT NULL,
    justification_reference character varying(255),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1,
    CONSTRAINT ck_absences_period CHECK ((end_at > start_at))
);

CREATE TABLE IF NOT EXISTS anomalies (
    id character varying(32) NOT NULL,
    time_entry_id character varying(32) NOT NULL,
    type character varying(50) NOT NULL,
    severity character varying(50) NOT NULL,
    status character varying(50) NOT NULL,
    description text,
    detected_at timestamp with time zone NOT NULL,
    resolved_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS calculation_rule_versions (
    id character varying(32) NOT NULL,
    rule_version integer NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    min_break_duration interval NOT NULL,
    break_threshold interval NOT NULL,
    max_daily_work_duration interval NOT NULL,
    max_amplitude interval NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS daily_time_results (
    id character varying(32) NOT NULL,
    employee_id character varying(32) NOT NULL,
    period_id character varying(32) NOT NULL,
    calculation_rule_version_id character varying(32) NOT NULL,
    work_date date NOT NULL,
    planned_duration interval NOT NULL,
    worked_duration interval NOT NULL,
    break_duration interval NOT NULL,
    absence_duration interval NOT NULL,
    late_duration interval NOT NULL,
    status character varying(16) NOT NULL,
    calculated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS directories (
    id character varying(32) NOT NULL,
    code character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1 NOT NULL,
    parent_directory_id character varying(32)
);

CREATE TABLE IF NOT EXISTS employee_assignments (
    id character varying(32) NOT NULL,
    employee_id character varying(32) NOT NULL,
    directory_id character varying(32) NOT NULL,
    site_id character varying(32) NOT NULL,
    start_date date NOT NULL,
    end_date date,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_employee_assignments_dates CHECK (((end_date IS NULL) OR (end_date >= start_date)))
);

CREATE TABLE IF NOT EXISTS employee_schedules (
    id character varying(32) NOT NULL,
    employee_id character varying(32) NOT NULL,
    time_profile_version_id character varying(32) NOT NULL,
    start_date date NOT NULL,
    end_date date,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1,
    CONSTRAINT ck_employee_schedules_dates CHECK (((end_date IS NULL) OR (end_date >= start_date)))
);

CREATE TABLE IF NOT EXISTS employees (
    id character varying(32) NOT NULL,
    user_id character varying(32) NOT NULL,
    employee_number character varying(20) NOT NULL,
    phone character varying(20),
    is_active boolean DEFAULT false NOT NULL,
    role character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS periods (
    id character varying(32) NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    status character varying(16) NOT NULL,
    closed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1,
    CONSTRAINT ck_periods_dates CHECK ((end_date >= start_date))
);

CREATE TABLE IF NOT EXISTS regularization_requests (
    id character varying(32) NOT NULL,
    anomaly_id character varying(32) NOT NULL,
    request_at timestamp with time zone NOT NULL,
    status character varying(50) NOT NULL,
    reason text,
    proposed_time timestamp with time zone,
    decision_comment text,
    validated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sites (
    id character varying(32) NOT NULL,
    name character varying(255) NOT NULL,
    address character varying(512),
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1 NOT NULL,
    directory_id character varying(32) NOT NULL,
    location geography(Point,4326) NOT NULL,
    kind character varying(16) DEFAULT 'ANNEX'::character varying NOT NULL
);

CREATE TABLE IF NOT EXISTS time_entries (
    id character varying(32) NOT NULL,
    employee_id character varying(32) NOT NULL,
    entry_type character varying(16) NOT NULL,
    occured_at timestamp with time zone NOT NULL,
    location geography(Point,4326),
    location_confidence character varying(16) NOT NULL,
    source character varying(16) NOT NULL,
    idempotency_key character varying(255) NOT NULL,
    wifi_identifier character varying(255),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone,
    version_id integer DEFAULT 1 NOT NULL,
    assisted_by_user_id character varying(32),
    photo_key character varying(255),
    validation_status character varying(16) DEFAULT 'COUNTED' NOT NULL
);

CREATE TABLE IF NOT EXISTS time_profile_days (
    id character varying(32) NOT NULL,
    time_profile_version_id character varying(32) NOT NULL,
    day_of_week character varying(16) NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    break_duration interval NOT NULL,
    break_threshold interval NOT NULL,
    tolerance interval NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS time_profile_versions (
    id character varying(32) NOT NULL,
    time_profile_id character varying(32) NOT NULL,
    version integer NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS time_profiles (
    id character varying(32) NOT NULL,
    name character varying(100) NOT NULL,
    timezone character varying(64) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1
);

CREATE TABLE IF NOT EXISTS users (
    id character varying(32) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255),
    role character varying(16) NOT NULL,
    first_name character varying(255),
    last_name character varying(255),
    avatar_url character varying(512),
    is_active boolean DEFAULT true NOT NULL,
    last_active_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    version_id integer DEFAULT 1 NOT NULL
);

ALTER TABLE absence_types
    ADD CONSTRAINT absence_types_name_key UNIQUE (name);

ALTER TABLE absence_types
    ADD CONSTRAINT absence_types_pkey PRIMARY KEY (id);

ALTER TABLE absences
    ADD CONSTRAINT absences_pkey PRIMARY KEY (id);

ALTER TABLE anomalies
    ADD CONSTRAINT anomalies_pkey PRIMARY KEY (id);

ALTER TABLE calculation_rule_versions
    ADD CONSTRAINT calculation_rule_versions_pkey PRIMARY KEY (id);

ALTER TABLE calculation_rule_versions
    ADD CONSTRAINT calculation_rule_versions_rule_version_key UNIQUE (rule_version);

ALTER TABLE daily_time_results
    ADD CONSTRAINT daily_time_results_pkey PRIMARY KEY (id);

ALTER TABLE directories
    ADD CONSTRAINT directories_pkey PRIMARY KEY (id);

ALTER TABLE employee_assignments
    ADD CONSTRAINT employee_assignments_pkey PRIMARY KEY (id);

ALTER TABLE employee_schedules
    ADD CONSTRAINT employee_schedules_pkey PRIMARY KEY (id);

ALTER TABLE employees
    ADD CONSTRAINT employees_pkey PRIMARY KEY (id);

ALTER TABLE periods
    ADD CONSTRAINT periods_pkey PRIMARY KEY (id);

ALTER TABLE regularization_requests
    ADD CONSTRAINT regularization_requests_pkey PRIMARY KEY (id);

ALTER TABLE sites
    ADD CONSTRAINT sites_pkey PRIMARY KEY (id);

ALTER TABLE time_entries
    ADD CONSTRAINT time_entries_pkey PRIMARY KEY (id);

ALTER TABLE time_profile_days
    ADD CONSTRAINT time_profile_days_pkey PRIMARY KEY (id);

ALTER TABLE time_profile_versions
    ADD CONSTRAINT time_profile_versions_pkey PRIMARY KEY (id);

ALTER TABLE time_profiles
    ADD CONSTRAINT time_profiles_pkey PRIMARY KEY (id);

ALTER TABLE daily_time_results
    ADD CONSTRAINT uq_daily_time_results_employee_id UNIQUE (employee_id, work_date);

ALTER TABLE employees
    ADD CONSTRAINT uq_employees_employee_number UNIQUE (employee_number);

ALTER TABLE time_profile_days
    ADD CONSTRAINT uq_time_profile_days_day UNIQUE (time_profile_version_id, day_of_week);

ALTER TABLE time_profile_versions
    ADD CONSTRAINT uq_time_profile_versions_version UNIQUE (time_profile_id, version);

ALTER TABLE users
    ADD CONSTRAINT users_email_key UNIQUE (email);

ALTER TABLE users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

CREATE INDEX IF NOT EXISTS ix_absences_employee_id ON absences USING btree (employee_id);

CREATE INDEX IF NOT EXISTS ix_absences_status ON absences USING btree (status);

CREATE INDEX IF NOT EXISTS ix_anomalies_severity ON anomalies USING btree (severity);

CREATE INDEX IF NOT EXISTS ix_anomalies_status ON anomalies USING btree (status);

CREATE INDEX IF NOT EXISTS ix_anomalies_time_entry_id ON anomalies USING btree (time_entry_id);

CREATE INDEX IF NOT EXISTS ix_anomalies_type ON anomalies USING btree (type);

CREATE INDEX IF NOT EXISTS ix_daily_time_results_period_id ON daily_time_results USING btree (period_id);

CREATE INDEX IF NOT EXISTS ix_daily_time_results_status ON daily_time_results USING btree (status);

CREATE INDEX IF NOT EXISTS ix_directories_parent_directory_id ON directories USING btree (parent_directory_id);

CREATE INDEX IF NOT EXISTS ix_employee_assignments_directory_id ON employee_assignments USING btree (directory_id);

CREATE INDEX IF NOT EXISTS ix_employee_assignments_employee_id ON employee_assignments USING btree (employee_id);

CREATE INDEX IF NOT EXISTS ix_employee_schedules_employee_id ON employee_schedules USING btree (employee_id);

CREATE INDEX IF NOT EXISTS ix_employees_user_id ON employees USING btree (user_id);

CREATE INDEX IF NOT EXISTS ix_regularization_requests_anomaly_id ON regularization_requests USING btree (anomaly_id);

CREATE INDEX IF NOT EXISTS ix_regularization_requests_status ON regularization_requests USING btree (status);

CREATE INDEX IF NOT EXISTS ix_sites_directory_id ON sites USING btree (directory_id);

CREATE INDEX IF NOT EXISTS ix_time_entries_employee_id ON time_entries USING btree (employee_id);

CREATE INDEX IF NOT EXISTS ix_time_entries_entry_type ON time_entries USING btree (entry_type);

CREATE INDEX IF NOT EXISTS ix_time_entries_idempotency_key ON time_entries USING btree (idempotency_key);

CREATE INDEX IF NOT EXISTS ix_time_profile_days_time_profile_version_id ON time_profile_days USING btree (time_profile_version_id);

CREATE INDEX IF NOT EXISTS ix_time_profile_versions_time_profile_id ON time_profile_versions USING btree (time_profile_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_sites_one_principal_per_directory ON sites USING btree (directory_id) WHERE ((kind)::text = 'PRINCIPAL'::text);

ALTER TABLE absences
    ADD CONSTRAINT absences_absence_type_id_fkey FOREIGN KEY (absence_type_id) REFERENCES absence_types(id);

ALTER TABLE absences
    ADD CONSTRAINT absences_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES employees(id);

ALTER TABLE anomalies
    ADD CONSTRAINT anomalies_time_entry_id_fkey FOREIGN KEY (time_entry_id) REFERENCES time_entries(id);

ALTER TABLE daily_time_results
    ADD CONSTRAINT daily_time_results_calculation_rule_version_id_fkey FOREIGN KEY (calculation_rule_version_id) REFERENCES calculation_rule_versions(id);

ALTER TABLE daily_time_results
    ADD CONSTRAINT daily_time_results_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES employees(id);

ALTER TABLE daily_time_results
    ADD CONSTRAINT daily_time_results_period_id_fkey FOREIGN KEY (period_id) REFERENCES periods(id);

ALTER TABLE directories
    ADD CONSTRAINT directories_parent_directory_id_fkey FOREIGN KEY (parent_directory_id) REFERENCES directories(id);

ALTER TABLE employee_assignments
    ADD CONSTRAINT employee_assignments_directory_id_fkey FOREIGN KEY (directory_id) REFERENCES directories(id);

ALTER TABLE employee_assignments
    ADD CONSTRAINT employee_assignments_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES employees(id);

ALTER TABLE employee_assignments
    ADD CONSTRAINT employee_assignments_site_id_fkey FOREIGN KEY (site_id) REFERENCES sites(id);

ALTER TABLE employee_schedules
    ADD CONSTRAINT employee_schedules_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES employees(id);

ALTER TABLE employee_schedules
    ADD CONSTRAINT employee_schedules_time_profile_version_id_fkey FOREIGN KEY (time_profile_version_id) REFERENCES time_profile_versions(id);

ALTER TABLE employees
    ADD CONSTRAINT employees_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

ALTER TABLE regularization_requests
    ADD CONSTRAINT regularization_requests_anomaly_id_fkey FOREIGN KEY (anomaly_id) REFERENCES anomalies(id);

ALTER TABLE sites
    ADD CONSTRAINT sites_directory_id_fkey FOREIGN KEY (directory_id) REFERENCES directories(id);

ALTER TABLE time_entries
    ADD CONSTRAINT time_entries_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES employees(id);

ALTER TABLE time_profile_days
    ADD CONSTRAINT time_profile_days_time_profile_version_id_fkey FOREIGN KEY (time_profile_version_id) REFERENCES time_profile_versions(id);

ALTER TABLE time_profile_versions
    ADD CONSTRAINT time_profile_versions_time_profile_id_fkey FOREIGN KEY (time_profile_id) REFERENCES time_profiles(id);

-- The last event position applied by each projection runner.
CREATE TABLE IF NOT EXISTS projection_checkpoints (
    id VARCHAR(64) PRIMARY KEY,
    position BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    version_id INTEGER DEFAULT 1 NOT NULL
);

INSERT INTO projection_checkpoints (id, position) VALUES ('read_model', 0) ON CONFLICT (id) DO NOTHING;

-- Events a projection could not apply (logged, parked, skipped). Each row
-- names the stream left stale from that event on: fix the cause, then
-- rebuild (see the top of this file).
CREATE TABLE IF NOT EXISTS projection_failures (
    id VARCHAR(64) PRIMARY KEY,               -- the event's id
    runner VARCHAR(64) NOT NULL,
    global_position BIGINT NOT NULL,
    stream_type VARCHAR(64) NOT NULL,
    stream_id VARCHAR(32) NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    error TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    version_id INTEGER DEFAULT 1 NOT NULL
);
