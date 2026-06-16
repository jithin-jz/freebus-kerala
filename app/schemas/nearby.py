from pydantic import BaseModel, Field


class NearbyBus(BaseModel):
    route_id: int
    route_name: str
    origin_stop: str
    destination_stop: str
    via: str | None = None
    bus_type: str
    is_priyadarshini: bool
    stop_id: int
    stop_name: str
    distance_metres: int
    walk_minutes: int
    departure_time: str
    departure_iso: str
    minutes_until: int
    catchability: str = Field(pattern="^(catchable|tight|missed)$")


class NearbyResponse(BaseModel):
    lat: float
    lng: float
    radius_metres: int
    results: list[NearbyBus]

