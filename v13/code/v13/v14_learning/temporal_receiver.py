"""Cross-process safe scalar readout; not a JEPA encoder or native body weights."""
import fcntl
import json
import math
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


class TemporalReadout:
    def __init__(self, path, learning_enabled=False, rate=.1, decay=.95):
        if type(learning_enabled) is not bool:
            raise ValueError("learning_enabled")
        if type(rate) not in (int, float) or not math.isfinite(rate) or not 0 < rate <= .5:
            raise ValueError("rate")
        if type(decay) not in (int, float) or not math.isfinite(decay) or not 0 <= decay < 1:
            raise ValueError("decay")
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.learning_enabled = learning_enabled
        self.rate = rate
        self.decay = decay
        self.weights = {k: 0. for k in ("WORLD", "B1", "B2")}
        self.ema = dict(self.weights)
        self.seen = []
        self._refresh()

    @contextmanager
    def _locked(self, exclusive):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _validate(data):
        if data.get("schema") != 1 or set(data["weights"]) != {"WORLD", "B1", "B2"} or set(data["ema"]) != {"WORLD", "B1", "B2"}:
            raise ValueError("schema")
        values = list(data["weights"].values()) + list(data["ema"].values())
        if not all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 4 for v in values):
            raise ValueError("weights")
        seen = data.get("seen")
        if (not isinstance(seen, list) or len(seen) > 100000
                or not all(type(v) is str and v and len(v) <= 128 for v in seen)
                or len(set(seen)) != len(seen)):
            raise ValueError("seen")
        return data

    def _load_unlocked(self):
        if not self.path.exists():
            self.weights = {k: 0. for k in ("WORLD", "B1", "B2")}
            self.ema = dict(self.weights)
            self.seen = []
            return
        data = self._validate(json.loads(self.path.read_text()))
        self.weights = dict(data["weights"])
        self.ema = dict(data["ema"])
        self.seen = list(data["seen"])

    def _refresh(self):
        with self._locked(False):
            self._load_unlocked()

    def _save_unlocked(self):
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".temporal-")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"schema": 1, "weights": self.weights, "ema": self.ema, "seen": self.seen}, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
            dfd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def save(self):
        with self._locked(True):
            self._load_unlocked()
            self._save_unlocked()

    def read(self, role, target=False):
        if role not in ("WORLD", "B1", "B2") or type(target) is not bool:
            raise ValueError("read selector")
        with self._locked(False):
            self._load_unlocked()
            return 1 / (1 + math.exp(-((self.ema if target else self.weights)[role])))

    def has_seen(self, event_id):
        with self._locked(False):
            self._load_unlocked()
            return event_id in self.seen

    def update(self, intent, event_id, authorized=False):
        if not self.learning_enabled or authorized is not True:
            raise PermissionError("learning gate")
        if type(event_id) is not str or not event_id or len(event_id) > 128:
            raise ValueError("event id")
        if not isinstance(intent, dict) or intent.get("target") != "WORLD_TEMPORAL" or intent.get("requires_optimizer_permission") is not True:
            raise ValueError("intent")
        if not all(type(intent.get(k)) is str and intent[k].startswith("T8:") and len(intent[k]) > 3 for k in ("source", "evidence")):
            raise ValueError("provenance")
        if type(intent.get("expected_outcome")) is not str or not intent["expected_outcome"]:
            raise ValueError("expected outcome")
        observed = intent.get("observed_outcome")
        if observed is not None and (type(observed) is not str or not observed):
            raise ValueError("observed outcome")
        err = intent.get("prediction_error")
        if type(err) not in (int, float) or not math.isfinite(err) or abs(err) > 1:
            raise ValueError("error")
        with self._locked(True):
            self._load_unlocked()
            if event_id in self.seen:
                raise ValueError("event id already processed")
            if len(self.seen) >= 100000:
                raise OverflowError("event budget")
            before = (dict(self.weights), dict(self.ema), list(self.seen))
            for role, scale in (("WORLD", 1.), ("B1", .6), ("B2", .3)):
                self.weights[role] = max(-4., min(4., self.weights[role] + self.rate * err * scale))
                self.ema[role] = self.decay * self.ema[role] + (1 - self.decay) * self.weights[role]
            self.seen.append(event_id)
            try:
                self._save_unlocked()
            except Exception:
                self.weights, self.ema, self.seen = before
                raise
            return {k: self.weights[k] - before[0][k] for k in self.weights}

    def rollback(self, snapshot):
        if type(snapshot) is not bytes:
            raise TypeError("snapshot")
        data = self._validate(json.loads(snapshot.decode("utf-8")))
        with self._locked(True):
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".rollback-")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(snapshot)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.path)
                dfd = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
                self.weights = dict(data["weights"])
                self.ema = dict(data["ema"])
                self.seen = list(data["seen"])
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
