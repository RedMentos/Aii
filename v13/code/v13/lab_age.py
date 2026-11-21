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
# Laboratory age is a TEST of implemented feature/right gates, NOT a
# resource/compute budget or a verified progression of developmental Age.
# Owner requested active stage 10. Missing settings therefore default to
# X10 active; explicit off/shadow is preserved, corrupt settings fail closed.
# The runtime still has independently configured user tool enables,
# prohibitions, resource safety, per-effect confirmation, and stop controls.
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
                feature_gates_active=False,  # only the running staged controller can attest
                runtime_gate_attested=False,
                effective_implemented_stage=min(settings["stage"], 5) if active else None,
                implemented_stage_ceiling=5,
                runtime_released_stage_6_plus=False,
                resource_guard_may_block=True,
                test_only=True, verified_maturity_unchanged=True,
                tool_authority="AGE_GATES_TEST_ONLY",
                learning_commit_authority="REQUIRES_SEPARATE_SHADOW_MODE",
                note="Labor-Age testet Werkzeug- und Lernrechte, nicht Rechenzeit; offizielles Age bleibt separat")

def effective_stage(home):
    """Implemented rights ceiling in a selected *active* lab, else None.

    Stages 6..10 have no implemented additional Age rules, so X10 exercises
    all *implemented* stage 0..5 rights only. It does NOT invent organs.
    """
    state = read(home)
    if state["mode"] != "active" or state["stage"] <= 0:
        return None
    return min(state["stage"], 5)


def right_enabled(control, right, earned):
    """Pass an established Age right through the owner's lab test selection.

    Called *after* AgeControl's hard prohibitions, explicit user-permissions,
    structural lock and resource gating. It changes no persistent Age state,
    capability maturity, physical compute budget or model weights.
    """
    if earned:
        return True
    stage = effective_stage(control.s.home)
    if stage is None:
        return False
    from .age import RIGHTS
    return stage >= RIGHTS[right]


class LabConfig(dict):
    """Runtime config with thread-scoped explicit shadow-training rights.

    Ordinary turns and background tasks see the original learning mode.
    Only an explicitly queued lab_shadow task gets SHADOW_UPDATE, only while
    the saved laboratory mode still authorizes testing; never COMMIT.
    This also makes an owner OFF request revoke the overlay on its next read.
    """
    def __init__(self, original, home):
        super().__init__(original)
        self.lab_home = Path(home)
        import threading
        self._trial = threading.local()

    def __getitem__(self, key):
        if (key == "learning_mode" and getattr(self._trial, "active", False)
                and effective_stage(self.lab_home) is not None
                and effective_stage(self.lab_home) >= 2
                and dict.__getitem__(self, "learning_mode") == "RECORD_ONLY"):
            return "SHADOW_UPDATE"
        return dict.__getitem__(self, key)

    def get(self, key, default=None):
        return self[key] if key in self else default

    def shadow_training(self):
        from contextlib import contextmanager

        @contextmanager
        def scope():
            if (effective_stage(self.lab_home) is None
                    or effective_stage(self.lab_home) < 2):
                raise ValueError("LAB_LEARNING_RIGHT_NOT_ACTIVE")
            if getattr(self._trial, "active", False):
                raise ValueError("LAB_LEARNING_ALREADY_ACTIVE")
            # A separate explicit normal learning mode takes precedence;
            # the experimental scope does not switch to APPROVED_COMMIT.
            if dict.__getitem__(self, "learning_mode") != "RECORD_ONLY":
                raise ValueError("LAB_SHADOW_REQUIRES_RECORD_ONLY_BASELINE")
            self._trial.active = True
            try:
                yield
            finally:
                self._trial.active = False

        return scope()


def rights_status(control, resource_mode="GREEN"):
    """Truthful effective-vs-earned grant list for owner/test diagnostics."""
    from .age import RIGHTS, RIGHT_CAPABILITY
    base = sorted(r for r in RIGHTS
                  if control.ceiling(RIGHT_CAPABILITY.get(r, "system"))
                  >= RIGHTS[r])
    actual = sorted(r for r in RIGHTS if control.may(r, resource_mode=resource_mode))
    trial = [r for r in actual if r not in base]
    lab = view(control.s.home, official_stage=control.system_stage())
    return {"official_stage": control.system_stage(),
            "requested_lab_stage": lab["stage"],
            "lab_mode": lab["mode"],
            "implemented_test_stage": effective_stage(control.s.home),
            "granted_effective": actual,
            "newly_testable": trial,
            "earned_stage_unchanged": True,
            "explicit_per_tool_enable_still_required": True,
            "human_approval_still_required_for_effects": True,
            "shadow_training_only_when_explicitly_queued": True,
            "native_model_feature_coverage_verified": False}
