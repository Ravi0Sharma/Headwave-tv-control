"""Time based debounce; a held pose triggers only once until released."""

class GestureFilter:
    def __init__(self, confidence=0.75, hold=0.5, release=0.35, cooldown=1.0):
        self.confidence = confidence
        self.hold = hold
        self.release = release
        self.cooldown = cooldown
        self.candidate = None
        self.since = 0.0
        self.absent_since = None
        self.latched = False
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
        if self.latched:
            return None
        if label != self.candidate:
            self.candidate, self.since = label, now
        if now - self.since >= self.hold and now - self.last_fire >= self.cooldown:
            self.latched, self.last_fire = True, now
            return label
        return None
