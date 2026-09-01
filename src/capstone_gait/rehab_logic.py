\
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RehabConfig:
    side: str = "left"
    target_knee_flexion_deg: float = 50.0
    rep_start_deg: float = 20.0
    rep_end_deg: float = 15.0
    trunk_delta_limit_deg: float = 10.0
    pelvic_tilt_delta_limit_deg: float = 8.0
    shoulder_tilt_delta_limit_deg: float = 8.0


class RehabRepEvaluator:
    """
    Dynamic target: knee flexion.
    Reference/postural landmarks: trunk, pelvis, shoulders.

    A rep is marked:
      ROM PASS/FAIL
      POSTURE PASS/FAIL
    """

    def __init__(self, config: RehabConfig, baseline: Dict[str, float]):
        self.cfg = config
        self.baseline = baseline
        self.active = False
        self.rep_count = 0
        self.peak_flex = 0.0
        self.max_trunk_delta = 0.0
        self.max_pelvic_delta = 0.0
        self.max_shoulder_delta = 0.0
        self.last_result: Optional[Dict] = None

    def _reset_active(self):
        self.peak_flex = 0.0
        self.max_trunk_delta = 0.0
        self.max_pelvic_delta = 0.0
        self.max_shoulder_delta = 0.0

    def update(self, features: Dict[str, float]) -> Optional[Dict]:
        flex_key = f"{self.cfg.side}_knee_flexion_deg"
        flex = float(features[flex_key])
        trunk_d = abs(float(features["trunk_lean_deg"]) - self.baseline["trunk_lean_deg"])
        pelvic_d = abs(float(features["pelvic_tilt_deg"]) - self.baseline["pelvic_tilt_deg"])
        shoulder_d = abs(float(features["shoulder_tilt_deg"]) - self.baseline["shoulder_tilt_deg"])

        if not self.active and flex >= self.cfg.rep_start_deg:
            self.active = True
            self._reset_active()

        if self.active:
            self.peak_flex = max(self.peak_flex, flex)
            self.max_trunk_delta = max(self.max_trunk_delta, trunk_d)
            self.max_pelvic_delta = max(self.max_pelvic_delta, pelvic_d)
            self.max_shoulder_delta = max(self.max_shoulder_delta, shoulder_d)

            if flex <= self.cfg.rep_end_deg:
                self.active = False
                self.rep_count += 1
                rom_ok = self.peak_flex >= self.cfg.target_knee_flexion_deg
                posture_ok = (
                    self.max_trunk_delta <= self.cfg.trunk_delta_limit_deg
                    and self.max_pelvic_delta <= self.cfg.pelvic_tilt_delta_limit_deg
                    and self.max_shoulder_delta <= self.cfg.shoulder_tilt_delta_limit_deg
                )
                self.last_result = {
                    "rep": self.rep_count,
                    "peak_knee_flexion_deg": self.peak_flex,
                    "rom_ok": rom_ok,
                    "posture_ok": posture_ok,
                    "max_trunk_delta_deg": self.max_trunk_delta,
                    "max_pelvic_delta_deg": self.max_pelvic_delta,
                    "max_shoulder_delta_deg": self.max_shoulder_delta,
                    "correct_movement": bool(rom_ok and posture_ok),
                }
                return self.last_result

        return None
