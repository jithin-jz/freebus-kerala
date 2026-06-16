import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.nearby import NearbyResponse
from app.schemas.route import SearchResponse
from app.services.search import nearby_buses, search_routes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["api"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    try:
        row = (
            await db.execute(
                text(
                    """
                    SELECT status, finished_at, routes_added, routes_updated, schedules_added
                    FROM scrape_logs
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                )
            )
        ).mappings().first()
    except Exception as exc:
        logger.warning("Health check could not read database: %s", exc)
        return {"status": "ok", "database": "unavailable", "last_scrape": None}

    return {
        "status": "ok",
        "database": "ok",
        "last_scrape": dict(row) if row else None,
    }


@router.get("/nearby", response_model=NearbyResponse)
async def nearby(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_metres: int | None = Query(None, ge=100, le=5000),
    db: AsyncSession = Depends(get_db),
) -> NearbyResponse:
    settings = get_settings()
    radius = radius_metres or settings.default_nearby_radius_metres
    radius = min(radius, settings.max_nearby_radius_metres)
    results = await nearby_buses(db, lat=lat, lng=lng, radius_metres=radius, free_only=True)
    return NearbyResponse(lat=lat, lng=lng, radius_metres=radius, results=results)


@router.get("/search", response_model=SearchResponse)
async def search(
    from_stop: str | None = Query(None, alias="from"),
    to_stop: str | None = Query(None, alias="to"),
    free_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    results = await search_routes(db, origin=from_stop, destination=to_stop, free_only=free_only)
    return SearchResponse(
        query_from=from_stop,
        query_to=to_stop,
        free_only=free_only,
        results=results,
    )

