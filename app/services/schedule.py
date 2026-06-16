from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def parse_time(value: str | time) -> time:
    if isinstance(value, time):
        return value
    normalized = value.strip().upper().replace(".", ":")
    for suffix in (" AM", " PM"):
        if normalized.endswith(suffix):
            return datetime.strptime(normalized, "%I:%M %p").time()
    return datetime.strptime(normalized, "%H:%M").time()


def next_departure_at(departure_time: str | time, now: datetime | None = None) -> datetime:
    current = now or now_ist()
    if current.tzinfo is None:
        current = current.replace(tzinfo=IST)
    departure = parse_time(departure_time)
    candidate = datetime.combine(current.date(), departure, tzinfo=IST)
    if candidate <= current:
        candidate += timedelta(days=1)
    return candidate


def minutes_until_departure(departure_time: str | time, now: datetime | None = None) -> int:
    departure = next_departure_at(departure_time, now)
    current = now or now_ist()
    if current.tzinfo is None:
        current = current.replace(tzinfo=IST)
    return max(0, round((departure - current).total_seconds() / 60))

