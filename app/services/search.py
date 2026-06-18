from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.geo import catchability, walking_minutes
from app.services.schedule import current_day_code, minutes_until_departure, next_departure_at


def normalize_stop_query(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.strip().split())
    # Defensive cap so a pathological query string can't blow up the ILIKE.
    normalized = normalized[:120]
    return normalized or None


def _day_filter_clause(alias: str = "sch") -> str:
    """SQL fragment matching schedules that run today (or every day)."""
    return (
        f"({alias}.days_of_operation = 'daily' OR {alias}.days_of_operation = '' "
        f"OR {alias}.days_of_operation ILIKE :day_like)"
    )


async def search_routes(
    db: AsyncSession,
    origin: str | None,
    destination: str | None,
    free_only: bool = True,
) -> list[dict[str, Any]]:
    origin = normalize_stop_query(origin)
    destination = normalize_stop_query(destination)

    clauses = ["r.is_active = true", "sch.is_active = true", _day_filter_clause()]
    joins: list[str] = []
    params: dict[str, Any] = {"day_like": f"%{current_day_code()}%"}

    # Match against every stop on the route (origin, intermediate, destination)
    # via route_stops, enforcing correct travel direction when both ends are given.
    if origin:
        joins.append("JOIN route_stops rso ON rso.route_id = r.id")
        joins.append("JOIN stops bo ON bo.id = rso.stop_id")
        clauses.append("bo.name ILIKE :origin")
        params["origin"] = f"%{origin}%"
    if destination:
        joins.append("JOIN route_stops rsd ON rsd.route_id = r.id")
        joins.append("JOIN stops al ON al.id = rsd.stop_id")
        clauses.append("al.name ILIKE :destination")
        params["destination"] = f"%{destination}%"
    if origin and destination:
        clauses.append("rso.sequence < rsd.sequence")
    if free_only:
        clauses.append("r.is_priyadarshini = true")

    sql = text(
        f"""
        SELECT DISTINCT
            r.id AS route_id,
            r.route_name,
            r.route_name_ml,
            r.via,
            r.bus_type,
            r.is_priyadarshini,
            o.name AS origin_stop,
            d.name AS destination_stop,
            sch.departure_time,
            sch.days_of_operation,
            sch.frequency_note
        FROM routes r
        JOIN stops o ON o.id = r.origin_stop_id
        JOIN stops d ON d.id = r.destination_stop_id
        JOIN schedules sch ON sch.route_id = r.id
        {" ".join(joins)}
        WHERE {" AND ".join(clauses)}
        ORDER BY o.name, d.name, sch.departure_time
        LIMIT 200
        """
    )
    rows = (await db.execute(sql, params)).mappings().all()

    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        route_id = row["route_id"]
        if route_id not in grouped:
            grouped[route_id] = {
                "route_id": route_id,
                "route_name": row["route_name"],
                "route_name_ml": row["route_name_ml"],
                "origin_stop": row["origin_stop"],
                "destination_stop": row["destination_stop"],
                "via": row["via"],
                "bus_type": row["bus_type"],
                "is_priyadarshini": row["is_priyadarshini"],
                "schedules": [],
            }
        grouped[route_id]["schedules"].append(
            {
                "departure_time": row["departure_time"],
                "days_of_operation": row["days_of_operation"],
                "frequency_note": row["frequency_note"],
            }
        )
    return list(grouped.values())


