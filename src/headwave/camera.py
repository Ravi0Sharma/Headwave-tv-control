"""OpenCV capture shared by Mac development and Pi runtime."""
import json
import time
from pathlib import Path

from .adb import AdbRemote
from .custom import CustomClassifier
from .filter import GestureFilter


def resize_frame(frame, width, height):
    """Bound actual image size even when a capture backend ignores set()."""
    import cv2

    scale = min(width / frame.shape[1], height / frame.shape[0], 1.0)
    if scale < 1.0:
        return cv2.resize(frame, (max(1, int(frame.shape[1] * scale)),
                                  max(1, int(frame.shape[0] * scale))),
                          interpolation=cv2.INTER_AREA)
    return frame


def make_preview(frame, points, label, score, last_action, fps, inference_ms, mode):
    """Keep readable black status text outside the camera image."""
    import cv2

    preview = cv2.flip(frame, 1)
    for x, y, _ in points:
        cv2.circle(preview, (preview.shape[1] - 1 - int(x * preview.shape[1]),
                            int(y * preview.shape[0])), 3, (0, 255, 0), -1)
    preview = cv2.copyMakeBorder(preview, 88, 0, 0, 0, cv2.BORDER_CONSTANT,
                                 value=(255, 255, 255))
    lines = [f"{label or '-'}  {score:.2f}  |  {mode}  |  q quits",
             f"Last event: {last_action}",
             f"{fps:.1f} FPS  |  model {inference_ms:.0f} ms"]
    for y, line in zip((23, 49, 75), lines):
        font = cv2.FONT_HERSHEY_SIMPLEX
        size = cv2.getTextSize(line, font, .55, 1)[0][0]
        scale = .55 * min(1.0, max(1, preview.shape[1]-24) / max(1, size))
        cv2.putText(preview, line, (12, y), font, scale, (0, 0, 0), 1, cv2.LINE_AA)
    return preview


def run(config, args):
    import cv2
    import mediapipe as mp

    if not Path(config["model"]).is_file():
        raise ValueError("Model missing. Run headwave download-model first.")
    collecting = args.command == "collect"
    headless = getattr(args, "headless", False)
    custom = CustomClassifier(args.custom_model, args.max_distance) if getattr(args, "custom_model", None) else None
    remote = AdbRemote(config.get("adb_serial", "")) if getattr(args, "live", False) else None
    if remote:
        remote.connect()
    gate = GestureFilter(config["confidence"], config["hold_seconds"],
                         config["release_seconds"], config["cooldown_seconds"],
                         config["switch_without_release"])
    options = mp.tasks.vision.GestureRecognizerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=config["model"], delegate=mp.tasks.BaseOptions.Delegate.CPU),
        running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=1,
    )
    cap = cv2.VideoCapture(config["camera"])
    saved = 0
    last_timestamp = -1
    previous_frame_time = None
    fps = 0.0
    mode = "COLLECT" if collecting else "LIVE" if remote else "DRY RUN"
    last_action = "COLLECT: SPACE saves a sample" if collecting else "LIVE" if remote else "DRY RUN: no TV commands"
    try:
        if not cap.isOpened():
            raise RuntimeError("Cannot open camera. Check camera index and macOS camera permissions.")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config["width"])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config["height"])
        # Best effort: some backends (including macOS variants) ignore this.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        with mp.tasks.vision.GestureRecognizer.create_from_options(options) as recognizer:
            print(last_action, flush=True)
            while True:
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError("Camera stopped delivering frames")
                frame = resize_frame(frame, config["width"], config["height"])
                now = time.monotonic()
                if previous_frame_time is not None:
                    current_fps = 1.0 / max(now - previous_frame_time, 1e-6)
                    fps = current_fps if fps == 0 else .8 * fps + .2 * current_fps
                previous_frame_time = now
                timestamp = max(last_timestamp + 1, int(now * 1000))
                last_timestamp = timestamp
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                inference_start = time.monotonic()
                result = recognizer.recognize_for_video(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
                inference_ms = (time.monotonic() - inference_start) * 1000
                points = [[p.x, p.y, p.z] for p in result.hand_landmarks[0]] if result.hand_landmarks else []
                label, score = None, 0.
                if points and custom:
                    label, score = custom.predict(points)
                elif result.gestures and result.gestures[0]:
                    category = max(result.gestures[0], key=lambda c: c.score)
                    label, score = category.category_name, category.score
                if not collecting:
                    mapped = label if label in config["gestures"] else None
                    event = gate.update(mapped, score, now)
                    if event:
                        key = config["gestures"][event]
                        last_action = f"{event} -> {key}"
                        if remote:
                            try:
                                remote.send(key)
                            except RuntimeError as exc:
                                # A timed-out key may already have executed. Never replay it.
                                last_action = f"ADB failed: {exc}; restart after reconnecting"
                                raise RuntimeError(last_action) from exc
                        print(last_action, flush=True)
                if not headless:
                    preview = make_preview(frame, points, label, score, last_action,
                                           fps, inference_ms, mode)
                    cv2.imshow("Headwave", preview)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27):
                        break
                    if collecting and key == 32 and points:
                        path = Path(args.output)
                        path.parent.mkdir(parents=True, exist_ok=True)
                        with path.open("a") as stream:
                            stream.write(json.dumps({"label": args.label, "landmarks": points}) + "\n")
                        saved += 1
                        last_action = f"Saved {saved} samples of {args.label}; SPACE saves"
                        print(last_action, flush=True)
    finally:
        cap.release()
        if not headless:
            cv2.destroyAllWindows()
