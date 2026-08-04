-- Схема ab_game в базе communication (одинаково на stage и prod).
--
-- Новая установка (от roman):
--   psql -h localhost -U roman -d communication -f sql/001_init.sql

CREATE SCHEMA IF NOT EXISTS ab_game;

CREATE TABLE IF NOT EXISTS ab_game.users (
    user_id TEXT PRIMARY KEY,
    internal_user_id BIGSERIAL NOT NULL UNIQUE,
    external_user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    registration_date TIMESTAMP NOT NULL,
    registration_channel TEXT NOT NULL,
    last_active_at TIMESTAMP NOT NULL,
    is_paid BOOLEAN NOT NULL DEFAULT FALSE,
    is_trial BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS ab_game.events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_id TEXT NOT NULL REFERENCES ab_game.users (user_id),
    internal_user_id BIGINT NOT NULL,
    external_user_id TEXT NOT NULL,
    event_name TEXT NOT NULL,
    channel TEXT NOT NULL,
    event_parameters JSONB,
    inserted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_user_id ON ab_game.events (user_id);
CREATE INDEX IF NOT EXISTS idx_events_internal_user_id ON ab_game.events (internal_user_id);
CREATE INDEX IF NOT EXISTS idx_events_event_name ON ab_game.events (event_name);
CREATE INDEX IF NOT EXISTS idx_users_external_user_id ON ab_game.users (external_user_id);

-- Один external_user_id на канал = одна строка users.
CREATE UNIQUE INDEX IF NOT EXISTS users_channel_external_uidx
    ON ab_game.users (registration_channel, external_user_id);

-- Параметры раундов (подробности / миграция для старых БД — sql/002_round_parameters.sql).
CREATE TABLE IF NOT EXISTS ab_game.round_parameters (
    id BIGSERIAL PRIMARY KEY,
    played_at TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id TEXT NOT NULL REFERENCES ab_game.users (user_id),
    internal_user_id BIGINT NOT NULL,
    external_user_id TEXT NOT NULL,
    round_index INTEGER NOT NULL,
    difficulty TEXT NOT NULL,
    noise DOUBLE PRECISION NOT NULL,
    base_p DOUBLE PRECISION NOT NULL,
    target_a DOUBLE PRECISION NOT NULL,
    target_b DOUBLE PRECISION NOT NULL,
    want_effect BOOLEAN NOT NULL,
    p_value DOUBLE PRECISION NOT NULL,
    significant BOOLEAN NOT NULL,
    aligned BOOLEAN NOT NULL,
    calibrate_steps INTEGER NOT NULL DEFAULT 0,
    series JSONB NOT NULL,
    inserted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_round_parameters_user_id
    ON ab_game.round_parameters (user_id);
CREATE INDEX IF NOT EXISTS idx_round_parameters_played_at
    ON ab_game.round_parameters (played_at);
CREATE INDEX IF NOT EXISTS idx_round_parameters_want_effect
    ON ab_game.round_parameters (want_effect);
