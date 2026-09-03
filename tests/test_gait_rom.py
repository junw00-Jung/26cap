import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from capstone_gait.gait_rom import StreamingGaitRom


def test_streaming_gait_rom_emits_result_after_full_stride():
    evaluator = StreamingGaitRom(
        side="left",
        min_cycle_ms=500,
        max_cycle_ms=2000,
        direction_epsilon=0.01,
        smoothing_window=1,
        min_samples=5,
    )
    result = None
    ankle_pattern = [0.0, 0.2, 0.4, 0.6, 0.4, 0.2, 0.0, 0.2, 0.4, 0.6, 0.4]
    flex_pattern = [5, 10, 20, 40, 55, 35, 10, 8, 25, 50, 30]
    for i, (ankle_x, flexion) in enumerate(zip(ankle_pattern, flex_pattern)):
        candidate = evaluator.update({
            "timestamp_ms": i * 100,
            "left_ankle_nx": ankle_x,
            "left_knee_flexion_deg": flexion,
        })
        if candidate is not None:
            result = candidate

    assert result is not None
    assert result.side == "left"
    assert math.isclose(result.cycle_time_s, 0.6, abs_tol=1e-6)
    assert result.knee_rom_deg > 35
    assert result.sample_count >= 5


def test_invalid_side_is_rejected():
    try:
        StreamingGaitRom(side="middle")
    except ValueError:
        return
    raise AssertionError("Expected invalid side to raise ValueError")
