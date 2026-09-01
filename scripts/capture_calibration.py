\
from __future__ import annotations

import argparse, csv, json, sys
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from capstone_gait.pose_engine import PoseProcessor
from capstone_gait.sensors import MockSensorSource, SerialSensorSource, monotonic_ms
from capstone_gait.visualization import put_lines

def append_rows(path: Path, rows):
    if not rows: return
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if not exists: writer.writeheader()
        writer.writerows(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--session",default="normal_01"); ap.add_argument("--sensor",choices=["mock","serial"],default=None); ap.add_argument("--port",default=None); ap.add_argument("--duration",type=float,default=30.0)
    args=ap.parse_args(); config=json.loads((ROOT/"config.json").read_text(encoding="utf-8")); sensor_cfg=config["sensor"]; mode=args.sensor or sensor_cfg["mode"]
    session_dir=ROOT/"data"/"raw"/args.session; session_dir.mkdir(parents=True,exist_ok=True); pose_path=session_dir/"pose_raw.csv"; sensor_path=session_dir/"sensor_raw.csv"
    pose=PoseProcessor(model_path=str(ROOT/config["pose_model"]),scale_mode=config["normalization"]["scale_mode"],visibility_threshold=config["normalization"]["visibility_threshold"],min_scale=config["normalization"]["min_scale"])
    sensors=MockSensorSource(sensor_cfg["sample_rate_hz"],sensor_cfg["pressure_channels"]) if mode=="mock" else SerialSensorSource(args.port or sensor_cfg["serial_port"],sensor_cfg["baudrate"],sensor_cfg["pressure_channels"])
    cap=cv2.VideoCapture(config["camera_index"])
    if not cap.isOpened(): raise RuntimeError("Cannot open camera.")
    t0=monotonic_ms(); pose_buffer=[]; sensor_buffer=[]
    try:
        while True:
            ok,frame=cap.read()
            if not ok: break
            t_ms=monotonic_ms(); feat=pose.process(frame,t_ms)
            if feat is not None: pose_buffer.append(feat)
            sensor_buffer.extend(sensors.poll())
            if len(pose_buffer)>=60: append_rows(pose_path,pose_buffer); pose_buffer.clear()
            if len(sensor_buffer)>=200: append_rows(sensor_path,sensor_buffer); sensor_buffer.clear()
            elapsed=(t_ms-t0)/1000.0; lines=[f"CALIBRATION / {mode}",f"time: {elapsed:5.1f}s",f"pose: {'OK' if feat else 'NO POSE'}"]
            if feat: lines += [f"L knee flex: {feat['left_knee_flexion_deg']:.1f} deg",f"R knee flex: {feat['right_knee_flexion_deg']:.1f} deg",f"trunk lean: {feat['trunk_lean_deg']:.1f} deg",f"ankleH/hipW L: {feat['left_ankle_height_over_hip_width']:.2f}"]
            put_lines(frame,lines); cv2.imshow("Capstone Calibration",frame)
            if cv2.waitKey(1)&0xFF==ord("q"): break
            if args.duration>0 and elapsed>=args.duration: break
    finally:
        append_rows(pose_path,pose_buffer); append_rows(sensor_path,sensor_buffer); cap.release(); pose.close(); sensors.close(); cv2.destroyAllWindows()

if __name__=="__main__": main()
