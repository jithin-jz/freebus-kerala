import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.database import AsyncSessionLocal
from sqlalchemy import text

from scraper.fetcher import RateLimitedFetcher
from scraper.parser import parse_routes
from scraper.upserter import deactivate_stale, upsert_routes

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class GuardrailError(RuntimeError):
    """Raised when parsed data fails a sanity check and the write is aborted."""


async def _last_successful_route_count(db) -> int:
    row = (
        await db.execute(
            text(
                """
                SELECT routes_seen
                FROM scrape_logs
                WHERE status IN ('success', 'partial') AND routes_seen > 0
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
        )
    ).scalar_one_or_none()
    return int(row or 0)


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    force = os.getenv("SCRAPER_FORCE", "false").lower() == "true"

    fetcher = RateLimitedFetcher()
    html = await fetcher.fetch(settings.scraper_source_url)
    routes = parse_routes(html, source_url=settings.scraper_source_url)
    logger.info("Parsed %s candidate routes", len(routes))

    if dry_run:
        logger.info("Dry run enabled; parsed data was not written")
        return

    async with AsyncSessionLocal() as db:
        # Guardrail: refuse to overwrite good data if the source appears broken.
        previous = await _last_successful_route_count(db)
        threshold = int(previous * settings.scraper_min_route_ratio)
        if previous and len(routes) < threshold and not force:
            message = (
                f"Parsed {len(routes)} routes, below guardrail threshold {threshold} "
                f"(last successful run saw {previous}). Aborting write. "
                f"Set SCRAPER_FORCE=true to override."
            )
            logger.error(message)
            await db.execute(
                text(
                    """
                    INSERT INTO scrape_logs (started_at, finished_at, status, routes_seen,
                                             error_message, source_url)
                    VALUES (:started_at, :finished_at, 'failed', :routes_seen, :error, :source_url)
                    """
                ),
                {
                    "started_at": datetime.now(tz=IST),
                    "finished_at": datetime.now(tz=IST),
                    "routes_seen": len(routes),
                    "error": message,
                    "source_url": settings.scraper_source_url,
                },
            )
            await db.commit()
            raise GuardrailError(message)

        run_started_at = datetime.now(tz=IST)
        log_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO scrape_logs (started_at, status, source_url)
                    VALUES (:started_at, 'running', :source_url)
                    RETURNING id
                    """
                ),
                {"started_at": run_started_at, "source_url": settings.scraper_source_url},
            )
        ).scalar_one()
        await db.commit()

        try:
            stats = await upsert_routes(db, routes)
            deactivated = await deactivate_stale(db, run_started_at)
            await db.execute(
                text(
                    """
                    UPDATE scrape_logs
                    SET finished_at = :finished_at,
                        status = :status,
                        routes_added = :routes_added,
                        routes_updated = :routes_updated,
                        routes_failed = :routes_failed,
                        routes_seen = :routes_seen,
                        routes_deactivated = :routes_deactivated,
                        schedules_added = :schedules_added
                    WHERE id = :id
                    """
                ),
                {
                    "id": log_id,
                    "finished_at": datetime.now(tz=IST),
                    "status": "success" if stats["routes_failed"] == 0 else "partial",
                    "routes_deactivated": deactivated,
                    **stats,
                },
            )
            await db.commit()
            logger.info("Scrape complete: %s deactivated=%s", stats, deactivated)
        except Exception as exc:
            await db.rollback()
            await db.execute(
                text(
                    """
                    UPDATE scrape_logs
                    SET finished_at = :finished_at,
                        status = 'failed',
                        error_message = :error_message
                    WHERE id = :id
                    """
                ),
                {"id": log_id, "finished_at": datetime.now(tz=IST), "error_message": str(exc)},
            )
            await db.commit()
            logger.exception("Scrape failed")
            raise


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
