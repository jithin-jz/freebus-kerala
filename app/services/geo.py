from math import atan2, cos, radians, sin, sqrt

EARTH_RADIUS_METRES = 6_371_000
WALKING_METRES_PER_MINUTE = 80


def haversine_distance_metres(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    """Return great-circle distance between two WGS84 coordinates."""
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lng2 - lng1)

    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS_METRES * c


def walking_minutes(distance_metres: float) -> int:
    return max(1, round(distance_metres / WALKING_METRES_PER_MINUTE))


def catchability(minutes_until: int, walk_minutes: int) -> str:
    if minutes_until >= walk_minutes + 5:
        return "catchable"
    if minutes_until >= walk_minutes:
        return "tight"
    return "missed"

