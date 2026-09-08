\
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from capstone_gait.synchronization import synchronize_to_sensor_timeline
from capstone_gait.step_features import detect_heel_strikes, make_step_segments, extract_step_features


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="normal_01")
    ap.add_argument("--label", default="Normal")
    ap.add_argument("--config", default="config.json")
    args = ap.parse_args()

    cfg = json.loads((ROOT / args.config).read_text(encoding="utf-8"))
    raw = ROOT / "data" / "raw" / args.session
    out_dir = ROOT / "data" / "processed" / args.session
    out_dir.mkdir(parents=True, exist_ok=True)

    pose = pd.read_csv(raw / "pose_raw.csv")
    sensor = pd.read_csv(raw / "sensor_raw.csv")

    synced = synchronize_to_sensor_timeline(pose, sensor)
    strikes = detect_heel_strikes(synced, heel_channels=cfg["step_detection"]["heel_channels"], refractory_ms=cfg["step_detection"]["refractory_ms"])
    segments = make_step_segments(synced, strikes, min_step_ms=cfg["step_detection"]["min_step_ms"], max_step_ms=cfg["step_detection"]["max_step_ms"])
    dataset = extract_step_features(synced, segments, label=args.label)

    synced.to_csv(out_dir / "synced_timeseries.csv", index=False)
    dataset.to_csv(out_dir / "dataset_steps.csv", index=False)

    print(f"Pose rows:      {len(pose)}")
    print(f"Sensor rows:    {len(sensor)}")
    print(f"Heel strikes:   {len(strikes)}")
    print(f"Valid steps:    {len(dataset)}")
    print(f"Saved: {out_dir / 'synced_timeseries.csv'}")
    print(f"Saved: {out_dir / 'dataset_steps.csv'}")


if __name__ == "__main__":
    main()
