\
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from capstone_gait.geometry import Point2D, angle_abc_deg, midpoint, normalize_point, signed_trunk_lean_deg


def test_straight_knee_angle():
    hip = Point2D(0, 0)
    knee = Point2D(0, 1)
    ankle = Point2D(0, 2)
    assert math.isclose(angle_abc_deg(hip, knee, ankle), 180.0, abs_tol=1e-6)


def test_body_center_normalization_is_scale_invariant():
    origin = Point2D(0.5, 0.5)
    p = Point2D(0.6, 0.8)
    a = normalize_point(p, origin, 0.1)

    origin2 = Point2D(0.5, 0.5)
    p2 = Point2D(0.7, 1.1)
    b = normalize_point(p2, origin2, 0.2)

    assert math.isclose(a.x, b.x, abs_tol=1e-6)
    assert math.isclose(a.y, b.y, abs_tol=1e-6)


def test_trunk_lean_zero_when_vertical():
    assert math.isclose(
        signed_trunk_lean_deg(Point2D(0.5, 0.8), Point2D(0.5, 0.3)),
        0.0,
        abs_tol=1e-6,
    )
