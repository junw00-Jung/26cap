\
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from capstone_gait.rehab_logic import RehabConfig, RehabRepEvaluator


def frame(flex, trunk=0, pelvis=0, shoulder=0):
    return {
        "left_knee_flexion_deg": flex,
        "trunk_lean_deg": trunk,
        "pelvic_tilt_deg": pelvis,
        "shoulder_tilt_deg": shoulder,
    }


def test_good_rep():
    cfg = RehabConfig(target_knee_flexion_deg=50)
    ev = RehabRepEvaluator(cfg, {"trunk_lean_deg": 0, "pelvic_tilt_deg": 0, "shoulder_tilt_deg": 0})
    for flex in [5, 25, 40, 55, 35]:
        assert ev.update(frame(flex)) is None
    result = ev.update(frame(10))
    assert result["rom_ok"] is True
    assert result["posture_ok"] is True
    assert result["correct_movement"] is True


def test_compensated_rep_fails_posture():
    cfg = RehabConfig(target_knee_flexion_deg=50, trunk_delta_limit_deg=10)
    ev = RehabRepEvaluator(cfg, {"trunk_lean_deg": 0, "pelvic_tilt_deg": 0, "shoulder_tilt_deg": 0})
    for flex, trunk in [(5,0), (25,3), (45,8), (55,16), (30,12)]:
        ev.update(frame(flex, trunk=trunk))
    result = ev.update(frame(10, trunk=2))
    assert result["rom_ok"] is True
    assert result["posture_ok"] is False
    assert result["correct_movement"] is False
