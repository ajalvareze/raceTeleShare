-- RaceTrace — full schema creation
-- Targets: PostgreSQL 14+
-- Generated from Alembic migrations: b00cb40aabe3 → 245d6ad9d0d3
-- Apply with: psql -U racetrace -d racetrace -f schema_create.sql

-- ── Custom types ────────────────────────────────────────────────────────────

DO $$ BEGIN
    CREATE TYPE sessiontype  AS ENUM ('practice', 'qualifying', 'race', 'hotlap');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE drivetrain    AS ENUM ('fwd', 'rwd', 'awd');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE eventstatus   AS ENUM ('upcoming', 'active', 'completed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Tables (dependency order) ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS tracks (
    id      SERIAL PRIMARY KEY,
    name    VARCHAR(128) NOT NULL,
    country VARCHAR(64)  NOT NULL,
    city    VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS users (
    id                     SERIAL PRIMARY KEY,
    username               VARCHAR(64)  NOT NULL,
    email                  VARCHAR(255) NOT NULL,
    hashed_password        VARCHAR(255),
    full_name              VARCHAR(128),
    is_active              BOOLEAN      NOT NULL DEFAULT TRUE,
    is_superuser           BOOLEAN      NOT NULL DEFAULT FALSE,
    failed_login_attempts  INTEGER      NOT NULL DEFAULT 0,
    locked_until           TIMESTAMPTZ,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS track_configurations (
    id                SERIAL PRIMARY KEY,
    track_id          INTEGER      NOT NULL REFERENCES tracks(id),
    name              VARCHAR(128) NOT NULL,
    length_meters     FLOAT,
    num_sectors       INTEGER      NOT NULL DEFAULT 3,
    start_finish_lat  FLOAT,
    start_finish_lon  FLOAT,
    layout_data       TEXT,
    is_default        BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS cars (
    id          SERIAL PRIMARY KEY,
    owner_id    INTEGER      NOT NULL REFERENCES users(id),
    make        VARCHAR(64)  NOT NULL,
    model       VARCHAR(64)  NOT NULL,
    year        INTEGER,
    category    VARCHAR(64),
    drivetrain  drivetrain,
    power_hp    INTEGER,
    weight_kg   INTEGER,
    engine_cc   INTEGER,
    notes       VARCHAR(1024)
);

CREATE TABLE IF NOT EXISTS oauth_accounts (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER      NOT NULL REFERENCES users(id),
    provider          VARCHAR(32)  NOT NULL,
    provider_user_id  VARCHAR(255) NOT NULL,
    provider_email    VARCHAR(255),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (provider, provider_user_id)
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER     NOT NULL REFERENCES users(id),
    token_hash  VARCHAR(64) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    id                      SERIAL PRIMARY KEY,
    organizer_id            INTEGER      NOT NULL REFERENCES users(id),
    track_configuration_id  INTEGER      NOT NULL REFERENCES track_configurations(id),
    name                    VARCHAR(128) NOT NULL,
    description             TEXT,
    date_start              TIMESTAMPTZ  NOT NULL,
    date_end                TIMESTAMPTZ  NOT NULL,
    is_public               BOOLEAN      NOT NULL DEFAULT TRUE,
    is_open                 BOOLEAN      NOT NULL DEFAULT TRUE,
    status                  eventstatus  NOT NULL DEFAULT 'upcoming',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_participants (
    id         SERIAL PRIMARY KEY,
    event_id   INTEGER     NOT NULL REFERENCES events(id),
    user_id    INTEGER     NOT NULL REFERENCES users(id),
    joined_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id                      SERIAL PRIMARY KEY,
    user_id                 INTEGER       NOT NULL REFERENCES users(id),
    track_configuration_id  INTEGER       NOT NULL REFERENCES track_configurations(id),
    car_id                  INTEGER       REFERENCES cars(id),
    event_id                INTEGER       REFERENCES events(id),
    session_type            sessiontype   NOT NULL DEFAULT 'practice',
    date                    TIMESTAMPTZ   NOT NULL,
    notes                   VARCHAR(1024),
    is_public               BOOLEAN       NOT NULL DEFAULT FALSE,
    source_file_path        VARCHAR(512),
    app_source              VARCHAR(64),
    vehicle_hint            VARCHAR(128),
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS laps (
    id                  SERIAL PRIMARY KEY,
    session_id          INTEGER      NOT NULL REFERENCES sessions(id),
    lap_number          INTEGER      NOT NULL,
    lap_time_ms         INTEGER,
    sector1_ms          INTEGER,
    sector2_ms          INTEGER,
    sector3_ms          INTEGER,
    telemetry_file_path VARCHAR(512),
    telemetry_format    VARCHAR(32),
    max_speed_kmh       FLOAT,
    avg_speed_kmh       FLOAT,
    max_throttle_pct    FLOAT,
    max_brake_pct       FLOAT,
    summary             JSONB,
    gps_track           JSONB,
    is_valid            BOOLEAN      NOT NULL DEFAULT TRUE,
    is_outlap           BOOLEAN      NOT NULL DEFAULT FALSE,
    is_inlap            BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Alembic version tracking
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num)
VALUES ('245d6ad9d0d3')
ON CONFLICT DO NOTHING;

-- ── Indexes ──────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS ix_tracks_id            ON tracks(id);
CREATE INDEX IF NOT EXISTS ix_tracks_name          ON tracks(name);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username  ON users(username);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email     ON users(email);
CREATE INDEX        IF NOT EXISTS ix_users_id        ON users(id);

CREATE INDEX IF NOT EXISTS ix_track_configurations_id  ON track_configurations(id);

CREATE INDEX IF NOT EXISTS ix_cars_id              ON cars(id);

CREATE INDEX        IF NOT EXISTS ix_oauth_accounts_id  ON oauth_accounts(id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash  ON refresh_tokens(token_hash);
CREATE INDEX        IF NOT EXISTS ix_refresh_tokens_id          ON refresh_tokens(id);

CREATE INDEX IF NOT EXISTS ix_events_id             ON events(id);
CREATE INDEX IF NOT EXISTS ix_event_participants_id ON event_participants(id);

CREATE INDEX IF NOT EXISTS ix_sessions_id          ON sessions(id);

CREATE INDEX IF NOT EXISTS ix_laps_id              ON laps(id);
