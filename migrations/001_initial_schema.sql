CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS depots (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL UNIQUE,
    name_ml     VARCHAR(120),
    district    VARCHAR(60)  NOT NULL,
    address     TEXT,
    phone       VARCHAR(20),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stops (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    name_ml     VARCHAR(120),
    name_slug   VARCHAR(140) NOT NULL UNIQUE,
    district    VARCHAR(60)  NOT NULL,
    depot_id    INT REFERENCES depots(id),
    location    GEOMETRY(Point, 4326),
    osm_id      BIGINT,
    is_major    BOOLEAN      NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stops_location ON stops USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_stops_name_trgm ON stops USING GIN (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS routes (
    id                  SERIAL PRIMARY KEY,
    origin_stop_id      INT NOT NULL REFERENCES stops(id),
    destination_stop_id INT NOT NULL REFERENCES stops(id),
    route_name          VARCHAR(250) NOT NULL,
    route_name_ml       VARCHAR(250),
    via                 VARCHAR(200),
    bus_type            VARCHAR(60)  NOT NULL,
    is_priyadarshini    BOOLEAN      NOT NULL DEFAULT false,
    depot_id            INT REFERENCES depots(id),
    source_url          TEXT,
    data_hash           VARCHAR(64),
    last_scraped_at     TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_route UNIQUE (origin_stop_id, destination_stop_id, via, bus_type)
);

CREATE INDEX IF NOT EXISTS idx_routes_origin ON routes(origin_stop_id);
CREATE INDEX IF NOT EXISTS idx_routes_destination ON routes(destination_stop_id);
CREATE INDEX IF NOT EXISTS idx_routes_priyadarshini ON routes(is_priyadarshini) WHERE is_priyadarshini = true;

CREATE TABLE IF NOT EXISTS schedules (
    id                  SERIAL PRIMARY KEY,
    route_id            INT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    departure_time      TIME NOT NULL,
    days_of_operation   VARCHAR(20) NOT NULL DEFAULT 'daily',
    frequency_note      TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_schedule UNIQUE (route_id, departure_time, days_of_operation)
);

CREATE INDEX IF NOT EXISTS idx_schedules_route ON schedules(route_id);
CREATE INDEX IF NOT EXISTS idx_schedules_time ON schedules(departure_time);
CREATE INDEX IF NOT EXISTS idx_schedules_active ON schedules(is_active) WHERE is_active = true;

CREATE TABLE IF NOT EXISTS scrape_logs (
    id              SERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',
    routes_added    INT NOT NULL DEFAULT 0,
    routes_updated  INT NOT NULL DEFAULT 0,
    routes_failed   INT NOT NULL DEFAULT 0,
    schedules_added INT NOT NULL DEFAULT 0,
    error_message   TEXT,
    source_url      TEXT
);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_stops_updated_at ON stops;
CREATE TRIGGER trg_stops_updated_at
    BEFORE UPDATE ON stops
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_routes_updated_at ON routes;
CREATE TRIGGER trg_routes_updated_at
    BEFORE UPDATE ON routes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

