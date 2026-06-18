from __future__ import annotations

import asyncio
import logging

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

# Fast-path gazetteer for common hubs. Avoids a network round trip and guarantees
# coordinates even when the geocoding service is unavailable.
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

# In-process cache so repeated stops within a single scrape run hit the network once.
_GEOCODE_CACHE: dict[str, tuple[float | None, float | None, str]] = {}
_GEOCODE_LOCK = asyncio.Lock()
_KERALA_VIEWBOX = "74.8,12.8,77.5,8.2"  # lon/lat bounds to bias results to Kerala.


def normalize_stop_name(name: str) -> str:
    return " ".join(name.lower().replace("ksrtc", "").split()).strip()


def _match_known(normalized: str) -> tuple[float, float, str] | None:
    for known, coords in KNOWN_STOPS.items():
        if known in normalized:
            return coords
    return None


async def _nominatim_lookup(name: str) -> tuple[float | None, float | None, str]:
    """Query OSM Nominatim, biased to Kerala. Returns (lat, lng, district)."""
    settings = get_settings()
    params = {
        "q": f"{name}, Kerala, India",
        "format": "jsonv2",
        "limit": "1",
        "countrycodes": "in",
        "viewbox": _KERALA_VIEWBOX,
        "bounded": "1",
        "addressdetails": "1",
    }
    headers = {"User-Agent": settings.scraper_user_agent}
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            response = await client.get(settings.osm_nominatim_url, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Nominatim lookup failed for %s: %s", name, exc)
        return None, None, "Kerala"

    if not payload:
        return None, None, "Kerala"

    top = payload[0]
    address = top.get("address", {})
    district = (
        address.get("state_district")
        or address.get("county")
        or address.get("district")
        or "Kerala"
    )
    try:
        return float(top["lat"]), float(top["lon"]), district
    except (KeyError, TypeError, ValueError):
        return None, None, "Kerala"


async def geocode_stop(name: str) -> tuple[float | None, float | None, str]:
    """Resolve a stop name to coordinates.

    Order: in-process cache -> known gazetteer -> Nominatim (if enabled).
    Never raises; returns (None, None, "Kerala") when nothing resolves.
    """
    settings = get_settings()
    normalized = normalize_stop_name(name)
    if not normalized:
        return None, None, "Kerala"

    if normalized in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[normalized]

    known = _match_known(normalized)
    if known is not None:
        _GEOCODE_CACHE[normalized] = known
        return known

    if not settings.geocoding_enabled:
        return None, None, "Kerala"

    # Serialise network lookups to respect the public Nominatim usage policy.
    async with _GEOCODE_LOCK:
        if normalized in _GEOCODE_CACHE:
            return _GEOCODE_CACHE[normalized]
        await asyncio.sleep(max(settings.scraper_rate_limit_seconds, 1.0))
        result = await _nominatim_lookup(name)
        _GEOCODE_CACHE[normalized] = result
        return result
