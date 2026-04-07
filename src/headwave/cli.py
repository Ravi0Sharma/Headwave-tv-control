import argparse
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

from .adb import AdbRemote, command, endpoint
from .custom import train

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"


def config(path):
    data = json.loads(Path(path).read_text())
    for name, default in [("confidence", .75), ("hold_seconds", .5),
                          ("release_seconds", .35), ("cooldown_seconds", 1.)]:
        value = data.setdefault(name, default)
        if not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a positive finite number")
    if data["confidence"] > 1:
        raise ValueError("confidence must be <= 1")
    for name, default in [("width", 640), ("height", 480)]:
        value = data.setdefault(name, default)
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    camera = data.setdefault("camera", 0)
    if type(camera) is not int or camera < 0:
        raise ValueError("camera must be a nonnegative index")
    if not isinstance(data.get("gestures"), dict):
        raise ValueError("gestures must map labels to Android keycodes")
    for label, key in data["gestures"].items():
        if not isinstance(key, str) or not re.fullmatch(r"KEYCODE_[A-Z0-9_]+", key):
            raise ValueError(f"Invalid keycode for {label}")
    model = Path(data.get("model", "models/gesture_recognizer.task"))
    data["model"] = str(Path(path).resolve().parent / model)
    return data


def main():
    parser = argparse.ArgumentParser(description="Headwave: Mac gesture lab / Raspberry Pi TV remote")
    sub = parser.add_subparsers(dest="command", required=True)
    download = sub.add_parser("download-model")
    download.add_argument("--output", default="models/gesture_recognizer.task")
    for name in ("run", "collect"):
        p = sub.add_parser(name)
        p.add_argument("--config", default="config.example.json")
        if name == "run":
            p.add_argument("--live", action="store_true", help="Send commands to the paired TV")
            p.add_argument("--headless", action="store_true")
            p.add_argument("--custom-model", help="Use custom landmark classifier instead of canned gestures")
            p.add_argument("--max-distance", type=float, default=.15)
        else:
            p.add_argument("--label", required=True)
            p.add_argument("--output", default="data/gestures.jsonl")
    p = sub.add_parser("train")
    p.add_argument("--data", default="data/gestures.jsonl")
    p.add_argument("--output", default="models/custom.json")
    for name in ("pair", "connect"):
        p = sub.add_parser(name)
        p.add_argument("endpoint", help="TV_IP:PORT (pairing and connection ports differ)")
    sub.add_parser("devices")
    args = parser.parse_args()
    try:
        if args.command == "download-model":
            path = Path(args.output)
            if path.exists():
                raise ValueError(f"Already exists: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(MODEL_URL, timeout=60) as response:
                content = response.read()
            if len(content) < 1_000_000:
                raise ValueError("Downloaded model is unexpectedly small")
            path.write_bytes(content)
            print(path)
        elif args.command == "pair":
            command("pair", endpoint(args.endpoint), interactive=True)
        elif args.command == "connect":
            AdbRemote(args.endpoint).connect()
            print("Connected")
        elif args.command == "devices":
            print(command("devices", "-l"))
        elif args.command == "train":
            print(train(args.data, args.output))
        else:
            if args.command == "run" and (not math.isfinite(args.max_distance) or args.max_distance <= 0):
                raise ValueError("max-distance must be positive and finite")
            from .camera import run
            run(config(args.config), args)
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, RuntimeError, ImportError, KeyError, TypeError) as exc:
        print(f"Headwave: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
