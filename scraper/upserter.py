from __future__ import annotations

import hashlib
import logging
from datetime import datetime
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


async def upsert_route(db: AsyncSession, route: ParsedRoute) -> tuple[int, bool]:
    """Upsert a route. Returns (route_id, inserted) where inserted is True for new rows."""
    origin_id = await upsert_stop(db, route.origin)
    destination_id = await upsert_stop(db, route.destination)
    data_hash = hashlib.sha256(route.raw_text.encode("utf-8")).hexdigest()
    via = route.via or ""
    row = (
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
                    is_active,
                    source_url,
                    data_hash,
                    last_scraped_at,
                    last_seen_at
                )
                VALUES (
                    :origin_stop_id,
                    :destination_stop_id,
                    :route_name,
                    :via,
                    :bus_type,
                    :is_priyadarshini,
                    true,
                    :source_url,
                    :data_hash,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (origin_stop_id, destination_stop_id, via, bus_type) DO UPDATE
                SET route_name = EXCLUDED.route_name,
                    is_priyadarshini = EXCLUDED.is_priyadarshini,
                    is_active = true,
                    source_url = EXCLUDED.source_url,
                    data_hash = EXCLUDED.data_hash,
                    last_scraped_at = NOW(),
                    last_seen_at = NOW(),
                    updated_at = NOW()
                RETURNING id, (xmax = 0) AS inserted
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
    ).mappings().one()

    route_id = int(row["id"])
    await sync_route_stops(db, route_id, origin_id, destination_id, route)
    return route_id, bool(row["inserted"])


async def sync_route_stops(
    db: AsyncSession,
    route_id: int,
    origin_id: int,
    destination_id: int,
    route: ParsedRoute,
) -> None:
    """Rebuild the ordered stop sequence for a route (origin, via..., destination)."""
    sequence_ids: list[int] = [origin_id]
    for via_name in route.via_stops:
        try:
            sequence_ids.append(await upsert_stop(db, via_name))
        except Exception:
            logger.exception("Failed to upsert via stop %s for route %s", via_name, route_id)
    sequence_ids.append(destination_id)

    # Replace the full sequence so removed intermediate stops don't linger.
    await db.execute(
        text("DELETE FROM route_stops WHERE route_id = :route_id"),
        {"route_id": route_id},
    )
    seen: set[int] = set()
    sequence = 0
    for stop_id in sequence_ids:
        if stop_id in seen:
            continue
        seen.add(stop_id)
        await db.execute(
            text(
                """
                INSERT INTO route_stops (route_id, stop_id, sequence)
                VALUES (:route_id, :stop_id, :sequence)
                ON CONFLICT (route_id, sequence) DO UPDATE
                SET stop_id = EXCLUDED.stop_id
                """
            ),
            {"route_id": route_id, "stop_id": stop_id, "sequence": sequence},
        )
        sequence += 1


async def upsert_routes(db: AsyncSession, routes: list[ParsedRoute]) -> dict[str, int]:
    stats = {
        "routes_added": 0,
        "routes_updated": 0,
        "routes_failed": 0,
        "routes_seen": 0,
        "schedules_added": 0,
    }
    for route in routes:
        try:
            route_id, inserted = await upsert_route(db, route)
            stats["routes_seen"] += 1
            if inserted:
                stats["routes_added"] += 1
            else:
                stats["routes_updated"] += 1
            for schedule in route.schedules:
                result = await db.execute(
                    text(
                        """
                        INSERT INTO schedules (route_id, departure_time, days_of_operation,
                                               frequency_note, last_seen_at)
                        VALUES (:route_id, :departure_time, :days_of_operation,
                                :frequency_note, NOW())
                        ON CONFLICT (route_id, departure_time, days_of_operation) DO UPDATE
                        SET frequency_note = EXCLUDED.frequency_note,
                            is_active = true,
                            last_seen_at = NOW()
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


async def deactivate_stale(db: AsyncSession, run_started_at: datetime) -> int:
    """Deactivate routes/schedules not seen during the current scrape run."""
    await db.execute(
        text(
            """
            UPDATE schedules SET is_active = false
            WHERE is_active = true
              AND (last_seen_at IS NULL OR last_seen_at < :run_started_at)
            """
        ),
        {"run_started_at": run_started_at},
    )
    result = await db.execute(
        text(
            """
            UPDATE routes SET is_active = false, updated_at = NOW()
            WHERE is_active = true
              AND (last_seen_at IS NULL OR last_seen_at < :run_started_at)
            """
        ),
        {"run_started_at": run_started_at},
    )
    return result.rowcount or 0
