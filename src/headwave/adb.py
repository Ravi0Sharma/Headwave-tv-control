"""Explicit device selection, bounded calls, and no automatic key retries."""
import re
import subprocess


def endpoint(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*:[0-9]{1,5}", value):
        raise ValueError("Use the TV's IPv4 address or hostname followed by :port")
    if not 1 <= int(value.rsplit(":", 1)[1]) <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    return value


def command(*args, interactive=False):
    try:
        result = subprocess.run(
            ["adb", *args], check=True, text=True,
            capture_output=not interactive, timeout=120 if interactive else 5,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("adb is missing; install Android Platform Tools") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ADB timed out. Check the TV and its connection port.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError((exc.stderr or exc.stdout or "ADB failed").strip()) from exc
    return (result.stdout or "").strip()


class AdbRemote:
    def __init__(self, serial):
        self.serial = endpoint(serial)

    def connect(self):
        output = command("connect", self.serial)
        # adb connect may exit successfully even when the connection failed.
        if command("-s", self.serial, "get-state") != "device":
            raise RuntimeError("TV not ready: " + output)

    def send(self, key):
        if not re.fullmatch(r"KEYCODE_[A-Z0-9_]+", key):
            raise ValueError("Invalid Android keycode")
        command("-s", self.serial, "shell", "input", "keyevent", key)
