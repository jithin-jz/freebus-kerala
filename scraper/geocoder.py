import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

KNOWN_STOPS: dict[str, tuple[float, float, str]] = {
    "kalpetta": (11.6101, 76.0824, "Wayanad"),
    "kozhikode": (11.2588, 75.7804, "Kozhikode"),
    "vythiri": (11.5516, 76.0363, "Wayanad"),
    "sulthan bathery": (11.6643, 76.2570, "Wayanad"),
    "mananthavady": (11.8014, 76.0044, "Wayanad"),
    "thrissur": (10.5276, 76.2144, "Thrissur"),
    "ernakulam": (9.9816, 76.2999, "Ernakulam"),
    "thiruvananthapuram": (8.5241, 76.9366, "Thiruvananthapuram"),
}


def normalize_stop_name(name: str) -> str:
    return " ".join(name.lower().replace("ksrtc", "").split()).strip()


async def geocode_stop(name: str) -> tuple[float | None, float | None, str]:
    """Return known coordinates first; OSM lookup can be added behind this boundary."""
    settings = get_settings()
    normalized = normalize_stop_name(name)
    for known, (lat, lng, district) in KNOWN_STOPS.items():
        if known in normalized:
            return lat, lng, district
    logger.debug("No local coordinate match for %s using %s", name, settings.osm_overpass_url)
    return None, None, "Kerala"

