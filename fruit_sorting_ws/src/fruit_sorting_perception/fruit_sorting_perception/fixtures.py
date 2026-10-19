"""Synthetic coordinates in metres; these are not robot calibration data."""

# Stable IDs make repeated frames safe to deduplicate for the demo.
# id, class label, confidence, x, y, z
DETECTIONS = (
    ('apple-001', 'apple', 0.96, 0.10, 0.00, 0.05),
    ('tomato-001', 'tomato', 0.94, 0.15, 0.05, 0.05),
    ('cucumber-001', 'cucumber', 0.92, 0.20, 0.10, 0.05),
    ('unknown-001', 'unknown', 0.99, 0.25, 0.10, 0.05),
    ('uncertain-001', 'apple', 0.20, 0.30, 0.10, 0.05),
)
