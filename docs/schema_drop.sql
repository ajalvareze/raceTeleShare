-- RaceTrace — full schema teardown
-- Drops all tables and custom types in reverse-dependency order.
-- WARNING: this permanently deletes all data.
-- Apply with: psql -U racetrace -d racetrace -f schema_drop.sql

DROP TABLE IF EXISTS alembic_version     CASCADE;
DROP TABLE IF EXISTS laps                CASCADE;
DROP TABLE IF EXISTS sessions            CASCADE;
DROP TABLE IF EXISTS event_participants  CASCADE;
DROP TABLE IF EXISTS events              CASCADE;
DROP TABLE IF EXISTS refresh_tokens      CASCADE;
DROP TABLE IF EXISTS oauth_accounts      CASCADE;
DROP TABLE IF EXISTS cars                CASCADE;
DROP TABLE IF EXISTS track_configurations CASCADE;
DROP TABLE IF EXISTS users               CASCADE;
DROP TABLE IF EXISTS tracks              CASCADE;

DROP TYPE IF EXISTS sessiontype  CASCADE;
DROP TYPE IF EXISTS drivetrain   CASCADE;
DROP TYPE IF EXISTS eventstatus  CASCADE;
