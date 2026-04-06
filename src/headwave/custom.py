"""Small, portable nearest-neighbour classifier for static hand poses.

Training stores normalized landmark examples. No TensorFlow is needed.
Distances are RMS distances in wrist-relative, scale-normalized coordinates.
"""
import json
import math
from collections import Counter
from pathlib import Path


def features(points):
    if len(points) != 21 or any(len(p) != 3 for p in points):
        raise ValueError("Expected 21 XYZ landmarks")
    values = [float(p[i]) - float(points[0][i]) for p in points for i in range(3)]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Landmarks must be finite")
    scale = max(abs(v) for v in values)
    if scale < 1e-8:
        raise ValueError("Degenerate hand landmarks")
    return [v / scale for v in values]


def train(source, destination):
    samples = []
    for line in Path(source).read_text().splitlines():
        row = json.loads(line)
        label = row["label"]
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Every sample needs a label")
        samples.append({"label": label, "features": features(row["landmarks"])})
    counts = Counter(s["label"] for s in samples)
    if "none" not in counts or len(counts) < 2 or min(counts.values()) < 20:
        raise ValueError("Collect at least 20 examples per label, including 'none' and a gesture")
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "samples": samples}))
    return dict(counts)


class CustomClassifier:
    def __init__(self, path, max_distance=0.15):
        model = json.loads(Path(path).read_text())
        if model.get("version") != 1 or len(model.get("samples", [])) < 5:
            raise ValueError("Unsupported or empty custom model")
        self.samples = model["samples"]
        for sample in self.samples:
            values = sample["features"]
            if (not isinstance(sample["label"], str) or len(values) != 63
                    or not all(math.isfinite(v) for v in values)):
                raise ValueError("Invalid custom model sample")
        self.max_distance = max_distance

    def predict(self, points):
        vector = features(points)
        nearest = sorted(
            (math.sqrt(sum((a-b)**2 for a, b in zip(vector, s["features"])) / 63), s["label"])
            for s in self.samples
        )[:5]
        label, count = Counter(label for _, label in nearest).most_common(1)[0]
        if label == "none" or max(d for d, name in nearest if name == label) > self.max_distance:
            return None, 0.0
        return label, count / 5  # vote agreement, not calibrated probability
