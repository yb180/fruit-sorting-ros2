from dataclasses import replace
from types import SimpleNamespace

import pytest

from fruit_sorting_planning.policy import Candidate, make_bins, response_error, select_bin


VALID = Candidate('id-1', 'apple', 0.9, 'mock_table', (0.1, 0.0, 0.05),
                  (0.0, 0.0, 0.0, 1.0))
BINS = make_bins(['apple', 'tomato'], [0.4, -0.2, 0.05, 0.4, 0.2, 0.05])


def test_category_selects_destination():
    assert select_bin(VALID, BINS, 0.8, 'mock_table') == (0.4, -0.2, 0.05)
    assert select_bin(replace(VALID, label='tomato'), BINS, 0.8, 'mock_table') == (
        0.4, 0.2, 0.05)


@pytest.mark.parametrize('change', [{'confidence': 0.79}, {'label': 'unknown'}])
def test_unsupported_or_uncertain_detection_is_filtered(change):
    assert select_bin(replace(VALID, **change), BINS, 0.8, 'mock_table') is None


def test_confidence_boundary_is_inclusive():
    assert select_bin(replace(VALID, confidence=0.8), BINS, 0.8, 'mock_table')


@pytest.mark.parametrize('change', [
    {'detection_id': ''}, {'frame_id': 'camera'},
    {'position': (float('nan'), 0.0, 0.0)},
    {'position': (float('inf'), 0.0, 0.0)},
    {'position': (0.0, 0.0)},
    {'orientation': (0.0, 0.0, 0.0, 0.0)},
    {'orientation': (0.0, 0.0, 0.0, 2.0)},
    {'orientation': (0.0, 0.0, 0.0, float('nan'))},
    {'confidence': float('nan')}, {'confidence': -0.1}, {'confidence': 1.1},
])
def test_invalid_detection_is_rejected(change):
    with pytest.raises(ValueError):
        select_bin(replace(VALID, **change), BINS, 0.8, 'mock_table')


@pytest.mark.parametrize('threshold', [-1.0, 1.1, float('nan')])
def test_invalid_threshold_is_rejected(threshold):
    with pytest.raises(ValueError):
        select_bin(VALID, BINS, threshold, 'mock_table')


@pytest.mark.parametrize('labels, positions', [
    ([], []), (['apple', 'apple'], [0.0] * 6), ([''], [0.0] * 3),
    (['apple'], [0.0] * 2), (['apple'], [0.0, 0.0, float('inf')]),
])
def test_invalid_bin_configuration_is_rejected(labels, positions):
    with pytest.raises(ValueError):
        make_bins(labels, positions)


@pytest.mark.parametrize('success, simulated, expected', [
    (True, True, None), (False, True, 'rejected'),
    (True, False, 'refused non-simulated service response'),
    (False, False, 'refused non-simulated service response'),
])
def test_controller_response_gate(success, simulated, expected):
    response = SimpleNamespace(success=success, simulated=simulated, message='rejected')
    assert response_error(response) == expected
