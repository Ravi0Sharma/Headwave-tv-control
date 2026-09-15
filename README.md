# Headwave TV Control

Control Chromecast with Google TV using static hand gestures. A camera detects the
gesture, Raspberry Pi translates it into a command, and ADB sends the command to
the TV.

## Hardware

- **Raspberry Pi 5** runs gesture recognition and sends TV commands.
- **Camera Module 3** captures the user's hand and connects directly to the Pi.
  The current code needs a Picamera2 adapter before this camera can be used.
- **Chromecast with Google TV** receives commands over the local network through
  Wireless debugging.

## Add and train hand gestures

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

## License

[MIT](LICENSE)
