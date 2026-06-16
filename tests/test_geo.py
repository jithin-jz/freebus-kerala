from app.services.geo import catchability, haversine_distance_metres, walking_minutes


def test_haversine_distance_for_nearby_points():
    distance = haversine_distance_metres(11.6101, 76.0824, 11.6110, 76.0824)
    assert 90 <= distance <= 110


def test_walking_minutes_has_minimum_one():
    assert walking_minutes(10) == 1


def test_catchability_thresholds():
    assert catchability(minutes_until=15, walk_minutes=8) == "catchable"
    assert catchability(minutes_until=8, walk_minutes=8) == "tight"
    assert catchability(minutes_until=6, walk_minutes=8) == "missed"

