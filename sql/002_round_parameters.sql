-- Параметры показанных раундов (аналитика баланса эффекта / p-value).
--
-- Новая установка: достаточно sql/001_init.sql (таблица уже включена).
-- Уже развёрнутая БД:
--   psql -h localhost -U roman -d communication -f sql/002_round_parameters.sql

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
    -- Явный флаг раунда: должен ли z-тест показать значимый эффект.
    want_effect BOOLEAN NOT NULL,
    p_value DOUBLE PRECISION NOT NULL,
    significant BOOLEAN NOT NULL,
    -- Совпал ли фактический significant с want_effect после калибровки.
    aligned BOOLEAN NOT NULL,
    calibrate_steps INTEGER NOT NULL DEFAULT 0,
    -- Дневные точки графика: {"A":[{day,numerator,denominator,rate},...],"B":[...]}
    series JSONB NOT NULL,
    inserted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_round_parameters_user_id
    ON ab_game.round_parameters (user_id);
CREATE INDEX IF NOT EXISTS idx_round_parameters_played_at
    ON ab_game.round_parameters (played_at);
CREATE INDEX IF NOT EXISTS idx_round_parameters_want_effect
    ON ab_game.round_parameters (want_effect);
