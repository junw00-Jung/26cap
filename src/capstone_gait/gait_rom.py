from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from typing import Deque, Dict, Optional

import numpy as np


@dataclass(frozen=True)
class GaitRomResult:
    side: str
    start_ms: int
    end_ms: int
    cycle_time_s: float
    knee_flexion_min_deg: float
    knee_flexion_max_deg: float
    knee_rom_deg: float
    sample_count: int


class StreamingGaitRom:
    """Estimate one stride ROM from a normalized ankle trajectory.

    A cycle boundary is a local maximum of the selected ankle's hip-centred,
    body-scaled x coordinate. The 5th-to-95th percentile knee-flexion range is
    used instead of raw extrema to reduce single-frame landmark jitter.
    """

    def __init__(
        self,
        side: str = "left",
        min_cycle_ms: int = 600,
        max_cycle_ms: int = 2200,
        direction_epsilon: float = 0.003,
        smoothing_window: int = 5,
        min_samples: int = 8,
    ):
        if side not in {"left", "right"}:
            raise ValueError("side must be 'left' or 'right'")
        if smoothing_window < 1:
            raise ValueError("smoothing_window must be positive")
        self.side = side
        self.min_cycle_ms = int(min_cycle_ms)
        self.max_cycle_ms = int(max_cycle_ms)
        self.direction_epsilon = float(direction_epsilon)
        self.min_samples = int(min_samples)
        self._ankle_x: Deque[float] = deque(maxlen=int(smoothing_window))
        self._last_x: Optional[float] = None
        self._direction = 0
        self._cycle_start_ms: Optional[int] = None
        self._flexion: list[float] = []
        self.last_result: Optional[GaitRomResult] = None

    def update(self, feature: Dict[str, float]) -> Optional[GaitRomResult]:
        timestamp_ms = int(feature["timestamp_ms"])
        ankle_x = float(feature[f"{self.side}_ankle_nx"])
        flexion = float(feature[f"{self.side}_knee_flexion_deg"])
        if not (math.isfinite(ankle_x) and math.isfinite(flexion)):
            return None

        self._ankle_x.append(ankle_x)
        smooth_x = float(np.median(self._ankle_x))
        self._flexion.append(flexion)

        if self._last_x is None:
            self._last_x = smooth_x
            return None

        delta = smooth_x - self._last_x
        new_direction = self._direction
        if delta > self.direction_epsilon:
            new_direction = 1
        elif delta < -self.direction_epsilon:
            new_direction = -1

        result = None
        if self._direction == 1 and new_direction == -1:
            result = self._finish_cycle(timestamp_ms)

        self._direction = new_direction
        self._last_x = smooth_x
        return result

    def _finish_cycle(self, timestamp_ms: int) -> Optional[GaitRomResult]:
        if self._cycle_start_ms is None:
            self._cycle_start_ms = timestamp_ms
            self._flexion.clear()
            return None

        elapsed_ms = timestamp_ms - self._cycle_start_ms
        values = np.asarray(self._flexion, dtype=float)
        self._cycle_start_ms = timestamp_ms
        self._flexion.clear()

        if not (self.min_cycle_ms <= elapsed_ms <= self.max_cycle_ms):
            return None
        values = values[np.isfinite(values)]
        if values.size < self.min_samples:
            return None

        low, high = np.percentile(values, [5, 95])
        self.last_result = GaitRomResult(
            side=self.side,
            start_ms=timestamp_ms - elapsed_ms,
            end_ms=timestamp_ms,
            cycle_time_s=elapsed_ms / 1000.0,
            knee_flexion_min_deg=float(low),
            knee_flexion_max_deg=float(high),
            knee_rom_deg=float(high - low),
            sample_count=int(values.size),
        )
        return self.last_result

    def running_rom_deg(self) -> float:
        values = np.asarray(self._flexion, dtype=float)
        values = values[np.isfinite(values)]
        if values.size < 2:
            return float("nan")
        low, high = np.percentile(values, [5, 95])
        return float(high - low)
