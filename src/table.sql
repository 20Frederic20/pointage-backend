

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
)

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