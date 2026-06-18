from __future__ import annotations

import asyncio
import logging
import re

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

# Curated gazetteer of Kerala (and a few border) towns served by KSRTC ordinary
# routes. Town-centre coordinates are accurate enough for nearby-bus matching at
# the default 1-2 km radius. Only well-identified towns are included; tiny or
# ambiguous stop names are intentionally left out so they stay un-located rather
# than producing false "nearby" hits.
KNOWN_STOPS: dict[str, tuple[float, float, str]] = {
    # District HQs / major hubs
    "thiruvananthapuram": (8.5241, 76.9366, "Thiruvananthapuram"),
    "kollam": (8.8932, 76.6141, "Kollam"),
    "alappuzha": (9.4981, 76.3388, "Alappuzha"),
    "kottayam": (9.5916, 76.5222, "Kottayam"),
    "pathanamthitta": (9.2648, 76.7870, "Pathanamthitta"),
    "ernakulam": (9.9816, 76.2999, "Ernakulam"),
    "thrissur": (10.5276, 76.2144, "Thrissur"),
    "palakkad": (10.7867, 76.6548, "Palakkad"),
    "malappuram": (11.0510, 76.0711, "Malappuram"),
    "kozhikode": (11.2588, 75.7804, "Kozhikode"),
    "kalpetta": (11.6101, 76.0824, "Wayanad"),
    "kannur": (11.8745, 75.3704, "Kannur"),
    "kasaragod": (12.4996, 74.9869, "Kasaragod"),
    # Wayanad
    "vythiri": (11.5516, 76.0363, "Wayanad"),
    "sulthan bathery": (11.6643, 76.2570, "Wayanad"),
    "mananthavady": (11.8014, 76.0044, "Wayanad"),
    # Pathanamthitta belt
    "adoor": (9.1583, 76.7333, "Pathanamthitta"),
    "konni": (9.2350, 76.8470, "Pathanamthitta"),
    "kozhencherry": (9.3330, 76.7000, "Pathanamthitta"),
    "ranni": (9.3830, 76.7830, "Pathanamthitta"),
    "thiruvalla": (9.3833, 76.5750, "Pathanamthitta"),
    "pandalam": (9.2167, 76.6783, "Pathanamthitta"),
    "mallappally": (9.4500, 76.6667, "Pathanamthitta"),
    "chittar": (9.3000, 76.9170, "Pathanamthitta"),
    "seethathode": (9.3500, 76.9330, "Pathanamthitta"),
    "vadasserikara": (9.3500, 76.8667, "Pathanamthitta"),
    "pamba": (9.4167, 77.0333, "Pathanamthitta"),
    "vechoochira": (9.4000, 76.8500, "Pathanamthitta"),
    # Kollam belt
    "kottarakkara": (9.0000, 76.7833, "Kollam"),
    "punalur": (9.0167, 76.9220, "Kollam"),
    "pathanapuram": (9.1000, 76.8300, "Kollam"),
    "ayoor": (8.9100, 76.8800, "Kollam"),
    "kayamkulam": (9.1773, 76.5012, "Alappuzha"),
    "haripad": (9.2876, 76.4602, "Alappuzha"),
    "cherthala": (9.6841, 76.3361, "Alappuzha"),
    "chengannur": (9.3150, 76.6150, "Alappuzha"),
    # Kottayam belt
    "changanassery": (9.4419, 76.5366, "Kottayam"),
    "pala": (9.7167, 76.6833, "Kottayam"),
    "erattupetta": (9.6850, 76.7800, "Kottayam"),
    "erumely": (9.4833, 76.8667, "Kottayam"),
    "ponkunnam": (9.5670, 76.7830, "Kottayam"),
    "mundakayam": (9.5333, 76.8833, "Kottayam"),
    # Idukki / high range
    "thodupuzha": (9.8950, 76.7180, "Idukki"),
    "adimaly": (10.0167, 76.9667, "Idukki"),
    "munnar": (10.0889, 77.0595, "Idukki"),
    "devikulam": (10.0700, 77.1050, "Idukki"),
    "kanthalloor": (10.2200, 77.1900, "Idukki"),
    "kattappana": (9.7500, 77.1167, "Idukki"),
    "nedumkandam": (9.8330, 77.1500, "Idukki"),
    "kumily": (9.6000, 77.1670, "Idukki"),
    "vagamon": (9.6856, 76.9075, "Idukki"),
    "cheruthoni": (9.8500, 76.9667, "Idukki"),
    "anakulam": (10.1700, 76.8800, "Idukki"),
    # Ernakulam belt
    "aluva": (10.1004, 76.3570, "Ernakulam"),
    "muvattupuzha": (9.9830, 76.5780, "Ernakulam"),
    # Thrissur belt
    "chalakudy": (10.3000, 76.3360, "Thrissur"),
    "guruvayur": (10.5946, 76.0411, "Thrissur"),
    "athirappilly": (10.2850, 76.5694, "Thrissur"),
    # Malappuram belt
    "manjeri": (11.1200, 76.1200, "Malappuram"),
    "perinthalmanna": (10.9756, 76.2275, "Malappuram"),
    "nilambur": (11.2733, 76.2236, "Malappuram"),
    "ponnani": (10.7670, 75.9250, "Malappuram"),
    "melattur": (10.9830, 76.2830, "Malappuram"),
    "areekode": (11.2050, 76.0700, "Malappuram"),
    # Kozhikode belt
    "koyilandy": (11.4330, 75.7000, "Kozhikode"),
    "mavoor": (11.2670, 75.9330, "Kozhikode"),
    "thamarassery": (11.4170, 75.9330, "Kozhikode"),
    # Border towns (Tamil Nadu / Nilgiris)
    "cumbum": (9.7378, 77.2872, "Theni"),
    "theni": (10.0104, 77.4768, "Theni"),
    "gudalur": (11.5000, 76.4900, "Nilgiris"),
    "pandalur": (11.5500, 76.4330, "Nilgiris"),
}

# In-process cache so repeated stops within a single scrape run hit the network once.
_GEOCODE_CACHE: dict[str, tuple[float | None, float | None, str]] = {}
_GEOCODE_LOCK = asyncio.Lock()
_KERALA_VIEWBOX = "74.8,12.8,77.5,8.2"  # lon/lat bounds to bias results to Kerala.


def normalize_stop_name(name: str) -> str:
    return " ".join(name.lower().replace("ksrtc", "").split()).strip()


def _match_known(normalized: str) -> tuple[float, float, str] | None:
    # Exact match wins, so "palakkad" never resolves to "pala".
    if normalized in KNOWN_STOPS:
        return KNOWN_STOPS[normalized]
    # Otherwise match a known town as a whole word (longest key first) so that
    # "konni medical college" -> Konni, but "pala" does not match "palakkad".
    for known in sorted(KNOWN_STOPS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(known)}\b", normalized):
            return KNOWN_STOPS[known]
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
