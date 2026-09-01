\
from __future__ import annotations
import math
from typing import List, Sequence, Tuple
import numpy as np
import pandas as pd
from .geometry import rms

def detect_heel_strikes(df: pd.DataFrame, heel_channels: Sequence[int]=(0,1), refractory_ms:int=450)->List[int]:
    cols=[f"pressure_{i}" for i in heel_channels]; missing=[c for c in cols if c not in df.columns]
    if missing: raise KeyError(f"Missing heel pressure columns: {missing}")
    heel=df[cols].sum(axis=1).to_numpy(dtype=float); finite=heel[np.isfinite(heel)]
    if finite.size<10: return []
    q10=float(np.nanpercentile(finite,10)); q90=float(np.nanpercentile(finite,90)); threshold=q10+0.30*max(q90-q10,1.0)
    above=heel>=threshold; rising=np.where(above & np.r_[False,~above[:-1]])[0]; t=df["timestamp_ms"].to_numpy(dtype=float)
    accepted=[]; last_t=-float("inf")
    for idx in rising:
        if t[idx]-last_t>=refractory_ms: accepted.append(int(idx)); last_t=t[idx]
    return accepted

def make_step_segments(df, heel_strike_indices, min_step_ms=400, max_step_ms=2000):
    seg=[]
    for a,b in zip(heel_strike_indices[:-1],heel_strike_indices[1:]):
        dt=float(df.iloc[b]["timestamp_ms"]-df.iloc[a]["timestamp_ms"])
        if min_step_ms<=dt<=max_step_ms: seg.append((a,b))
    return seg

def _safe_stat(series,op):
    x=pd.to_numeric(series,errors="coerce").dropna()
    if x.empty:return float("nan")
    return {"mean":lambda:float(x.mean()),"std":lambda:float(x.std(ddof=0)),"min":lambda:float(x.min()),"max":lambda:float(x.max())}[op]()

def _feature_range(step,col):
    if col not in step:return {}
    lo=_safe_stat(step[col],"min"); hi=_safe_stat(step[col],"max")
    return {f"{col}_min":lo,f"{col}_max":hi,f"{col}_rom":hi-lo if math.isfinite(lo) and math.isfinite(hi) else float("nan"),f"{col}_mean":_safe_stat(step[col],"mean")}

def extract_step_features(synced_df,segments,label="Normal"):
    rows=[]; pose_cols=["left_knee_flexion_deg","right_knee_flexion_deg","left_ankle_joint_deg","right_ankle_joint_deg","trunk_lean_deg","pelvic_tilt_deg","shoulder_tilt_deg","left_ankle_height_over_hip_width","right_ankle_height_over_hip_width"]
    pressure_cols=[c for c in synced_df.columns if c.startswith("pressure_")]; imu_cols=[c for c in ["acc_x","acc_y","acc_z","gyro_x","gyro_y","gyro_z"] if c in synced_df]
    for step_id,(a,b) in enumerate(segments,start=1):
        step=synced_df.iloc[a:b+1].copy()
        if len(step)<3: continue
        start_ms=int(step["timestamp_ms"].iloc[0]); end_ms=int(step["timestamp_ms"].iloc[-1]); feat={"step_id":step_id,"start_ms":start_ms,"end_ms":end_ms,"step_time_s":(end_ms-start_ms)/1000.0,"label":label}
        for col in pose_cols: feat.update(_feature_range(step,col))
        if pressure_cols:
            total=step[pressure_cols].sum(axis=1); feat["total_pressure_mean"]=float(total.mean()); feat["total_pressure_peak"]=float(total.max())
            for col in pressure_cols: feat[f"{col}_mean"]=_safe_stat(step[col],"mean"); feat[f"{col}_peak"]=_safe_stat(step[col],"max")
        for col in imu_cols:
            x=pd.to_numeric(step[col],errors="coerce").dropna().to_numpy(dtype=float); feat[f"{col}_mean"]=float(np.mean(x)) if x.size else float("nan"); feat[f"{col}_std"]=float(np.std(x)) if x.size else float("nan"); feat[f"{col}_rms"]=rms(x); feat[f"{col}_abs_peak"]=float(np.max(np.abs(x))) if x.size else float("nan")
        if all(c in step for c in ["acc_x","acc_y","acc_z"]):
            mag=np.sqrt(step["acc_x"]**2+step["acc_y"]**2+step["acc_z"]**2); feat["acc_mag_mean"]=float(mag.mean()); feat["acc_mag_std"]=float(mag.std(ddof=0)); feat["acc_mag_rms"]=rms(mag.to_numpy())
        if "left_knee_flexion_deg" in step: feat["pose_valid_fraction"]=float(step["left_knee_flexion_deg"].notna().mean())
        rows.append(feat)
    return pd.DataFrame(rows)
