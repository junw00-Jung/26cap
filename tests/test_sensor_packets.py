import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from capstone_gait.sensors import PacketDecoder, packet_to_row
from capstone_gait.synchronization import synchronize_to_sensor_timeline
from capstone_gait.step_features import extract_step_features


def packet():
    return {"pressure": [11, 22, 33, 44], "accel": [0, 0, 9.80665],
            "gyro": [1, 2, 3], "temperature_c": [20, 21, None, 23],
            "humidity_pct": [40, 41, None, 43], "seq": 7,
            "device_ms": 400, "environment_age_ms": 20}


def test_fragmented_and_batched_usb_reads():
    decoder = PacketDecoder(4)
    raw = json.dumps(packet()).encode() + b"\r\n"
    assert decoder.feed(raw[:50]) == []
    rows = decoder.feed(raw[50:] + raw)
    assert len(rows) == 2
    assert rows[0]["pressure_3"] == 44
    assert rows[0]["temperature_c_1"] == 21
    assert math.isnan(rows[0]["humidity_pct_2"])
    assert rows[0]["acc_z"] == 9.80665
    assert rows[0]["timestamp_ms"] != 400
    assert rows[0]["device_ms"] == 400


def test_legacy_packets_keep_stable_schema():
    old = packet_to_row({"pressure": list(range(8))}, 1)
    new = packet_to_row(packet(), 2)
    assert list(old) == list(new)
    assert math.isnan(old["temperature_c_0"])
    assert math.isnan(new["pressure_7"])


@pytest.mark.parametrize("bad", [[], {}, {"pressure": [1]*8},
    {"pressure": [1], "accel": []}, {"pressure": ["bad"]},
    {"pressure": [True]}, {"pressure": [1], "humidity_pct": "bad"}])
def test_malformed_packets_are_rejected(bad):
    with pytest.raises(ValueError):
        packet_to_row(bad, 0, 4)


def test_debug_invalid_and_overlong_lines_recover():
    decoder = PacketDecoder(4)
    raw = json.dumps(packet()).encode()+b"\n"
    rows = decoder.feed(b"# boot\nnot json\n" + b"x"*5000 + b"\n" + raw)
    assert len(rows) == 1
    assert decoder.last_message == "# boot"
    assert decoder.invalid_packets == 2


def test_environment_survives_sync_and_step_summary():
    sensor = pd.DataFrame([packet_to_row(packet(), t, 4) for t in [100, 120, 140]])
    pose = pd.DataFrame({"timestamp_ms": [100, 140], "left_knee_flexion_deg": [10, 30]})
    synced = synchronize_to_sensor_timeline(pose, sensor)
    assert synced["temperature_c_1"].tolist() == [21, 21, 21]
    steps = extract_step_features(synced, [(0, 2)])
    assert steps.iloc[0]["temperature_c_1_mean"] == 21
    assert steps.iloc[0]["humidity_pct_3_mean"] == 43
    assert math.isnan(steps.iloc[0]["temperature_c_2_mean"])


def test_sensor_cli_writes_csv_and_refuses_existing_session(tmp_path, monkeypatch):
    import importlib.util
    script = Path(__file__).resolve().parents[1] / "scripts/capture_sensors.py"
    spec = importlib.util.spec_from_file_location("capture_sensors_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    closed = []
    class FakeSource:
        def __init__(self, *args):
            self.decoder = PacketDecoder(4)
        def poll(self):
            return self.decoder.feed(json.dumps(packet()).encode()+b"\n")
        def close(self):
            closed.append(True)
    (tmp_path / "config.hardware.json").write_text(json.dumps({"sensor": {
        "baudrate": 115200, "pressure_channels": 4, "environment_channels": 4}}))
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "SerialSensorSource", FakeSource)
    monkeypatch.setattr(sys, "argv", ["capture_sensors.py", "--port", "FAKE",
        "--session", "test", "--duration", "0.03"])
    module.main()
    saved = pd.read_csv(tmp_path / "data/raw/test/sensor_raw.csv")
    assert len(saved) > 0
    assert saved["pressure_3"].eq(44).all()
    assert saved["temperature_c_1"].eq(21).all()
    assert saved["temperature_c_2"].isna().all()
    assert closed == [True]
    with pytest.raises(FileExistsError):
        module.main()


def test_background_serial_reader_preserves_split_packets(monkeypatch):
    import queue
    import time
    import serial
    from capstone_gait.sensors import SerialSensorSource
    chunks = queue.Queue()
    raw = json.dumps(packet()).encode()+b"\n"
    chunks.put(raw[:10]); chunks.put(raw[10:])
    class FakeSerial:
        in_waiting = 0
        def read(self, size):
            try:
                return chunks.get(timeout=0.01)
            except queue.Empty:
                return b""
        def close(self):
            self.closed = True
    fake = FakeSerial()
    monkeypatch.setattr(serial, "Serial", lambda *a, **kw: fake)
    source = SerialSensorSource("FAKE", pressure_channels=4)
    try:
        deadline = time.monotonic()+1
        rows = []
        while not rows and time.monotonic()<deadline:
            rows = source.poll()
            time.sleep(0.005)
        assert len(rows) == 1
        assert rows[0]["humidity_pct_0"] == 40
    finally:
        source.close()
    assert fake.closed
