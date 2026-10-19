"""ROS-independent validation and policy for the mock pipeline."""
from dataclasses import dataclass
from math import isfinite, sqrt


@dataclass(frozen=True)
class Candidate:
    detection_id: str
    label: str
    confidence: float
    frame_id: str
    position: tuple
    orientation: tuple


STEPS = (('arm', 'pick'), ('hand', 'close'), ('arm', 'place'), ('hand', 'open'))


def make_bins(labels, positions):
    if not labels or len(set(labels)) != len(labels) or any(not label for label in labels):
        raise ValueError('bin_labels must be nonempty and unique')
    if len(positions) != 3 * len(labels) or not all(isfinite(v) for v in positions):
        raise ValueError('bin_positions must have three finite coordinates per label')
    return {label: tuple(positions[3 * i:3 * i + 3]) for i, label in enumerate(labels)}


def select_bin(candidate, bins, minimum_confidence, frame_id):
    if not isfinite(minimum_confidence) or not 0 <= minimum_confidence <= 1:
        raise ValueError('minimum_confidence must be between zero and one')
    if not candidate.detection_id or candidate.frame_id != frame_id:
        raise ValueError('missing detection ID or unsupported frame; TF is not implemented')
    if (len(candidate.position) != 3 or len(candidate.orientation) != 4
            or not all(isfinite(v) for v in candidate.position + candidate.orientation)):
        raise ValueError('pose must contain finite XYZ and XYZW values')
    if abs(sqrt(sum(v * v for v in candidate.orientation)) - 1.0) > 1e-3:
        raise ValueError('orientation must be a unit quaternion')
    if not isfinite(candidate.confidence) or not 0 <= candidate.confidence <= 1:
        raise ValueError('confidence must be finite and between zero and one')
    if candidate.confidence < minimum_confidence:
        return None
    return bins.get(candidate.label)


def response_error(response):
    if not response.simulated:
        return 'refused non-simulated service response'
    if not response.success:
        return response.message or 'mock controller rejected request'
    return None
