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

def numeric(value):
    if value is None:
        return float("nan")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Sensor values must be numbers or null")
    return float(value) if math.isfinite(value) else float("nan")


def packet_to_row(obj, timestamp_ms, pressure_channels=8, environment_channels=4):
    """Stable CSV schema; absent channels are NaN, never fabricated zeros."""
    if not isinstance(obj, dict) or not isinstance(obj.get("pressure"), list):
        raise ValueError("Not a sensor packet")
    row = {"timestamp_ms": timestamp_ms}
    for key, prefix, count in [("pressure", "pressure", pressure_channels),
                               ("temperature_c", "temperature_c", environment_channels),
                               ("humidity_pct", "humidity_pct", environment_channels)]:
        values = obj.get(key, [])
        if not isinstance(values, list) or len(values) > count:
            raise ValueError(f"Unexpected {key} channel count; check config")
        for i in range(count):
            row[f"{prefix}_{i}"] = numeric(values[i]) if i < len(values) else float("nan")
    for key, prefix in [("accel", "acc"), ("gyro", "gyro")]:
        values = obj.get(key, [None]*3)
        if not isinstance(values, list) or len(values) != 3:
            raise ValueError(f"{key} must contain three axes")
        for axis, value in zip("xyz", values):
            row[f"{prefix}_{axis}"] = numeric(value)
    for key in ("seq", "device_ms", "environment_age_ms"):
        row[key] = numeric(obj.get(key))
    return row


class PacketDecoder:
    """Keep incomplete USB reads until newline, with bounded resynchronization."""
    def __init__(self, pressure_channels=8, environment_channels=4):
        self.pressure_channels = pressure_channels
        self.environment_channels = environment_channels
        self.buffer = bytearray()
        self.discarding = False
        self.invalid_packets = 0
        self.last_message = ""

    def feed(self, chunk):
        rows = []
        for byte in chunk:
            if byte == 10:
                if self.discarding:
                    self.discarding = False
                elif self.buffer:
                    try:
                        line = self.buffer.decode("utf-8").strip()
                        if line.startswith("#"):
                            self.last_message = line
                        else:
                            rows.append(packet_to_row(json.loads(line), monotonic_ms(),
                                self.pressure_channels, self.environment_channels))
                    except (ValueError, TypeError, OverflowError):
                        self.invalid_packets += 1
                self.buffer.clear()
            elif not self.discarding:
                self.buffer.append(byte)
                if len(self.buffer) > 4096:
                    self.buffer.clear(); self.discarding = True; self.invalid_packets += 1
        return rows


class SerialSensorSource:
    def __init__(self, port: str, baudrate: int = 115200, pressure_channels: int = 8,
                 environment_channels: int = 4):
        import serial
        import queue
        import threading
        self.serial = serial.Serial(port, baudrate=baudrate, timeout=0.1)
        self.decoder = PacketDecoder(pressure_channels, environment_channels)
        self.rows = queue.Queue(maxsize=10000)
        self.stop = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            while not self.stop.is_set():
                chunk = self.serial.read(min(max(self.serial.in_waiting, 1), 4096))
                for row in self.decoder.feed(chunk):
                    self.rows.put_nowait(row)
        except Exception as exc:
            if not self.stop.is_set():
                self.error = exc

    def poll(self):
        import queue
        if self.error is not None:
            raise RuntimeError(f"Serial reader stopped: {self.error}") from self.error
        rows = []
        while True:
            try:
                rows.append(self.rows.get_nowait())
            except queue.Empty:
                return rows

    def close(self):
        self.stop.set()
        self.thread.join(timeout=1)
        self.serial.close()
