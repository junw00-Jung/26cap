\
from __future__ import annotations
import argparse,json,statistics,sys
from pathlib import Path
import cv2
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from capstone_gait.pose_engine import PoseProcessor
from capstone_gait.rehab_logic import RehabConfig,RehabRepEvaluator
from capstone_gait.sensors import monotonic_ms
from capstone_gait.visualization import put_lines

def median_baseline(samples):
    keys=["trunk_lean_deg","pelvic_tilt_deg","shoulder_tilt_deg"]; return {k:statistics.median(float(x[k]) for x in samples) for k in keys}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--side",choices=["left","right"],default=None); ap.add_argument("--target",type=float,default=None); args=ap.parse_args()
    cfg=json.loads((ROOT/"config.json").read_text(encoding="utf-8")); r=cfg["rehab"]; rcfg=RehabConfig(side=args.side or r["side"],target_knee_flexion_deg=args.target or r["target_knee_flexion_deg"],rep_start_deg=r["rep_start_deg"],rep_end_deg=r["rep_end_deg"],trunk_delta_limit_deg=r["trunk_delta_limit_deg"],pelvic_tilt_delta_limit_deg=r["pelvic_tilt_delta_limit_deg"],shoulder_tilt_delta_limit_deg=r["shoulder_tilt_delta_limit_deg"])
    pose=PoseProcessor(str(ROOT/cfg["pose_model"]),cfg["normalization"]["scale_mode"],cfg["normalization"]["visibility_threshold"],cfg["normalization"]["min_scale"]); cap=cv2.VideoCapture(cfg["camera_index"])
    if not cap.isOpened(): raise RuntimeError("Cannot open camera.")
    samples=[]; evaluator=None; t0=monotonic_ms(); baseline_ms=int(r["baseline_seconds"]*1000)
    try:
        while True:
            ok,frame=cap.read()
            if not ok: break
            t_ms=monotonic_ms(); feat=pose.process(frame,t_ms)
            if feat is not None and evaluator is None:
                samples.append(feat)
                if t_ms-t0>=baseline_ms and len(samples)>=10: evaluator=RehabRepEvaluator(rcfg,median_baseline(samples))
            if evaluator is None: lines=["REHAB BASELINE",f"pose: {'OK' if feat else 'NO POSE'}"]
            elif feat is None: lines=["REHAB","NO POSE"]
            else:
                evaluator.update(feat); flex=feat[f"{rcfg.side}_knee_flexion_deg"]; lines=[f"REHAB / {rcfg.side.upper()} KNEE",f"current flexion: {flex:.1f} / target {rcfg.target_knee_flexion_deg:.1f}"]
                if evaluator.last_result:
                    rr=evaluator.last_result; lines += [f"ROM: {'PASS' if rr['rom_ok'] else 'FAIL'}",f"POSTURE: {'PASS' if rr['posture_ok'] else 'FAIL'}",f"FINAL: {'CORRECT' if rr['correct_movement'] else 'INCORRECT'}"]
            put_lines(frame,lines); cv2.imshow("Capstone Rehab Evaluation",frame)
            if cv2.waitKey(1)&0xFF==ord("q"): break
    finally: cap.release(); pose.close(); cv2.destroyAllWindows()
if __name__=="__main__": main()
