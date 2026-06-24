from frost_days.distance import haversine_km


def test_haversine_same_point_is_zero() -> None:
    assert haversine_km(48.8566, 2.3522, 48.8566, 2.3522) == 0


def test_haversine_paris_lyon() -> None:
    distance = haversine_km(48.8566, 2.3522, 45.7640, 4.8357)
    assert 390 <= distance <= 400
