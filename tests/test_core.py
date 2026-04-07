import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from headwave.adb import AdbRemote, command, endpoint
from headwave.cli import config, main
from headwave.custom import CustomClassifier, features, train
from headwave.filter import GestureFilter


class FilterTests(unittest.TestCase):
    def test_hold_and_release(self):
        gate = GestureFilter()
        self.assertIsNone(gate.update("Open_Palm", .9, 0))
        self.assertIsNone(gate.update("Open_Palm", .9, .49))
        self.assertEqual(gate.update("Open_Palm", .9, .51), "Open_Palm")
        self.assertIsNone(gate.update("Open_Palm", .9, 10))
        self.assertIsNone(gate.update("Victory", .9, 11))
        gate.update(None, 0, 12)
        gate.update(None, 0, 12.36)
        gate.update("Victory", .9, 13)
        self.assertEqual(gate.update("Victory", .9, 13.51), "Victory")

    def test_noise_breaks_hold_but_short_dropout_does_not_rearm(self):
        gate = GestureFilter()
        gate.update("Victory", .9, 0)
        gate.update("Victory", .4, .4)
        self.assertIsNone(gate.update("Victory", .9, .6))
        self.assertEqual(gate.update("Victory", .9, 1.11), "Victory")
        gate.update(None, 0, 2)
        self.assertIsNone(gate.update("Victory", .9, 2.1))
        self.assertIsNone(gate.update("Victory", .9, 3))

    def test_cooldown(self):
        gate = GestureFilter(hold=.1, release=.1, cooldown=2)
        gate.update("Victory", .9, 0)
        self.assertEqual(gate.update("Victory", .9, .11), "Victory")
        gate.update(None, 0, .2)
        gate.update(None, 0, .31)
        gate.update("Victory", .9, .4)
        self.assertIsNone(gate.update("Victory", .9, .6))
        self.assertEqual(gate.update("Victory", .9, 2.12), "Victory")

    def test_nan_does_not_trigger(self):
        gate = GestureFilter()
        gate.update("Victory", float("nan"), 0)
        self.assertIsNone(gate.update("Victory", float("nan"), 10))


class AdbTests(unittest.TestCase):
    @patch("headwave.adb.subprocess.run")
    def test_selected_device(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        AdbRemote("192.168.1.5:40000").send("KEYCODE_BACK")
        self.assertEqual(run.call_args.args[0], ["adb", "-s", "192.168.1.5:40000", "shell", "input", "keyevent", "KEYCODE_BACK"])

    def test_rejects_shell_metacharacters(self):
        with self.assertRaises(ValueError):
            endpoint("192.168.1.5:5555;reboot")
        with self.assertRaises(ValueError):
            AdbRemote("tv.local:5555").send("KEYCODE_BACK;reboot")

    @patch("headwave.adb.subprocess.run", side_effect=subprocess.TimeoutExpired("adb", 5))
    def test_timeout_not_retried(self, run):
        with self.assertRaises(RuntimeError):
            command("devices")
        self.assertEqual(run.call_count, 1)

    @patch("headwave.adb.command", side_effect=["failed to connect", "offline"])
    def test_connect_checks_state(self, _):
        with self.assertRaises(RuntimeError):
            AdbRemote("tv.local:5555").connect()


class CustomTests(unittest.TestCase):
    def test_normalization(self):
        points = [[i, i * .5, i * .1] for i in range(21)]
        moved = [[v * 2 + 7 for v in point] for point in points]
        for a, b in zip(features(points), features(moved)):
            self.assertAlmostEqual(a, b)

    def test_train_predict_and_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, model = Path(tmp) / "data.jsonl", Path(tmp) / "model.json"
            poses = {"Left": [[i, 0, 0] for i in range(21)], "none": [[0, i, 0] for i in range(21)]}
            source.write_text("\n".join(json.dumps({"label": label, "landmarks": points})
                                        for label, points in poses.items() for _ in range(20)))
            self.assertEqual(train(source, model), {"Left": 20, "none": 20})
            classifier = CustomClassifier(model)
            self.assertEqual(classifier.predict(poses["Left"]), ("Left", 1.0))
            self.assertEqual(classifier.predict(poses["none"]), (None, 0.0))
            self.assertEqual(classifier.predict([[0, 0, i] for i in range(21)]), (None, 0.0))

    def test_requires_negative_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "empty.jsonl"
            source.write_text("")
            with self.assertRaises(ValueError):
                train(source, Path(tmp) / "out.json")


class CliTests(unittest.TestCase):
    @patch("headwave.camera.run")
    def test_default_run_is_dry(self, run):
        with patch("sys.argv", ["headwave", "run"]):
            self.assertEqual(main(), 0)
        self.assertFalse(run.call_args.args[1].live)

    def test_model_path(self):
        self.assertEqual(config("config.example.json")["model"], str(Path("models/gesture_recognizer.task").resolve()))


if __name__ == "__main__":
    unittest.main()
