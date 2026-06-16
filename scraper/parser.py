from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from bs4 import BeautifulSoup

from scraper.classifier import is_priyadarshini

TIME_RE = re.compile(r"\b(\d{1,2})[:.](\d{2})\s*([AP]\.?M\.?)?\b", re.IGNORECASE)
FREQUENCY_RE = re.compile(
    r"every\s+(\d{1,3})\s*(?:min|mins|minutes).*?"
    r"(?:from|between)?\s*(\d{1,2}[:.]\d{2}\s*(?:[AP]\.?M\.?)?).*?"
    r"(?:to|and|-)\s*(\d{1,2}[:.]\d{2}\s*(?:[AP]\.?M\.?)?)",
    re.IGNORECASE,
)
FREQUENCY_NOTE_RE = re.compile(
    r"(?:then\s+)?every\s+\d{1,3}(?:\s*-\s*\d{1,3})?\s*(?:min|mins|minutes)[^,.;]*",
    re.IGNORECASE,
)
ROUTE_SPLIT_RE = re.compile(r"\s+(?:to|->|-->|-)\s+", re.IGNORECASE)
ROUTE_LINE_RE = re.compile(
    r"^\s*(?P<origin>.+?)\s+to\s+(?P<destination>.+?)\s*:\s*(?P<times>.+?)\s*$",
    re.IGNORECASE,
)
VIA_RE = re.compile(r"^(?P<destination>.+?)\s*\(\s*(?:via\s+)?(?P<via>[^)]+)\s*\)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedSchedule:
    departure_time: time
    days_of_operation: str = "daily"
    frequency_note: str | None = None


@dataclass(frozen=True)
class ParsedRoute:
    origin: str
    destination: str
    route_name: str
    bus_type: str
    is_priyadarshini: bool
    schedules: list[ParsedSchedule] = field(default_factory=list)
    via: str | None = None
    source_url: str | None = None
    raw_text: str = ""


def parse_time_token(token: str) -> time:
    match = TIME_RE.search(token.strip())
    if not match:
        raise ValueError(f"Invalid time token: {token}")
    hour = int(match.group(1))
    minute = int(match.group(2))
    suffix = (match.group(3) or "").replace(".", "").upper()
    if suffix == "PM" and hour != 12:
        hour += 12
    if suffix == "AM" and hour == 12:
        hour = 0
    return time(hour=hour % 24, minute=minute)


def parse_times(text: str) -> list[time]:
    seen: set[time] = set()
    parsed: list[time] = []
    for match in TIME_RE.finditer(text):
        value = parse_time_token(match.group(0))
        if value not in seen:
            seen.add(value)
            parsed.append(value)
    return parsed


def expand_frequency_patterns(text: str) -> list[ParsedSchedule]:
    schedules: list[ParsedSchedule] = []
    for match in FREQUENCY_RE.finditer(text):
        interval = int(match.group(1))
        start = parse_time_token(match.group(2))
        end = parse_time_token(match.group(3))
        cursor = datetime.combine(datetime.today(), start)
        limit = datetime.combine(datetime.today(), end)
        if limit < cursor:
            limit += timedelta(days=1)
        while cursor <= limit:
            schedules.append(
                ParsedSchedule(
                    departure_time=cursor.time().replace(second=0, microsecond=0),
                    frequency_note=match.group(0).strip(),
                )
            )
            cursor += timedelta(minutes=interval)
    return schedules


def schedules_from_text(text: str) -> list[ParsedSchedule]:
    schedules = expand_frequency_patterns(text)
    existing = {schedule.departure_time for schedule in schedules}
    frequency_note = None
    frequency_match = FREQUENCY_NOTE_RE.search(text)
    if frequency_match:
        frequency_note = frequency_match.group(0).strip()
    for parsed in parse_times(text):
        if parsed not in existing:
            schedules.append(ParsedSchedule(departure_time=parsed, frequency_note=frequency_note))
            existing.add(parsed)
    return sorted(schedules, key=lambda schedule: schedule.departure_time)


def infer_route_names(text: str) -> tuple[str, str] | None:
    cleaned = " ".join(text.split())
    if not cleaned:
        return None
    parts = ROUTE_SPLIT_RE.split(cleaned, maxsplit=1)
    if len(parts) != 2:
        return None
    origin = parts[0].strip(" :-")
    destination = re.split(r"\s+\d{1,2}[:.]\d{2}", parts[1], maxsplit=1)[0].strip(" :-")
    if not origin or not destination:
        return None
    return origin, destination


def parse_table_rows(soup: BeautifulSoup, source_url: str | None) -> list[ParsedRoute]:
    routes: list[ParsedRoute] = []
    for row in soup.select("tr"):
        cells = [" ".join(cell.get_text(" ", strip=True).split()) for cell in row.find_all(["td", "th"])]
        if len(cells) < 3 or not schedules_from_text(" ".join(cells)):
            continue
        origin, destination = cells[0], cells[1]
        bus_type = next((cell for cell in cells if "ordinary" in cell.lower()), "Ordinary")
        schedules = schedules_from_text(" ".join(cells[2:]))
        raw_text = " | ".join(cells)
        routes.append(
            ParsedRoute(
                origin=origin,
                destination=destination,
                route_name=f"{origin} to {destination}",
                bus_type=bus_type,
                is_priyadarshini=is_priyadarshini(bus_type, raw_text),
                schedules=schedules,
                source_url=source_url,
                raw_text=raw_text,
            )
        )
    return routes


def parse_route_line(text: str, source_url: str | None) -> ParsedRoute | None:
    cleaned = " ".join(text.replace("\xa0", " ").split())
    match = ROUTE_LINE_RE.match(cleaned)
    if not match:
        return None

    origin = match.group("origin").strip(" :-")
    destination = match.group("destination").strip(" :-")
    via = None
    via_match = VIA_RE.match(destination)
    if via_match:
        destination = via_match.group("destination").strip()
        via = via_match.group("via").strip()

    schedules = schedules_from_text(match.group("times"))
    if not origin or not destination or not schedules:
        return None

    bus_type = "Ordinary"
    return ParsedRoute(
        origin=origin,
        destination=destination,
        route_name=f"{origin} to {destination}",
        bus_type=bus_type,
        is_priyadarshini=is_priyadarshini(bus_type, cleaned),
        schedules=schedules,
        via=via,
        source_url=source_url,
        raw_text=cleaned,
    )


def parse_list_routes(soup: BeautifulSoup, source_url: str | None) -> list[ParsedRoute]:
    routes: list[ParsedRoute] = []
    for item in soup.select("li"):
        route = parse_route_line(item.get_text(" ", strip=True), source_url)
        if route:
            routes.append(route)
    return routes


def parse_text_routes(soup: BeautifulSoup, source_url: str | None) -> list[ParsedRoute]:
    routes: list[ParsedRoute] = []
    for line in soup.get_text("\n").splitlines():
        text = " ".join(line.split())
        if not text or not TIME_RE.search(text):
            continue
        inferred = infer_route_names(text)
        if not inferred:
            continue
        origin, destination = inferred
        bus_type = "Ordinary" if "ordinary" in text.lower() else ""
        schedules = schedules_from_text(text)
        routes.append(
            ParsedRoute(
                origin=origin,
                destination=destination,
                route_name=f"{origin} to {destination}",
                bus_type=bus_type or "Unknown",
                is_priyadarshini=is_priyadarshini(bus_type, text),
                schedules=schedules,
                source_url=source_url,
                raw_text=text,
            )
        )
    return routes


def parse_routes(html: str, source_url: str | None = None) -> list[ParsedRoute]:
    soup = BeautifulSoup(html, "html.parser")
    routes = parse_table_rows(soup, source_url)
    routes.extend(parse_list_routes(soup, source_url))
    if not routes:
        routes.extend(parse_text_routes(soup, source_url))

    deduped: dict[tuple[str, str, str], ParsedRoute] = {}
    for route in routes:
        key = (route.origin.lower(), route.destination.lower(), route.raw_text.lower())
        deduped[key] = route
    return list(deduped.values())
