from datetime import time

from pydantic import BaseModel


class RouteScheduleOut(BaseModel):
    departure_time: time
    days_of_operation: str = "daily"
    frequency_note: str | None = None


class RouteSearchResult(BaseModel):
    route_id: int
    route_name: str
    route_name_ml: str | None = None
    origin_stop: str
    destination_stop: str
    via: str | None = None
    bus_type: str
    is_priyadarshini: bool
    schedules: list[RouteScheduleOut] = []


class SearchResponse(BaseModel):
    query_from: str | None = None
    query_to: str | None = None
    free_only: bool = True
    results: list[RouteSearchResult]

