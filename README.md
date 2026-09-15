# Headwave TV Control

Control Chromecast with Google TV using static hand gestures. A camera detects the
gesture, Raspberry Pi translates it into a command, and ADB sends the command to
the TV.

## Diagram
![Camera frames pass through MediaPipe, filtering, key mapping, and ADB to Google TV.](docs/diagrams/pipeline.svg)

## Hardware

- **Raspberry Pi 5** runs gesture recognition and sends TV commands.
- **Camera Module 3** captures the user's hand and connects directly to the Pi.
- **Chromecast with Google TV** receives commands over the local network through
  Wireless debugging.

## Hand gestures

[Watch the hand gesture demo](docs/media/handGestures.mov)

The built-in MediaPipe model recognizes these gestures. Their TV commands are set
in `config.example.json` and can be changed:

| Gesture label | Hand pose | Example TV command |
|---|---|---|
| `Open_Palm` | Open hand | Play/pause |
| `Closed_Fist` | Closed fist | Select/OK |
| `Thumb_Up` | Thumb up | Volume up |
| `Thumb_Down` | Thumb down | Volume down |
| `Victory` | Two-finger V sign | Back |
| `Pointing_Up` | Index finger pointing up | Navigate up |
| `ILoveYou` | I-love-you hand sign | Home |

Copy the example before changing the gesture assignments:

```bash
cp config.example.json config.local.json
```

The gesture files are:

| File | Purpose |
|---|---|
| `config.example.json` | Example camera settings and gesture-to-command mappings |
| `config.local.json` | Personal settings and final gesture mappings |
| `models/gesture_recognizer.task` | Downloaded MediaPipe model for built-in gestures |
| `data/gestures.jsonl` | Collected landmarks and labels for custom gestures |
| `models/custom.json` | Custom model created by `headwave train` |

The generated model, training data, and local configuration are ignored by Git.

### Camera preview and response time

```bash
headwave run
```

The preview uses black text on a white header. It shows the current gesture,
the last accepted event, processing FPS, and MediaPipe inference time in milliseconds.
Frames are resized to fit the configured width/height before analysis if the camera
ignores the requested capture size. Buffer reduction is best effort and depends on
the camera backend.

The default filter accepts a stable pose after 0.18 seconds and allows at most one
event every 0.25 seconds. You can switch directly to a different stable pose.
Holding the same pose does not repeat it; release for 0.15 seconds to use that same
pose again. Actual response also includes frame capture and model processing time.

If you already use `config.local.json`, update its timing values too:

```json
"hold_seconds": 0.18,
"release_seconds": 0.15,
"cooldown_seconds": 0.25,
"switch_without_release": true
```

Set `switch_without_release` to `false` to require release before every new event.
Increase hold/cooldown times if accidental pose changes trigger commands. Restart
Headwave after changing code or configuration. Dry-run mode does not contact the TV.

## Add and train hand gestures

![Collect gesture samples, train a model, test it, and copy it to Raspberry Pi.](docs/diagrams/training.svg)

### 1. Collect samples

Create samples for every gesture and a `none` class for poses that should do
nothing:

```bash
headwave collect --label PlayPause
headwave collect --label VolumeUp
headwave collect --label none
```

Press Space to save a detected hand and `q` to finish. Record each gesture from
different angles, distances, and lighting conditions. At least 20 samples are
required for each label.

### 2. Train the model

```bash
headwave train
```

The program normalizes the collected hand landmarks and stores them as a simple
k-nearest-neighbors model in `models/custom.json`. No photos or videos are saved.

### 3. Assign TV commands

Add the trained labels to `config.local.json`:

```json
{
  "gestures": {
    "PlayPause": "KEYCODE_MEDIA_PLAY_PAUSE",
    "VolumeUp": "KEYCODE_VOLUME_UP"
  }
}
```

### 4. Test the gestures

```bash
headwave run --config config.local.json --custom-model models/custom.json
```

Commands are printed during testing. When the gestures work reliably, start TV
control on the Pi:

```bash
headwave run --config config.local.json \
  --custom-model models/custom.json --live --headless
```
