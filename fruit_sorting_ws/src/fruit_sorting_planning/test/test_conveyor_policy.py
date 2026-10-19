import pytest

from fruit_sorting_planning.conveyor_policy import fresh_sample, in_pick_window


@pytest.mark.parametrize('x, expected', [
    (0.09, False), (0.1, True), (0.2, True), (0.3, True), (0.31, False),
    (float('nan'), False), (float('inf'), False),
])
def test_only_finite_targets_inside_window_are_selected(x, expected):
    assert in_pick_window(x, 0.1, 0.3) is expected


@pytest.mark.parametrize('minimum, maximum', [(0.3, 0.1), (0.1, 0.1),
                                           (float('nan'), 0.3)])
def test_invalid_window_is_rejected(minimum, maximum):
    with pytest.raises(ValueError):
        in_pick_window(0.2, minimum, maximum)


@pytest.mark.parametrize('sample, now, after, expected', [
    (1_000_000_000, 1_100_000_000, None, True),
    (1_000_000_000, 1_500_000_000, None, True),
    (1_000_000_000, 1_500_000_001, None, False),
    (1_100_000_000, 1_000_000_000, None, False),
    (0, 1_000_000_000, None, False),
    (1_000_000_000, 1_100_000_000, 1_000_000_000, False),
    (1_000_000_001, 1_100_000_000, 1_000_000_000, True),
    (999_999_999, 1_100_000_000, 1_000_000_000, False),
])
def test_stale_future_or_pre_stop_sample_cannot_authorize_grasp(sample, now, after, expected):
    assert fresh_sample(sample, now, 0.5, after) is expected


@pytest.mark.parametrize('age', [0.0, -1.0, float('inf'), float('nan')])
def test_invalid_sample_age_is_rejected(age):
    with pytest.raises(ValueError):
        fresh_sample(1, 2, age)
