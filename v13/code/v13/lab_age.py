"""Independent user-operated laboratory age, never the earned V13 Age.

User 2026-11-13: explore higher hypothetical age while the verified age stays
at zero. Lab age changes only *local, reversible inference effort headroom*,
not build ceiling, earned developmental evidence, permissions, hard rules,
tool authority, autonomous actions, learning_mode or model weights.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from .common import atomic_write, dumps

SCHEMA = "v13.lab-age/1"
NAME = "lab-age.json"
MODES = ("off", "shadow", "active")
MAX_STAGE = 10
# Preview the highest requested level, but make *compute activation* an explicit
# local action. This preserves the measured Age-0 baseline across software
# updates; no surprise CPU/thermal change simply because GitHub updated code.
# The owner's explicit existing instruction is to try the highest laboratory
# compute level while keeping real Age 0. Missing files therefore do NOT mean
# an unchosen Age 0 or an inactive test. Unsafe/corrupt files still fail off.
DEFAULT = {"schema": SCHEMA, "mode": "active", "stage": 10}


def _path(home):
    return Path(home) / "config" / NAME


def _valid(raw):
    return (type(raw) is dict and set(raw) == {"schema", "mode", "stage"}
            and raw["schema"] == SCHEMA and raw["mode"] in MODES
            and type(raw["stage"]) is int and 0 <= raw["stage"] <= MAX_STAGE)


def read(home):
    """Invalid or unsafe configuration fails closed; never promotes actual Age."""
    path = _path(home)
    try:
        if path.is_symlink():
            raise ValueError("Unsafe lab-age config")
        if not path.exists():
            return dict(DEFAULT)
        st = path.stat()
        if (not path.is_file() or st.st_uid != os.getuid()
                or st.st_mode & 0o077 or st.st_size > 2048):
            raise ValueError("Unsafe lab-age config")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not _valid(value):
            raise ValueError("Invalid lab-age config")
        return value
    except (OSError, ValueError, UnicodeError):
        return {"schema": SCHEMA, "mode": "off", "stage": 0}


def save(home, *, mode=None, stage=None):
    """Local UI/CLI control. Cannot change official Age or any permission."""
    # The WebView control panel can start before the AI runtime has created
    # config/settings.json. A valid owner click must not be rejected merely
    # because the laboratory config directory does not exist yet.
    root = Path(home)
    if root.is_symlink():
        raise ValueError("Unsafe V13 home")
    if not root.exists():
        root.mkdir(mode=0o700, parents=True)
    if (not root.is_dir() or root.stat().st_uid != os.getuid()
            or root.stat().st_mode & 0o077):
        raise ValueError("Unsafe V13 home")
    config = _path(home)
    parent = config.parent
    if parent.is_symlink():
        raise ValueError("Unsafe V13 configuration directory")
    if not parent.exists():
        parent.mkdir(mode=0o700)
    if (not parent.is_dir() or parent.stat().st_uid != os.getuid()
            or parent.stat().st_mode & 0o077 or config.is_symlink()):
        raise ValueError("Unsafe V13 configuration directory")
    current = read(home)
    if mode is not None:
        if type(mode) is not str or mode not in MODES:
            raise ValueError("Lab mode must be off|shadow|active")
        current["mode"] = mode
    if stage is not None:
        if type(stage) is not int or not 0 <= stage <= MAX_STAGE:
            raise ValueError("Lab age must be 0..10")
        current["stage"] = stage
    if not _valid(current):
        raise ValueError("Invalid laboratory age")
    atomic_write(config, dumps(current))
    os.chmod(config, 0o600)
    return current


def simulated_effort(control, baseline, *, resource_mode):
    """Return shadow/active experimental compute plan, with real Age untouched.

    This adjusts the existing *thinking budget* only. The control passed in
    is still the real AgeControl, and may() decisions never consult this plan.
    The actual resource guard, max_reentry, observer deadlines, user stops and
    hard permission checks continue to bind downstream.
    """
    settings = read(control.s.home)
    out = dict(baseline)
    out["lab_mode"] = settings["mode"]
    out["lab_stage"] = settings["stage"]
    out["official_stage"] = baseline["stage"]
    requested = settings["mode"] == "active" and settings["stage"] > 0
    # A requested lab level is not necessarily an *applied* level. The
    # resource governor can block the extra compute; do not report ACTIVE
    # if the phone is actually under thermal/RAM pressure.
    out["lab_requested_active"] = requested
    out["lab_compute_active"] = requested and resource_mode in ("GREEN", "YELLOW")
    out["lab_compute_gate"] = (
        "APPLIED" if out["lab_compute_active"]
        else "BLOCKED_RESOURCE" if requested else "NOT_REQUESTED")
    if not out["lab_compute_active"]:
        return out
    stage = settings["stage"]
    # A hypothetical Age 6..10 cannot manufacture a missing Age 6..10
    # permission or trained organ. It only explores bounded compute headroom.
    # The user-requested level 10 uses the maximum existing effort band,
    # not additional unimplemented rights.
    out["autonomous_effort_max"] = (
        "max" if stage >= 8 else "high" if stage >= 5
        else "adaptive" if stage >= 2 else "low")
    out["focal_depth"] = min(3, 1 + (stage // 4))
    out["deliberation"] = False
    out["tools"] = False
    out["long_loops"] = False
    return out


def view(home, *, official_stage=0):
    settings = read(home)
    path = _path(home)
    stored = path.is_file() and not path.is_symlink()
    return dict(settings, official_stage=official_stage,
                config_persisted=stored,
                compute_requested=settings["mode"] == "active" and settings["stage"] > 0,
                effective_on_healthy_resources=(
                    settings["mode"] == "active" and settings["stage"] > 0),
                resource_guard_may_block=True,
                test_only=True, verified_maturity_unchanged=True,
                tool_authority="UNCHANGED", weight_authority="UNCHANGED",
                max_compute_focal_depth=3,
                note="Labor-Stufe ist keine Age-Beförderung; sie steuert reale begrenzte Denkbudgets")
