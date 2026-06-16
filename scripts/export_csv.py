import asyncio
import csv
import sys

from app.database import AsyncSessionLocal
from sqlalchemy import text


async def main() -> None:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT r.route_name, o.name AS origin, d.name AS destination, r.bus_type,
                           r.is_priyadarshini, sch.departure_time
                    FROM routes r
                    JOIN stops o ON o.id = r.origin_stop_id
                    JOIN stops d ON d.id = r.destination_stop_id
                    JOIN schedules sch ON sch.route_id = r.id
                    ORDER BY r.route_name, sch.departure_time
                    """
                )
            )
        ).mappings().all()

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=["route_name", "origin", "destination", "bus_type", "is_priyadarshini", "departure_time"],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(row))


if __name__ == "__main__":
    asyncio.run(main())

