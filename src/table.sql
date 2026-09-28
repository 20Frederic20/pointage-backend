---------------------------------------------------------------

CREATE TABLE outbox (
    id SERIAL PRIMARY KEY,
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

---------------------------------------------------------------
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