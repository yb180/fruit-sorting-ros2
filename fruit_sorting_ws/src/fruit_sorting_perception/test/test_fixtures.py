from math import isfinite

from fruit_sorting_perception.fixtures import DETECTIONS


def test_fixture_ids_are_stable_and_unique():
    ids = [row[0] for row in DETECTIONS]
    assert len(ids) == len(set(ids)) == 5


def test_fixtures_exercise_filtering():
    accepted = [row[1] for row in DETECTIONS
                if row[1] in {'apple', 'tomato', 'cucumber'} and row[2] >= 0.8]
    assert accepted == ['apple', 'tomato', 'cucumber']
    assert any(row[1] == 'unknown' for row in DETECTIONS)
    assert any(row[2] < 0.8 for row in DETECTIONS)


def test_fixture_values_are_finite():
    for _, _, confidence, x, y, z in DETECTIONS:
        assert 0 <= confidence <= 1
        assert all(isfinite(value) for value in (x, y, z))
