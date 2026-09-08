"""Read ESP USB JSON to CSV without loading a camera or MediaPipe."""
import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from capstone_gait.sensors import SerialSensorSource


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port")
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--session", default=datetime.now().strftime("sensor_%Y%m%d_%H%M%S"))
    parser.add_argument("--config", default="config.hardware.json")
    args = parser.parse_args()
    if args.list_ports:
        from serial.tools import list_ports
        ports = list(list_ports.comports())
        for port in ports:
            print(f"{port.device}: {port.description}")
        if not ports:
            print("No serial ports. Connect the ESP with a USB data cable.")
        return
    if not args.port:
        parser.error("Use --list-ports, then --port COMx")
    if Path(args.session).name != args.session or args.session in (".", ".."):
        parser.error("--session must be a folder name")
    cfg = json.loads((ROOT / args.config).read_text(encoding="utf-8"))["sensor"]
    directory = ROOT / "data" / "raw" / args.session
    directory.mkdir(parents=True, exist_ok=False)
    source = SerialSensorSource(args.port, cfg["baudrate"], cfg["pressure_channels"],
                                cfg.get("environment_channels", 4))
    path = directory / "sensor_raw.csv"
    count = 0
    started = last_data = last_print = time.monotonic()
    writer = None
    latest = None
    try:
        with path.open("x", newline="", encoding="utf-8") as stream:
            while args.duration <= 0 or time.monotonic()-started < args.duration:
                rows = source.poll()
                if rows:
                    if writer is None:
                        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                        writer.writeheader()
                    writer.writerows(rows)
                    count += len(rows)
                    latest = rows[-1]
                    last_data = time.monotonic()
                now = time.monotonic()
                if now-last_print >= 1:
                    stream.flush()
                    print(f"rows={count}, invalid={source.decoder.invalid_packets}")
                    if latest:
                        print(json.dumps(latest, ensure_ascii=False))
                    elif source.decoder.last_message:
                        print(source.decoder.last_message)
                    last_print = now
                if now-last_data > 10:
                    raise RuntimeError("No valid packets for 10 seconds. Check port, firmware and USB monitor.")
                time.sleep(0.005)
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        source.close()
        print(f"Saved {count} rows: {path}")
    if count == 0:
        raise RuntimeError("No sensor data captured.")


if __name__ == "__main__":
    main()
