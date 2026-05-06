"""Debounce pose changes while preventing repeats of the same held pose."""

class GestureFilter:
    def __init__(self, confidence=0.75, hold=0.18, release=0.15, cooldown=0.25,
                 switch_without_release=True):
        self.confidence = confidence
        self.hold = hold
        self.release = release
        self.cooldown = cooldown
        self.switch_without_release = switch_without_release
        self.candidate = None
        self.since = 0.0
        self.absent_since = None
        self.latched = False
        self.last_label = None
        self.last_fire = float("-inf")

    def update(self, label, score, now):
        if label in (None, "None", "none") or not score >= self.confidence:
            self.candidate = None
            if self.absent_since is None:
                self.absent_since = now
            if now - self.absent_since >= self.release:
                self.latched = False
            return None
        self.absent_since = None
        if self.latched and (label == self.last_label or not self.switch_without_release):
            # A brief flicker to another class must not retain its hold timer.
            self.candidate = None
            return None
        if label != self.candidate:
            self.candidate, self.since = label, now
        if now - self.since >= self.hold and now - self.last_fire >= self.cooldown:
            self.latched, self.last_fire = True, now
            self.last_label = label
            return label
        return None