async def nearby_buses(
    db: AsyncSession,
    lat: float,
    lng: float,
    radius_metres: int,
    free_only: bool = True,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    clauses = [
        "r.is_active = true",
        "sch.is_active = true",
        "s.location IS NOT NULL",
        # You can't board at the final terminus, so skip the last stop on the route.
        "rs.stop_id <> r.destination_stop_id",
        _day_filter_clause(),
    ]
    params: dict[str, Any] = {
        "lat": lat,
        "lng": lng,
        "radius": radius_metres,
        "day_like": f"%{current_day_code()}%",
    }
    if free_only:
        clauses.append("r.is_priyadarshini = true")

    # PostGIS does the spatial filter (uses the GIST index) and distance sort.
    sql = text(
        f"""
        SELECT
            s.id AS stop_id,
            s.name AS stop_name,
            ST_Distance(
                s.location::geography,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
            ) AS distance_metres,
            rs.arrival_offset_minutes,
            r.id AS route_id,
            r.route_name,
            r.via,
            r.bus_type,
            r.is_priyadarshini,
            o.name AS origin_stop,
            d.name AS destination_stop,
            sch.departure_time
        FROM route_stops rs
        JOIN stops s ON s.id = rs.stop_id
        JOIN routes r ON r.id = rs.route_id
        JOIN stops o ON o.id = r.origin_stop_id
        JOIN stops d ON d.id = r.destination_stop_id
        JOIN schedules sch ON sch.route_id = r.id
        WHERE {" AND ".join(clauses)}
          AND ST_DWithin(
                s.location::geography,
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                :radius
          )
        ORDER BY distance_metres
        LIMIT 500
        """
    )
    rows = (await db.execute(sql, params)).mappings().all()

    best_by_route: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        distance = float(row["distance_metres"])
        walk = walking_minutes(distance)
        # Pass-by time at this stop = origin departure + offset (when known).
        offset = row["arrival_offset_minutes"] or 0
        minutes = minutes_until_departure(row["departure_time"]) + offset
        departure = next_departure_at(row["departure_time"])
        item = {
            "route_id": row["route_id"],
            "route_name": row["route_name"],
            "origin_stop": row["origin_stop"],
            "destination_stop": row["destination_stop"],
            "via": row["via"],
            "bus_type": row["bus_type"],
            "is_priyadarshini": row["is_priyadarshini"],
            "stop_id": row["stop_id"],
            "stop_name": row["stop_name"],
            "distance_metres": round(distance),
            "walk_minutes": walk,
            "departure_time": row["departure_time"].strftime("%H:%M"),
            "departure_iso": departure.isoformat(),
            "minutes_until": minutes,
            "catchability": catchability(minutes, walk),
        }
        key = (row["route_id"], row["departure_time"].strftime("%H:%M"))
        current = best_by_route.get(key)
        if current is None or item["distance_metres"] < current["distance_metres"]:
            best_by_route[key] = item

    return sorted(
        best_by_route.values(),
        key=lambda bus: (bus["minutes_until"], bus["distance_metres"]),
    )[:max_results]


def group_departures_by_route(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["route_id"]].append(row)
    return grouped


async def get_route_detail(db: AsyncSession, route_id: int) -> dict[str, Any] | None:
    """Return a single route with its ordered stops and active schedules."""
    route = (
        await db.execute(
            text(
                """
                SELECT r.id AS route_id, r.route_name, r.route_name_ml, r.via,
                       r.bus_type, r.is_priyadarshini, r.is_active,
                       o.name AS origin_stop, d.name AS destination_stop
                FROM routes r
                JOIN stops o ON o.id = r.origin_stop_id
                JOIN stops d ON d.id = r.destination_stop_id
                WHERE r.id = :route_id
                """
            ),
            {"route_id": route_id},
        )
    ).mappings().first()
    if route is None:
        return None

    stops = (
        await db.execute(
            text(
                """
                SELECT rs.sequence, rs.arrival_offset_minutes, s.name AS stop_name
                FROM route_stops rs
                JOIN stops s ON s.id = rs.stop_id
                WHERE rs.route_id = :route_id
                ORDER BY rs.sequence
                """
            ),
            {"route_id": route_id},
        )
    ).mappings().all()

    schedules = (
        await db.execute(
            text(
                """
                SELECT departure_time, days_of_operation, frequency_note
                FROM schedules
                WHERE route_id = :route_id AND is_active = true
                ORDER BY departure_time
                """
            ),
            {"route_id": route_id},
        )
    ).mappings().all()

    return {
        **dict(route),
        "stops": [dict(stop) for stop in stops],
        "schedules": [dict(schedule) for schedule in schedules],
    }

