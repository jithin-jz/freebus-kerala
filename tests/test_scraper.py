from scraper.classifier import is_priyadarshini
from scraper.parser import parse_routes, schedules_from_text


def test_classifier_only_allows_ordinary_services():
    assert is_priyadarshini("Ordinary") is True
    assert is_priyadarshini("AC Ordinary") is False
    assert is_priyadarshini("Swift Deluxe") is False


def test_parser_reads_explicit_times():
    html = """
    <table>
      <tr><th>From</th><th>To</th><th>Times</th><th>Type</th></tr>
      <tr><td>Kalpetta</td><td>Kozhikode</td><td>06:30, 07:45</td><td>Ordinary</td></tr>
    </table>
    """
    routes = parse_routes(html, source_url="https://example.test")
    assert len(routes) == 1
    assert routes[0].origin == "Kalpetta"
    assert len(routes[0].schedules) == 2
    assert routes[0].is_priyadarshini is True


def test_parser_reads_source_list_items_with_via_and_frequency_note():
    html = """
    <ul>
      <li>Adoor to Kollam (via Chellakkad) : 06:30</li>
      <li>Thiruvalla to Kottayam : 06:30, 07:20, then every 30 mins a KSRTC ordinary bus available</li>
    </ul>
    """
    routes = parse_routes(html, source_url="https://example.test")
    assert len(routes) == 2
    assert routes[0].destination == "Kollam"
    assert routes[0].via == "Chellakkad"
    assert routes[1].schedules[0].frequency_note == "then every 30 mins a KSRTC ordinary bus available"


def test_parser_expands_frequency_patterns():
    schedules = schedules_from_text("Ordinary every 30 mins from 06:00 to 07:00")
    assert [schedule.departure_time.strftime("%H:%M") for schedule in schedules] == [
        "06:00",
        "06:30",
        "07:00",
    ]
