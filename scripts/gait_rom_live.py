from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from capstone_gait.gait_rom import StreamingGaitRom
from capstone_gait.pose_engine import PoseProcessor
from capstone_gait.sensors import monotonic_ms
from capstone_gait.visualization import put_lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", choices=["left", "right"], default="left")
    ap.add_argument("--minimum", type=float, default=None, help="Optional minimum acceptable ROM in degrees")
    ap.add_argument("--duration", type=float, default=0.0, help="0 means run until q")
    args = ap.parse_args()

    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    live = cfg["live_gait_rom"]
    pose = PoseProcessor(
        str(ROOT / cfg["pose_model"]),
        live.get("scale_mode", "robust"),
        cfg["normalization"]["visibility_threshold"],
        cfg["normalization"]["min_scale"],
    )
    evaluator = StreamingGaitRom(
        side=args.side,
        min_cycle_ms=live["min_cycle_ms"],
        max_cycle_ms=live["max_cycle_ms"],
        direction_epsilon=live["direction_epsilon"],
        smoothing_window=live["smoothing_window"],
        min_samples=live["min_samples"],
    )
    cap = cv2.VideoCapture(cfg["camera_index"])
    if not cap.isOpened():
        pose.close()
        raise RuntimeError("Cannot open camera.")

    t0 = monotonic_ms()
    last = None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            now = monotonic_ms()
            feature = pose.process(frame, now)
            elapsed = (now - t0) / 1000.0

            if feature is None:
                lines = ["LIVE GAIT ROM", "NO RELIABLE POSE", "Show the full body from the side"]
            else:
                result = evaluator.update(feature)
                if result is not None:
                    last = result
                flexion = feature[f"{args.side}_knee_flexion_deg"]
                running = evaluator.running_rom_deg()
                lines = [
                    f"LIVE GAIT ROM / {args.side.upper()}",
                    f"knee flexion: {flexion:.1f} deg",
                    f"current cycle ROM: {running:.1f} deg" if math.isfinite(running) else "current cycle ROM: collecting",
                    f"body scale: {feature['body_scale']:.3f}",
                ]
                if last is None:
                    lines.append("Walk sideways; waiting for a full stride")
                else:
                    lines += [
                        f"last stride ROM: {last.knee_rom_deg:.1f} deg",
                        f"cycle time: {last.cycle_time_s:.2f} s",
                    ]
                    if args.minimum is not None:
                        lines.append(f"ROM: {'PASS' if last.knee_rom_deg >= args.minimum else 'LOW'}")

            put_lines(frame, lines)
            cv2.imshow("Capstone Live Gait ROM", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            if args.duration > 0 and elapsed >= args.duration:
                break
    finally:
        cap.release()
        pose.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
