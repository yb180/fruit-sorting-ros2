"""ROS-independent freshness and pick-window policy for the conveyor demo."""
from math import isfinite


def in_pick_window(x, minimum, maximum):
    if not all(isfinite(value) for value in (minimum, maximum)) or minimum >= maximum:
        raise ValueError('pick window must have finite increasing bounds')
    return isfinite(x) and minimum <= x <= maximum


def fresh_sample(sample_ns, now_ns, max_age_seconds, after_ns=None):
    if not isfinite(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError('sample age limit must be positive and finite')
    if sample_ns <= 0 or now_ns < sample_ns:
        return False
    if after_ns is not None and sample_ns <= after_ns:
        return False
    return (now_ns - sample_ns) / 1e9 <= max_age_seconds
