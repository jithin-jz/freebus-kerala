from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.geo import catchability, haversine_distance_metres, walking_minutes
from app.services.schedule import minutes_until_departure, next_departure_at


def normalize_stop_query(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


async def search_routes(
    db: AsyncSession,
    origin: str | None,
    destination: str | None,
    free_only: bool = True,
) -> list[dict[str, Any]]:
    origin = normalize_stop_query(origin)
    destination = normalize_stop_query(destination)

    clauses = ["sch.is_active = true"]
    params: dict[str, Any] = {}

    if origin:
        clauses.append("o.name ILIKE :origin")
        params["origin"] = f"%{origin}%"
    if destination:
        clauses.append("d.name ILIKE :destination")
        params["destination"] = f"%{destination}%"
    if free_only:
        clauses.append("r.is_priyadarshini = true")

    sql = text(
        f"""
        SELECT
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
    clauses = ["sch.is_active = true", "s.location IS NOT NULL"]
    if free_only:
        clauses.append("r.is_priyadarshini = true")

    sql = text(
        f"""
        SELECT
            s.id AS stop_id,
            s.name AS stop_name,
            ST_Y(s.location::geometry) AS stop_lat,
            ST_X(s.location::geometry) AS stop_lng,
            r.id AS route_id,
            r.route_name,
            r.via,
            r.bus_type,
            r.is_priyadarshini,
            o.name AS origin_stop,
            d.name AS destination_stop,
            sch.departure_time
        FROM stops s
        JOIN routes r ON r.origin_stop_id = s.id
        JOIN stops o ON o.id = r.origin_stop_id
        JOIN stops d ON d.id = r.destination_stop_id
        JOIN schedules sch ON sch.route_id = r.id
        WHERE {" AND ".join(clauses)}
        ORDER BY sch.departure_time
        LIMIT 500
        """
    )
    rows = (await db.execute(sql)).mappings().all()

    best_by_route: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        if row["stop_lat"] is None or row["stop_lng"] is None:
            continue
        distance = haversine_distance_metres(lat, lng, float(row["stop_lat"]), float(row["stop_lng"]))
        if distance > radius_metres:
            continue
        walk = walking_minutes(distance)
        minutes = minutes_until_departure(row["departure_time"])
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

