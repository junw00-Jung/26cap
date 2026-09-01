\
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

EPS = 1e-9


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float


def distance(a: Point2D, b: Point2D) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def midpoint(a: Point2D, b: Point2D) -> Point2D:
    return Point2D((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def angle_abc_deg(a: Point2D, b: Point2D, c: Point2D) -> float:
    """Angle ABC in degrees, 0..180."""
    v1 = (a.x - b.x, a.y - b.y)
    v2 = (c.x - b.x, c.y - b.y)
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < EPS or n2 < EPS:
        return float("nan")
    cosv = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    cosv = max(-1.0, min(1.0, cosv))
    return math.degrees(math.acos(cosv))


def signed_trunk_lean_deg(hip_center: Point2D, shoulder_center: Point2D) -> float:
    """
    Lateral trunk lean relative to image vertical.
    Positive: shoulder center is to the right of hip center.
    Image y-axis points downward.
    """
    dx = shoulder_center.x - hip_center.x
    dy_up = hip_center.y - shoulder_center.y
    return math.degrees(math.atan2(dx, dy_up))


def line_tilt_deg(left: Point2D, right: Point2D) -> float:
    """Line tilt relative to image horizontal. Positive when right side is lower."""
    return math.degrees(math.atan2(right.y - left.y, right.x - left.x))


def choose_scale(
    hip_width: float,
    shoulder_width: float,
    torso_length: float,
    mode: str = "hip_width",
    min_scale: float = 0.02,
) -> float:
    candidates = {
        "hip_width": hip_width,
        "shoulder_width": shoulder_width,
        "torso_length": torso_length,
    }
    if mode == "robust":
        valid = sorted(v for v in candidates.values() if math.isfinite(v) and v >= min_scale)
        if not valid:
            return float("nan")
        return valid[len(valid) // 2]

    scale = candidates.get(mode, hip_width)
    if not math.isfinite(scale) or scale < min_scale:
        # Hip width can collapse when the body rotates. Fall back to torso length.
        fallback = torso_length if torso_length >= min_scale else shoulder_width
        return fallback if fallback >= min_scale else float("nan")
    return scale


def normalize_point(point: Point2D, origin: Point2D, scale: float) -> Point2D:
    if not math.isfinite(scale) or scale < EPS:
        return Point2D(float("nan"), float("nan"))
    return Point2D((point.x - origin.x) / scale, (point.y - origin.y) / scale)


def rms(values: Iterable[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    if not vals:
        return float("nan")
    return math.sqrt(sum(v * v for v in vals) / len(vals))
