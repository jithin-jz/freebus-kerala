from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_secret_key: str = "dev-secret-key"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    database_url: str = "postgresql+asyncpg://pbf_user:pbf_pass@localhost:5432/priyadarshini"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_db_url: str = ""

    # Connection pool. Keep small when running behind a transaction-mode pooler
    # (e.g. Supabase pgbouncer): the pooler multiplexes connections, so a large
    # SQLAlchemy pool only exhausts the upstream limit.
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout: int = 30

    scraper_source_url: str = (
        "https://www.tickettogetlost.com/2026/06/14/"
        "ksrtc-women-free-bus-list-timings-priyadarshini-scheme-kerala/"
    )
    scraper_rate_limit_seconds: float = 2.0
    scraper_user_agent: str = "PriyadarshiniBusFinder/1.0"
    scraper_alert_email: str = ""
    # Abort the write if parsed route count falls below this fraction of the last
    # successful scrape (guards against silent source-layout breakage). Override
    # with SCRAPER_FORCE=true to bypass.
    scraper_min_route_ratio: float = 0.7

    osm_overpass_url: str = "https://overpass-api.de/api/interpreter"
    osm_nominatim_url: str = "https://nominatim.openstreetmap.org/search"
    geocoding_enabled: bool = True

    enable_analytics: bool = False
    max_nearby_radius_metres: int = 2000
    default_nearby_radius_metres: int = 1000

    @property
    def active_db_url(self) -> str:
        """Return Supabase URL in production, local Docker URL in development."""
        if self.app_env == "production" and self.supabase_db_url:
            return self.supabase_db_url
        return self.database_url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

