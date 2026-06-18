-- Migration 002: intermediate stops, stale-data reconciliation, and scrape guardrails.
-- Idempotent: safe to run multiple times.

-- 1. Intermediate stop modelling -------------------------------------------------
-- A route is an ordered sequence of stops. sequence 0 is the origin, the highest
-- sequence is the destination, and everything in between is an intermediate stop.
-- arrival_offset_minutes is minutes after the origin departure (NULL when unknown).
CREATE TABLE IF NOT EXISTS route_stops (
    id                      SERIAL PRIMARY KEY,
    route_id                INT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    stop_id                 INT NOT NULL REFERENCES stops(id),
    sequence                INT NOT NULL,
    arrival_offset_minutes  INT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_route_stop UNIQUE (route_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_route_stops_route ON route_stops(route_id);
CREATE INDEX IF NOT EXISTS idx_route_stops_stop ON route_stops(stop_id);

-- 2. Stale-data reconciliation ---------------------------------------------------
-- Routes/schedules that vanish from the source should be deactivated, not orphaned.
ALTER TABLE routes    ADD COLUMN IF NOT EXISTS is_active    BOOLEAN     NOT NULL DEFAULT true;
ALTER TABLE routes    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_routes_active ON routes(is_active) WHERE is_active = true;

-- 3. Scrape guardrail bookkeeping ------------------------------------------------
ALTER TABLE scrape_logs ADD COLUMN IF NOT EXISTS routes_seen        INT NOT NULL DEFAULT 0;
ALTER TABLE scrape_logs ADD COLUMN IF NOT EXISTS routes_deactivated INT NOT NULL DEFAULT 0;
