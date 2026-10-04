

-------------------------------------------------------------------------

CREATE TABLE outbox (
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

CREATE INDEX ix_outbox_status ON outbox (status);

----------------------------------------------------------------------------
-- 1. Activer l'extension PostGIS (nécessaire pour GeoAlchemy2)
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Création de la table "directories"
CREATE TABLE directories (
    id VARCHAR(32) PRIMARY KEY,
    code VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Création de la table "users"
CREATE TABLE users (
    id VARCHAR(32) PRIMARY KEY,
    directory_id VARCHAR(32) NOT NULL REFERENCES directories(id),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL, -- Stocké en VARCHAR car native_enum=False
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    avatar_url VARCHAR(512),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_active_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Index sur directory_id (demandé via index=True dans le modèle)
CREATE INDEX ix_users_directory_id ON users (directory_id);


-------------------------------------------------------------------------------
-- Ajouter la colonne version_id à directories si elle n'existe pas
ALTER TABLE directories ADD COLUMN IF NOT EXISTS version_id INTEGER DEFAULT 1 NOT NULL;

-- Ajouter la colonne version_id à users si elle n'existe pas
ALTER TABLE users ADD COLUMN IF NOT EXISTS version_id INTEGER DEFAULT 1 NOT NULL;


---------------------------------------------------------------------------

ALTER TABLE users DROP COLUMN directory_id CASCADE;

CREATE TABLE employees(
    id VARCHAR(32) PRIMARY KEY,
    directory_id VARCHAR(32) NOT NULL REFERENCES directories(id),
    user_id VARCHAR(32) NOT NULL REFERENCES users(id),
    employee_number VARCHAR(20) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    role VARCHAR(16) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1
);

ALTER TABLE employees ADD CONSTRAINT uq_employees_employee_number UNIQUE (employee_number);

CREATE INDEX ix_employees_directory_id ON employees (directory_id);

CREATE INDEX ix_employees_user_id ON employees (user_id);

---------------------------------------------------------------------------

-- Création de la table time_entries
CREATE TABLE time_entries (
    id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(id),
    entry_type VARCHAR(16) NOT NULL,
    occured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    location_confidence VARCHAR(16) NOT NULL,
    source VARCHAR(16) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    wifi_identifier VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,
    version_id INTEGER DEFAULT 1 NOT NULL
);

-- Index pour optimiser les recherches par employé (recommandé pour les clés étrangères)
CREATE INDEX ix_time_entries_employee_id ON time_entries (employee_id);

-- Index optionnel mais conseillé sur l'idempotency_key si vous faites des recherches fréquentes dessus
CREATE INDEX ix_time_entries_idempotency_key ON time_entries (idempotency_key);

CREATE INDEX ix_time_entries_entry_type ON time_entries (entry_type);

CREATE TABLE IF NOT EXISTS anomalies (
    id VARCHAR(32) PRIMARY KEY,
    time_entry_id VARCHAR(32) NOT NULL REFERENCES time_entries(id),
    type VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    description TEXT,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1
);

CREATE INDEX ix_anomalies_time_entry_id ON anomalies (time_entry_id);

CREATE INDEX ix_anomalies_type ON anomalies (type);

CREATE INDEX ix_anomalies_status ON anomalies (status);

CREATE INDEX ix_anomalies_severity ON anomalies (severity);


CREATE TABLE IF NOT EXISTS regularization_requests (
    id VARCHAR(32) PRIMARY KEY,
    anomaly_id VARCHAR(32) NOT NULL REFERENCES anomalies(id),
    request_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) NOT NULL,
    reason TEXT,
    proposed_time TIMESTAMP WITH TIME ZONE,
    decision_comment TEXT,
    validated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1
);

CREATE INDEX ix_regularization_requests_anomaly_id ON regularization_requests (anomaly_id);

CREATE INDEX ix_regularization_requests_status ON regularization_requests (status);


CREATE TABLE IF NOT EXISTS absence_types (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    paid BOOLEAN NOT NULL,
    counts_as_work_time BOOLEAN NOT NULL,
    deducts_balance BOOLEAN NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS absences (
    id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(id),
    absence_type_id VARCHAR(32) NOT NULL REFERENCES absence_types(id),
    start_at TIMESTAMP WITH TIME ZONE NOT NULL,
    end_at TIMESTAMP WITH TIME ZONE NOT NULL,
    reason VARCHAR(512) NOT NULL,
    status VARCHAR(32) NOT NULL,
    justification_reference VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1,
    CONSTRAINT ck_absences_period CHECK (end_at > start_at)
);

CREATE INDEX ix_absences_employee_id ON absences (employee_id);

CREATE INDEX ix_absences_status ON absences (status);

CREATE TABLE IF NOT EXISTS time_profiles (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    timezone VARCHAR(64) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS time_profile_versions (
    id VARCHAR(32) PRIMARY KEY,
    time_profile_id VARCHAR(32) NOT NULL REFERENCES time_profiles(id),
    version INTEGER NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1,
    CONSTRAINT uq_time_profile_versions_version UNIQUE (time_profile_id, version)
);

CREATE INDEX ix_time_profile_versions_time_profile_id ON time_profile_versions (time_profile_id);

CREATE TABLE IF NOT EXISTS time_profile_days (
    id VARCHAR(32) PRIMARY KEY,
    time_profile_version_id VARCHAR(32) NOT NULL REFERENCES time_profile_versions(id),
    day_of_week VARCHAR(16) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    break_duration INTERVAL NOT NULL,
    break_threshold INTERVAL NOT NULL,
    tolerance INTERVAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1,
    CONSTRAINT uq_time_profile_days_day UNIQUE (time_profile_version_id, day_of_week)
);

CREATE INDEX ix_time_profile_days_time_profile_version_id ON time_profile_days (time_profile_version_id);

CREATE TABLE IF NOT EXISTS employee_schedules (
    id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(id),
    time_profile_version_id VARCHAR(32) NOT NULL REFERENCES time_profile_versions(id),
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1,
    CONSTRAINT ck_employee_schedules_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX ix_employee_schedules_employee_id ON employee_schedules (employee_id);

CREATE TABLE IF NOT EXISTS periods (
    id VARCHAR(32) PRIMARY KEY,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(16) NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1,
    CONSTRAINT ck_periods_dates CHECK (end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS calculation_rule_versions (
    id VARCHAR(32) PRIMARY KEY,
    rule_version INTEGER NOT NULL UNIQUE,
    effective_from DATE NOT NULL,
    effective_to DATE,
    min_break_duration INTERVAL NOT NULL,
    break_threshold INTERVAL NOT NULL,
    max_daily_work_duration INTERVAL NOT NULL,
    max_amplitude INTERVAL NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS daily_time_results (
    id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(id),
    period_id VARCHAR(32) NOT NULL REFERENCES periods(id),
    calculation_rule_version_id VARCHAR(32) NOT NULL REFERENCES calculation_rule_versions(id),
    work_date DATE NOT NULL,
    planned_duration INTERVAL NOT NULL,
    worked_duration INTERVAL NOT NULL,
    break_duration INTERVAL NOT NULL,
    absence_duration INTERVAL NOT NULL,
    late_duration INTERVAL NOT NULL,
    status VARCHAR(16) NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1,
    CONSTRAINT uq_daily_time_results_employee_id UNIQUE (employee_id, work_date)
);

CREATE INDEX ix_daily_time_results_period_id ON daily_time_results (period_id);

CREATE INDEX ix_daily_time_results_status ON daily_time_results (status);


---------------------------------------------------------------------------
-- Sites, directory hierarchy and employee assignments
-- (an employee is no longer bound to one directory: assignments say where
--  they work and from when to when). Safe to run more than once.
---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sites (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(512),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1 NOT NULL
);

-- Existing directories get a default site so site_id can be NOT NULL.
INSERT INTO sites (id, name)
SELECT 'defaultsite', 'Default site'
WHERE EXISTS (SELECT 1 FROM directories)
ON CONFLICT (id) DO NOTHING;

ALTER TABLE directories ADD COLUMN IF NOT EXISTS site_id VARCHAR(32) REFERENCES sites(id);
UPDATE directories SET site_id = 'defaultsite' WHERE site_id IS NULL;
ALTER TABLE directories ALTER COLUMN site_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_directories_site_id ON directories (site_id);

ALTER TABLE directories ADD COLUMN IF NOT EXISTS parent_directory_id VARCHAR(32) REFERENCES directories(id);
CREATE INDEX IF NOT EXISTS ix_directories_parent_directory_id ON directories (parent_directory_id);

CREATE TABLE IF NOT EXISTS employee_assignments (
    id VARCHAR(32) PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL REFERENCES employees(id),
    directory_id VARCHAR(32) NOT NULL REFERENCES directories(id),
    site_id VARCHAR(32) NOT NULL REFERENCES sites(id),
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    version_id INTEGER DEFAULT 1 NOT NULL,
    CONSTRAINT ck_employee_assignments_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS ix_employee_assignments_employee_id ON employee_assignments (employee_id);
CREATE INDEX IF NOT EXISTS ix_employee_assignments_directory_id ON employee_assignments (directory_id);

-- Each employee's current directory becomes an open-ended assignment
-- starting on the day the employee was created, then the column goes away.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'employees' AND column_name = 'directory_id'
    ) THEN
        INSERT INTO employee_assignments (id, employee_id, directory_id, site_id, start_date)
        SELECT 'ea' || substr(md5(e.id), 1, 30), e.id, e.directory_id, d.site_id, e.created_at::date
        FROM employees e
        JOIN directories d ON d.id = e.directory_id
        ON CONFLICT (id) DO NOTHING;

        ALTER TABLE employees DROP COLUMN directory_id;
    END IF;
END $$;
