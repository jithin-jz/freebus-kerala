from __future__ import annotations

import hashlib
import logging
from typing import Any

from slugify import slugify
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from scraper.geocoder import geocode_stop
from scraper.parser import ParsedRoute

logger = logging.getLogger(__name__)


async def upsert_stop(db: AsyncSession, name: str) -> int:
    lat, lng, district = await geocode_stop(name)
    slug = slugify(name)
    if lat is not None and lng is not None:
        sql = text(
            """
            INSERT INTO stops (name, name_slug, district, location, is_major)
            VALUES (:name, :slug, :district, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), true)
            ON CONFLICT (name_slug) DO UPDATE
            SET name = EXCLUDED.name,
                district = EXCLUDED.district,
                location = EXCLUDED.location,
                updated_at = NOW()
            RETURNING id
            """
        )
        params: dict[str, Any] = {"name": name, "slug": slug, "district": district, "lat": lat, "lng": lng}
    else:
        sql = text(
            """
            INSERT INTO stops (name, name_slug, district, is_major)
            VALUES (:name, :slug, :district, false)
            ON CONFLICT (name_slug) DO UPDATE
            SET name = EXCLUDED.name,
                district = EXCLUDED.district,
                updated_at = NOW()
            RETURNING id
            """
        )
        params = {"name": name, "slug": slug, "district": district}
    return int((await db.execute(sql, params)).scalar_one())


async def upsert_route(db: AsyncSession, route: ParsedRoute) -> int:
    origin_id = await upsert_stop(db, route.origin)
    destination_id = await upsert_stop(db, route.destination)
    data_hash = hashlib.sha256(route.raw_text.encode("utf-8")).hexdigest()
    via = route.via or ""
    route_id = (
        await db.execute(
            text(
                """
                INSERT INTO routes (
                    origin_stop_id,
                    destination_stop_id,
                    route_name,
                    via,
                    bus_type,
                    is_priyadarshini,
                    source_url,
                    data_hash,
                    last_scraped_at
                )
                VALUES (
                    :origin_stop_id,
                    :destination_stop_id,
                    :route_name,
                    :via,
                    :bus_type,
                    :is_priyadarshini,
                    :source_url,
                    :data_hash,
                    NOW()
                )
                ON CONFLICT (origin_stop_id, destination_stop_id, via, bus_type) DO UPDATE
                SET route_name = EXCLUDED.route_name,
                    is_priyadarshini = EXCLUDED.is_priyadarshini,
                    source_url = EXCLUDED.source_url,
                    data_hash = EXCLUDED.data_hash,
                    last_scraped_at = NOW(),
                    updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "origin_stop_id": origin_id,
                "destination_stop_id": destination_id,
                "route_name": route.route_name,
                "via": via,
                "bus_type": route.bus_type,
                "is_priyadarshini": route.is_priyadarshini,
                "source_url": route.source_url,
                "data_hash": data_hash,
            },
        )
    ).scalar_one()
    return int(route_id)


async def upsert_routes(db: AsyncSession, routes: list[ParsedRoute]) -> dict[str, int]:
    stats = {"routes_added": 0, "routes_updated": 0, "routes_failed": 0, "schedules_added": 0}
    for route in routes:
        try:
            route_id = await upsert_route(db, route)
            stats["routes_updated"] += 1
            for schedule in route.schedules:
                result = await db.execute(
                    text(
                        """
                        INSERT INTO schedules (route_id, departure_time, days_of_operation, frequency_note)
                        VALUES (:route_id, :departure_time, :days_of_operation, :frequency_note)
                        ON CONFLICT (route_id, departure_time, days_of_operation) DO NOTHING
                        """
                    ),
                    {
                        "route_id": route_id,
                        "departure_time": schedule.departure_time,
                        "days_of_operation": schedule.days_of_operation,
                        "frequency_note": schedule.frequency_note,
                    },
                )
                if result.rowcount:
                    stats["schedules_added"] += 1
        except Exception:
            stats["routes_failed"] += 1
            logger.exception("Failed to upsert route: %s", route.route_name)
    return stats
