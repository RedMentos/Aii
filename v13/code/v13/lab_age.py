"""Independent user-selected laboratory AGE feature/test permission level.

Official Age/evidence remain unchanged. ACTIVE tests implemented feature
gates (tools, learning, dreams, planning) in the composed runtime. Physical
CPU/time budgets stay separate; RECORD_ONLY still blocks live model updates.
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
    """Local UI/CLI control. Changes experimental feature gates, never official Age."""
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
    """Annotate the lab capability test; NEVER change CPU or reasoning budgets.

    Age stages select feature/right gates. The real resource governor continues
    to constrain physical execution independently of experimental feature tests.
    """
    settings = read(control.s.home)
    out = dict(baseline)
    out["lab_mode"] = settings["mode"]
    out["lab_stage"] = settings["stage"]
    out["official_stage"] = baseline["stage"]
    requested = settings["mode"] == "active" and settings["stage"] > 0
    out["lab_feature_test_requested"] = requested
    out["lab_feature_test_active"] = requested
    out["lab_effective_implemented_stage"] = min(settings["stage"], 5) if requested else None
    out["lab_compute_active"] = False
    out["lab_compute_gate"] = "NOT_A_COMPUTE_SETTING"
    return out


def view(home, *, official_stage=0):
    settings = read(home)
    path = _path(home)
    stored = path.is_file() and not path.is_symlink()
    active = settings["mode"] == "active" and settings["stage"] > 0
    return dict(settings, official_stage=official_stage,
                config_persisted=stored,
                compute_requested=False,
                feature_test_requested=active,
                feature_gates_active=active,
                effective_implemented_stage=min(settings["stage"], 5) if active else None,
                implemented_stage_ceiling=5,
                runtime_released_stage_6_plus=False,
                resource_guard_may_block=True,
                test_only=True, verified_maturity_unchanged=True,
                tool_authority="AGE_GATES_TEST_ONLY",
                learning_commit_authority="REQUIRES_SEPARATE_SHADOW_MODE",
                note="Labor-Age testet Werkzeug- und Lernrechte, nicht Rechenzeit; offizielles Age bleibt separat")
