\
from __future__ import annotations

import numpy as np
import pandas as pd


def synchronize_to_sensor_timeline(
    pose_df: pd.DataFrame,
    sensor_df: pd.DataFrame,
    max_pose_gap_ms: int = 150,
) -> pd.DataFrame:
    """
    Interpolate numeric pose features onto the denser sensor timeline.

    Sensor timestamps are retained. Pose values are linearly interpolated.
    If the nearest real pose sample is farther than max_pose_gap_ms,
    interpolated pose values are invalidated (NaN).
    """
    if pose_df.empty or sensor_df.empty:
        raise ValueError("pose_df and sensor_df must both contain data.")

    pose = pose_df.sort_values("timestamp_ms").drop_duplicates("timestamp_ms").copy()
    sensor = sensor_df.sort_values("timestamp_ms").drop_duplicates("timestamp_ms").copy()

    t_pose = pose["timestamp_ms"].to_numpy(dtype=float)
    t_sensor = sensor["timestamp_ms"].to_numpy(dtype=float)

    out = sensor.copy()

    numeric_cols = [
        c for c in pose.columns
        if c != "timestamp_ms" and pd.api.types.is_numeric_dtype(pose[c])
    ]
    for col in numeric_cols:
        valid = pose[["timestamp_ms", col]].dropna()
        if len(valid) < 2:
            out[col] = np.nan
            continue
        out[col] = np.interp(
            t_sensor,
            valid["timestamp_ms"].to_numpy(dtype=float),
            valid[col].to_numpy(dtype=float),
            left=np.nan,
            right=np.nan,
        )

    pose_times = t_pose
    idx = np.searchsorted(pose_times, t_sensor)
    left_idx = np.clip(idx - 1, 0, len(pose_times) - 1)
    right_idx = np.clip(idx, 0, len(pose_times) - 1)
    nearest_gap = np.minimum(
        np.abs(t_sensor - pose_times[left_idx]),
        np.abs(t_sensor - pose_times[right_idx]),
    )
    out["pose_time_gap_ms"] = nearest_gap

    bad = out["pose_time_gap_ms"] > max_pose_gap_ms
    out.loc[bad, numeric_cols] = np.nan
    return out
