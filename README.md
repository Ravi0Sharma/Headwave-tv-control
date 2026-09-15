# Headwave TV Control

Control Google TV with static hand gestures. Headwave recognizes one hand through
a camera, filters accidental detections, and sends the configured Android keycode
over ADB.

![Camera frames pass through MediaPipe, filtering, key mapping, and ADB to Google TV.](docs/diagrams/pipeline.svg)

## Requirements

- Python 3.9–3.12 (Python 3.11 recommended)
- A camera available through OpenCV
- A Google TV device with Wireless debugging for live control
- ADB on the computer that runs Headwave

Headwave recognizes static poses, not movements such as swipes. Camera input uses
OpenCV; on Raspberry Pi, use a compatible USB camera. Camera Module 3/Picamera2 is
not supported.

## Quick start on macOS

Run the following commands from the project directory:

```bash
brew install python@3.11
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
headwave download-model
headwave run
```

Allow camera access when macOS asks. The default run mode only prints the TV
commands it recognizes; it does not contact a TV. Press `q`, Escape, or Ctrl+C to
stop.

If the wrong camera opens, copy the example configuration and change `camera`:

```bash
cp config.example.json config.local.json
headwave run --config config.local.json
```

## Configure gestures

Edit `config.local.json` to map MediaPipe gesture labels to Android keycodes:

```json
{
  "adb_serial": "192.168.1.50:40877",
  "gestures": {
    "Open_Palm": "KEYCODE_MEDIA_PLAY_PAUSE",
    "Thumb_Up": "KEYCODE_VOLUME_UP",
    "Thumb_Down": "KEYCODE_VOLUME_DOWN",
    "Victory": "KEYCODE_BACK"
  }
}
```

See `config.example.json` for all settings. The most important timing settings are:

| Setting | Purpose |
|---|---|
| `confidence` | Minimum recognition score |
| `hold_seconds` | Time a pose must remain stable before it fires |
| `release_seconds` | Time the pose must disappear before another command can fire |
| `cooldown_seconds` | Minimum time between commands |

## Connect Google TV

The Pi or computer and TV must be on the same local network. On the TV, enable
Developer options, then open **Wireless debugging → Pair using pairing code**.

Pair and connect using the two addresses shown by the TV:

```bash
headwave pair 192.168.1.50:37123
headwave connect 192.168.1.50:40877
headwave devices
```

The pairing port and connection port are different. Put the connection address in
`adb_serial` inside `config.local.json`, then start live control:

```bash
headwave run --config config.local.json --live --headless
```

Remove `--headless` to keep the camera preview visible. Pair using the same system
account that will run Headwave because ADB stores credentials per account.

## Run on Raspberry Pi 5

Use 64-bit Raspberry Pi OS and create a new virtual environment on the Pi:

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev adb libgl1 libglib2.0-0 libportaudio2
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
headwave download-model
cp config.example.json config.local.json
```

Test the camera and printed commands before enabling TV control:

```bash
headwave run --config config.local.json
```

After pairing the TV and setting `adb_serial`, run:

```bash
headwave run --config config.local.json --live --headless
```

For automatic startup, adapt `deploy/headwave.service.example` with the correct
user and absolute project paths, then install it as a systemd service.

## Train custom static poses

Collect landmarks for every pose and for a `none` class that represents poses that
must not trigger an action:

```bash
headwave collect --label MyGesture
headwave collect --label none
```

Press Space to save a detected hand and `q` to finish. Collection stores 21 XYZ
landmarks per sample in `data/gestures.jsonl`; it does not store photos or video.
Use varied angles, distances, lighting, backgrounds, hands, and recording sessions.

Create and test the classifier:

```bash
headwave train
headwave run --config config.local.json --custom-model models/custom.json
```

Add each custom label to the `gestures` mapping before testing. When the results
are satisfactory, copy `models/custom.json` to the Pi and run:

```bash
headwave run --config config.local.json \
  --custom-model models/custom.json --live --headless
```

## Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Troubleshooting

| Problem | Check |
|---|---|
| `headwave` is not found | Activate `.venv` and install the project. |
| Camera does not open | Camera permission, camera index, and other apps using it. |
| Model is missing | Run `headwave download-model`. |
| A pose does not fire again | Remove the hand long enough to satisfy `release_seconds`. |
| Pairing works but connection fails | Use the connection port, not the pairing port. |
| TV stops responding | Check the TV address, run `headwave connect` again, and restart Headwave. |
| Custom poses are rejected | Improve sample variety or adjust `--max-distance`. |

## License

[MIT](LICENSE). Third-party libraries and model files retain their respective
licenses.
