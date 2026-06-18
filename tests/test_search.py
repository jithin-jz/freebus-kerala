from app.services.search import normalize_stop_query


def test_normalize_collapses_whitespace():
    assert normalize_stop_query("  Kalpetta   Town ") == "Kalpetta Town"


def test_normalize_returns_none_for_empty():
    assert normalize_stop_query("") is None
    assert normalize_stop_query(None) is None
    assert normalize_stop_query("   ") is None


def test_normalize_caps_pathological_length():
    assert len(normalize_stop_query("a" * 500)) == 120
