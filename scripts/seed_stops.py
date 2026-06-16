import asyncio
import logging

from app.database import AsyncSessionLocal
from slugify import slugify
from sqlalchemy import text

logger = logging.getLogger(__name__)

SEED_STOPS = [
    ("Kalpetta KSRTC", "Wayanad", 11.6101, 76.0824),
    ("Kozhikode KSRTC", "Kozhikode", 11.2588, 75.7804),
    ("Vythiri", "Wayanad", 11.5516, 76.0363),
    ("Sulthan Bathery", "Wayanad", 11.6643, 76.2570),
    ("Mananthavady", "Wayanad", 11.8014, 76.0044),
]


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    async with AsyncSessionLocal() as db:
        for name, district, lat, lng in SEED_STOPS:
            await db.execute(
                text(
                    """
                    INSERT INTO stops (name, name_slug, district, location, is_major)
                    VALUES (:name, :slug, :district, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), true)
                    ON CONFLICT (name_slug) DO UPDATE
                    SET name = EXCLUDED.name,
                        district = EXCLUDED.district,
                        location = EXCLUDED.location,
                        is_major = EXCLUDED.is_major,
                        updated_at = NOW()
                    """
                ),
                {"name": name, "slug": slugify(name), "district": district, "lat": lat, "lng": lng},
            )
        await db.commit()
    logger.info("Seeded %s stops", len(SEED_STOPS))


if __name__ == "__main__":
    asyncio.run(main())

