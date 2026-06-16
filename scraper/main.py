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
from scraper.upserter import upsert_routes

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    fetcher = RateLimitedFetcher()
    html = await fetcher.fetch(settings.scraper_source_url)
    routes = parse_routes(html, source_url=settings.scraper_source_url)
    logger.info("Parsed %s candidate routes", len(routes))

    if dry_run:
        logger.info("Dry run enabled; parsed data was not written")
        return

    async with AsyncSessionLocal() as db:
        log_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO scrape_logs (status, source_url)
                    VALUES ('running', :source_url)
                    RETURNING id
                    """
                ),
                {"source_url": settings.scraper_source_url},
            )
        ).scalar_one()
        await db.commit()

        try:
            stats = await upsert_routes(db, routes)
            await db.execute(
                text(
                    """
                    UPDATE scrape_logs
                    SET finished_at = :finished_at,
                        status = :status,
                        routes_added = :routes_added,
                        routes_updated = :routes_updated,
                        routes_failed = :routes_failed,
                        schedules_added = :schedules_added
                    WHERE id = :id
                    """
                ),
                {
                    "id": log_id,
                    "finished_at": datetime.now(tz=IST),
                    "status": "success" if stats["routes_failed"] == 0 else "partial",
                    **stats,
                },
            )
            await db.commit()
            logger.info("Scrape complete: %s", stats)
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

