\
from __future__ import annotations
import json, math, time
from typing import Dict, List
import numpy as np

def monotonic_ms() -> int:
    return time.perf_counter_ns() // 1_000_000

class MockSensorSource:
    def __init__(self, sample_rate_hz: int = 100, pressure_channels: int = 8):
        self.sample_rate_hz = sample_rate_hz; self.pressure_channels = pressure_channels
        self.period_ms = 1000.0 / sample_rate_hz; self.start_ms = monotonic_ms(); self.next_ms = float(self.start_ms)
    def _sample_at(self, t_ms: int) -> Dict[str, float]:
        t = (t_ms - self.start_ms) / 1000.0; cycle = 1.05; phase = (t % cycle) / cycle
        heel = max(0.0, math.exp(-((phase - 0.10) / 0.10) ** 2)); mid = max(0.0, math.exp(-((phase - 0.28) / 0.15) ** 2)); fore = max(0.0, math.exp(-((phase - 0.48) / 0.18) ** 2)); toe = max(0.0, math.exp(-((phase - 0.66) / 0.12) ** 2))
        base=[700*heel,620*heel,300*mid,270*mid,650*fore,590*fore,460*toe,320*toe]
        pressure = np.interp(np.linspace(0,7,self.pressure_channels), np.arange(8), base).tolist() if self.pressure_channels != 8 else base
        omega=2*math.pi/cycle
        row={"timestamp_ms":int(t_ms)}
        for i,v in enumerate(pressure): row[f"pressure_{i}"]=float(v)
        row.update({"acc_x":0.8*math.sin(omega*t),"acc_y":0.35*math.sin(omega*t+1.0),"acc_z":9.81+0.9*math.sin(2*omega*t),"gyro_x":20.0*math.sin(omega*t+0.5),"gyro_y":45.0*math.sin(omega*t),"gyro_z":10.0*math.sin(omega*t+1.2)})
        return row
    def poll(self)->List[Dict[str,float]]:
        now=monotonic_ms(); rows=[]
        while self.next_ms<=now:
            rows.append(self._sample_at(int(self.next_ms))); self.next_ms += self.period_ms
        return rows
    def close(self): pass

class SerialSensorSource:
    def __init__(self, port: str, baudrate: int = 115200, pressure_channels: int = 8):
        import serial
        self.serial=serial.Serial(port,baudrate=baudrate,timeout=0); self.pressure_channels=pressure_channels
    def poll(self)->List[Dict[str,float]]:
        rows=[]
        while self.serial.in_waiting:
            raw=self.serial.readline()
            if not raw: break
            try:
                obj=json.loads(raw.decode("utf-8",errors="ignore").strip()); pressure=obj.get("pressure",[]); accel=obj.get("accel",[float("nan")]*3); gyro=obj.get("gyro",[float("nan")]*3)
                row={"timestamp_ms":monotonic_ms()}
                for i in range(self.pressure_channels): row[f"pressure_{i}"]=float(pressure[i]) if i<len(pressure) else float("nan")
                row.update({"acc_x":float(accel[0]),"acc_y":float(accel[1]),"acc_z":float(accel[2]),"gyro_x":float(gyro[0]),"gyro_y":float(gyro[1]),"gyro_z":float(gyro[2])}); rows.append(row)
            except (ValueError,KeyError,TypeError,json.JSONDecodeError): continue
        return rows
    def close(self): self.serial.close()
