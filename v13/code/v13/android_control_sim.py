"""Finite Android-shaped world for V13 action-learning tests, NEVER Android I/O.

A dry-run broker envelope is replayed against a fake Notes app with committed
SQLite snapshots and unique action IDs. This is a deterministic acceptance
environment for JEF/world-control wiring, not an AccessibilityService or proof
that the model can operate the device. The broker's current local-UI boolean
is NOT an authenticated user-approval boundary; do not route model calls here.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading

from .android_control import _canonical, ControlDenied

REVISION = "v13-android-simulation-v1"
DEMO_PACKAGE = "org.v13.demo.notes"
MAX_ACTIONS = 10000
MAX_NOTES = 64
ACTION_ID = re.compile(r"[0-9a-f]{32}\Z")


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _sha(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _blank():
    return {
        "revision": REVISION, "app": "HOME", "screen": "HOME",
        "focus": "NONE", "draft": "", "notes": [], "scroll": 0,
    }


def _validate(state):
    if (type(state) is not dict or set(state) != set(_blank())
            or state.get("revision") != REVISION
            or state.get("app") not in ("HOME", DEMO_PACKAGE)
            or state.get("screen") not in ("HOME", "NOTES", "EDITOR")
            or state.get("focus") not in ("NONE", "EDITOR")
            or type(state.get("draft")) is not str or len(state["draft"]) > 256
            or type(state.get("scroll")) is not int
            or not 0 <= state["scroll"] <= 100
            or type(state.get("notes")) is not list
            or len(state["notes"]) > MAX_NOTES
            or any(type(n) is not str or len(n) > 256 for n in state["notes"])):
        raise ValueError("corrupt simulated Android snapshot")
    if state["app"] == "HOME" and (state["screen"] != "HOME"
                                 or state["focus"] != "NONE"):
        raise ValueError("inconsistent simulated Home state")
    if state["app"] != "HOME" and state["screen"] not in ("NOTES", "EDITOR"):
        raise ValueError("inconsistent simulated app state")
    if (state["focus"] == "EDITOR") != (state["screen"] == "EDITOR"):
        raise ValueError("inconsistent simulated input focus")
    return state


def _transition(before, cap, args):
    state = dict(before)
    state["notes"] = list(before["notes"])
    if cap == "observe_ui":
        pass
    elif cap == "launch_app":
        if args["package"] != DEMO_PACKAGE:
            raise ControlDenied("demo app only; Android OS never invoked")
        state.update(app=DEMO_PACKAGE, screen="NOTES", focus="NONE",
                     draft="", scroll=0)
    elif cap == "tap":
        x, y = args["x"], args["y"]
        if state["screen"] == "NOTES" and 100 <= x <= 300 and 100 <= y <= 200:
            state.update(screen="EDITOR", focus="EDITOR", draft="")
        elif state["screen"] == "EDITOR" and 100 <= x <= 300 and 300 <= y <= 400:
            if not state["draft"]:
                raise ControlDenied("empty simulated note")
            if len(state["notes"]) >= MAX_NOTES:
                raise ControlDenied("simulated notes full")
            state["notes"].append(state["draft"])
            state.update(screen="NOTES", focus="NONE", draft="")
        else:
            raise ControlDenied("no enabled simulated UI target at coordinates")
    elif cap == "type_text":
        if state["screen"] != "EDITOR":
            raise ControlDenied("simulated text field is not focused")
        if len(state["draft"] + args["text"]) > 256:
            raise ControlDenied("simulated editor 256-char cap")
        state["draft"] += args["text"]
    elif cap == "back":
        if state["screen"] == "EDITOR":
            state.update(screen="NOTES", focus="NONE", draft="")
        elif state["screen"] == "NOTES":
            state.update(app="HOME", screen="HOME", focus="NONE", draft="")
    elif cap == "swipe":
        if state["screen"] != "NOTES":
            raise ControlDenied("simulated swipe only supported in notes list")
        state["scroll"] = min(100, state["scroll"] + 1)
    else:
        raise ControlDenied("unsupported simulation action")
    return _validate(state)


class SimulatedAndroidWorld:
    """Tiny finite task environment with persistent idempotent dry-run actions."""

    def __init__(self, home):
        self.home = Path(home)
        if self.home.is_symlink():
            raise ValueError("simulation home may not be symlink")
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root = self.home / "android_control_sim"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise ValueError("simulation directory may not be symlink")
        self.path = self.root / "state.sqlite"
        if self.path.is_symlink():
            raise ValueError("simulation DB may not be symlink")
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        os.chmod(self.path, 0o600)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS snapshot (id INTEGER PRIMARY KEY CHECK(id=1), "
            "payload TEXT NOT NULL, sha256 TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS actions (action_id TEXT PRIMARY KEY, "
            "digest TEXT NOT NULL, before_sha256 TEXT NOT NULL, "
            "after_sha256 TEXT NOT NULL)"
        )
        if self.db.execute("SELECT 1 FROM snapshot WHERE id=1").fetchone() is None:
            state = _blank()
            self.db.execute("INSERT INTO snapshot VALUES (1,?,?)",
                            (_json(state), _sha(state)))
        self.db.commit()
        self._load()

    def _load(self):
        row = self.db.execute(
            "SELECT payload,sha256 FROM snapshot WHERE id=1"
        ).fetchone()
        if row is None:
            raise ValueError("missing simulator snapshot")
        state = _validate(json.loads(row[0]))
        if _sha(state) != row[1]:
            raise ValueError("simulator snapshot digest mismatch")
        return state

    def view(self):
        """User-facing synthetic screen, never an OS screenshot."""
        with self.lock:
            state = self._load()
            return {
                "kind": "SIMULATED_UI_ONLY",
                "screen": state["screen"], "app": state["app"],
                "notes": list(state["notes"]), "draft": state["draft"],
                "scroll": state["scroll"],
                "targets": (
                    ["launch_app"] if state["screen"] == "HOME"
                    else ["new_note", "swipe", "back"] if state["screen"] == "NOTES"
                    else ["type_text", "save", "back"]
                ),
                "state_sha256": _sha(state), "native_android_control": False,
            }

    def apply(self, envelope):
        """Consume only a structurally sound dry-run envelope once.

        Caller is a *trusted simulator harness*. A forged Python object can
        imitate this envelope because no authenticated Android companion
        exists; no real device action is available in this module.
        """
        if type(envelope) is not dict or set(envelope) != {
            "action_id", "capability", "args", "digest", "status"
        }:
            raise ControlDenied("invalid synthetic dry-run envelope")
        if envelope.get("status") != "DRY_RUN_ONLY":
            raise ControlDenied("live device action cannot enter simulator")
        aid, digest = envelope["action_id"], envelope["digest"]
        if (type(aid) is not str or not ACTION_ID.fullmatch(aid)
                or type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise ControlDenied("invalid dry-run identity")
        if type(envelope["capability"]) is not str or type(envelope["args"]) is not dict:
            raise ControlDenied("invalid simulated action schema")
        canonical = _canonical(envelope["capability"], envelope["args"])
        if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != digest:
            raise ControlDenied("dry-run action digest mismatch")
        with self.lock, self.db:
            # BEGIN IMMEDIATE protects the read+compute+publish cycle across
            # *separate processes*, not merely threads of this object.
            self.db.execute("BEGIN IMMEDIATE")
            current = self._load()
            before = _sha(current)
            after = _transition(current, envelope["capability"], envelope["args"])
            after_sha = _sha(after)
            count = self.db.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
            if count >= MAX_ACTIONS:
                raise ControlDenied("simulation action ledger full")
            if self.db.execute("SELECT 1 FROM actions WHERE action_id=?", (aid,)).fetchone():
                raise ControlDenied("replayed simulated action id")
            self.db.execute(
                "INSERT INTO actions VALUES (?,?,?,?)",
                (aid, digest, before, after_sha)
            )
            self.db.execute(
                "UPDATE snapshot SET payload=?,sha256=? WHERE id=1",
                (_json(after), after_sha)
            )
            return {
                "kind": "SIMULATED_ACTION_RECEIPT",
                "action_id": aid, "capability": envelope["capability"],
                "before_sha256": before, "after_sha256": after_sha,
                "simulation_applied": True, "native_android_executed": False,
                "model_calls": 0,
            }

    def receipt_count(self):
        with self.lock:
            return int(self.db.execute("SELECT COUNT(*) FROM actions").fetchone()[0])

    def close(self):
        with self.lock:
            self.db.close()
