\
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Optional

import cv2
import mediapipe as mp
import numpy as np

from .geometry import (
    Point2D,
    angle_abc_deg,
    choose_scale,
    distance,
    line_tilt_deg,
    midpoint,
    normalize_point,
    signed_trunk_lean_deg,
)


class PoseProcessor:
    """
    MediaPipe Pose Landmarker -> body-centered, body-scaled features.

    Important:
    - MediaPipe's x/y are already normalized by image width/height.
    - We *again* normalize the landmark geometry by a body reference scale
      (hip width by default) so camera distance changes affect features less.
    """

    def __init__(self, model_path: str, scale_mode: str = "hip_width", visibility_threshold: float = 0.5, min_scale: float = 0.02):
        model_path = str(Path(model_path))
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Pose model not found: {model_path}. Run: python scripts/download_model.py")
        self.scale_mode = scale_mode
        self.visibility_threshold = visibility_threshold
        self.min_scale = min_scale
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        self.P = mp.tasks.vision.PoseLandmark
        self.connections = mp.tasks.vision.PoseLandmarksConnections.POSE_LANDMARKS

    def close(self):
        self.landmarker.close()

    def _valid(self, lm) -> bool:
        visibility = 1.0 if lm.visibility is None else float(lm.visibility)
        presence = 1.0 if lm.presence is None else float(lm.presence)
        return visibility >= self.visibility_threshold and presence >= self.visibility_threshold

    @staticmethod
    def _pt(lm) -> Point2D:
        return Point2D(float(lm.x), float(lm.y))

    def process(self, frame_bgr: np.ndarray, timestamp_ms: int) -> Optional[Dict[str, float]]:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self.landmarker.detect_for_video(mp_image, int(timestamp_ms))
        if not result.pose_landmarks:
            return None
        lms = result.pose_landmarks[0]
        idx = lambda name: int(getattr(self.P, name).value)
        needed = ["LEFT_SHOULDER","RIGHT_SHOULDER","LEFT_HIP","RIGHT_HIP","LEFT_KNEE","RIGHT_KNEE","LEFT_ANKLE","RIGHT_ANKLE","LEFT_HEEL","RIGHT_HEEL","LEFT_FOOT_INDEX","RIGHT_FOOT_INDEX"]
        if not all(self._valid(lms[idx(n)]) for n in needed):
            return None
        pts = {n: self._pt(lms[idx(n)]) for n in needed}
        hip_center = midpoint(pts["LEFT_HIP"], pts["RIGHT_HIP"])
        shoulder_center = midpoint(pts["LEFT_SHOULDER"], pts["RIGHT_SHOULDER"])
        hip_width = distance(pts["LEFT_HIP"], pts["RIGHT_HIP"])
        shoulder_width = distance(pts["LEFT_SHOULDER"], pts["RIGHT_SHOULDER"])
        torso_length = distance(hip_center, shoulder_center)
        scale = choose_scale(hip_width, shoulder_width, torso_length, self.scale_mode, self.min_scale)
        if not math.isfinite(scale):
            return None
        left_knee_joint = angle_abc_deg(pts["LEFT_HIP"], pts["LEFT_KNEE"], pts["LEFT_ANKLE"])
        right_knee_joint = angle_abc_deg(pts["RIGHT_HIP"], pts["RIGHT_KNEE"], pts["RIGHT_ANKLE"])
        left_ankle_joint = angle_abc_deg(pts["LEFT_KNEE"], pts["LEFT_ANKLE"], pts["LEFT_FOOT_INDEX"])
        right_ankle_joint = angle_abc_deg(pts["RIGHT_KNEE"], pts["RIGHT_ANKLE"], pts["RIGHT_FOOT_INDEX"])
        left_knee_flex = 180.0 - left_knee_joint
        right_knee_flex = 180.0 - right_knee_joint
        out: Dict[str, float] = {
            "timestamp_ms": int(timestamp_ms), "hip_center_x": hip_center.x, "hip_center_y": hip_center.y,
            "hip_width": hip_width, "shoulder_width": shoulder_width, "torso_length": torso_length, "body_scale": scale,
            "left_knee_joint_deg": left_knee_joint, "right_knee_joint_deg": right_knee_joint,
            "left_knee_flexion_deg": left_knee_flex, "right_knee_flexion_deg": right_knee_flex,
            "left_ankle_joint_deg": left_ankle_joint, "right_ankle_joint_deg": right_ankle_joint,
            "trunk_lean_deg": signed_trunk_lean_deg(hip_center, shoulder_center),
            "pelvic_tilt_deg": line_tilt_deg(pts["LEFT_HIP"], pts["RIGHT_HIP"]),
            "shoulder_tilt_deg": line_tilt_deg(pts["LEFT_SHOULDER"], pts["RIGHT_SHOULDER"]),
            "left_ankle_height_over_hip_width": abs(pts["LEFT_ANKLE"].y - hip_center.y) / max(hip_width, 1e-9),
            "right_ankle_height_over_hip_width": abs(pts["RIGHT_ANKLE"].y - hip_center.y) / max(hip_width, 1e-9),
        }
        for name in needed:
            p = normalize_point(pts[name], hip_center, scale)
            key = name.lower()
            out[f"{key}_nx"] = p.x
            out[f"{key}_ny"] = p.y
        return out
