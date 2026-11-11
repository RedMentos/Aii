#!/usr/bin/env python3
"""V13 synthetic UI + tiny JEPA acceptance probe (never controls Android).

From v13/code:
    python scripts/android_sim_jepa_smoke.py --notes 24 --seed 17 --steps 5

A disposable private fake device is fed explicit TEST-ONLY dry-run broker
envelopes, not real Android gestures or human approvals. Its numeric receipts
train/replay a tiny NumPy WorldJEPA, verify inference checkpoint readback, and
report holdout/forgetting comparisons. No GGUF, real Store/T8, network or OS
control occurs. Output is a truthful review receipt, not a model benchmark.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v13.android_control import AndroidControlBroker
from v13.android_control_sim import SimulatedAndroidWorld, DEMO_PACKAGE
from v13.android_sim_jepa_probe import trial, replay_ablation

REVISION = "v13-synthetic-android-jepa-smoke-v1"


def _do(broker, simulator, capability, args):
    # The test harness intentionally simulates UI confirmation. The broker
    # still DENIES any live Android transport, and this test cannot execute
    # OS actions. Do NOT copy this path into a real companion service.
    proposal = broker.propose(capability, args)
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    receipt = simulator.apply(broker.execute(proposal.action_id, dry_run=True))
    if receipt["native_android_executed"] or not receipt["simulation_applied"]:
        raise ValueError("synthetic action crossed native boundary")


def probe(notes=24, seed=17, steps=5):
    if type(notes) is not int or not 12 <= notes <= 48:
        raise ValueError("notes must be 12..48")
    if type(seed) is not int or not 0 <= seed <= 2**63-1:
        raise ValueError("synthetic JEPA seed invalid")
    if type(steps) is not int or not 1 <= steps <= 32:
        raise ValueError("steps must be 1..32")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="v13-synthetic-android-") as scratch:
        home = Path(scratch)
        broker = AndroidControlBroker(home / "broker.sqlite")
        device = SimulatedAndroidWorld(home)
        try:
            broker.start()
            _do(broker, device, "launch_app", {"package": DEMO_PACKAGE})
            for index in range(notes):
                _do(broker, device, "tap", {"x": 200, "y": 150})
                _do(broker, device, "type_text", {
                    "text": "SYNTHETIC-LOCAL-NOTE-%d" % index
                })
                _do(broker, device, "tap", {"x": 200, "y": 350})
                _do(broker, device, "observe_ui", {})
            view = device.view()
            if (view["screen"] != "NOTES" or len(view["notes"]) != notes
                    or device.receipt_count() != 1 + 4 * notes):
                raise ValueError("simulated UI goal failed")
            first = trial(
                device, seed=seed, steps=steps,
                checkpoint=home / "synthetic_inference_checkpoint.npz"
            )
            ablation = replay_ablation(device, seed=seed, steps=steps)
            if not (first["readback"]["inference_reload_exact_loss"]
                    and ablation["both_models_changed_numeric_weights"]):
                raise ValueError("synthetic numeric learning proof failed")
            return {
                "revision": REVISION,
                "evidence_level": "SYNTHETIC_LOCAL_PYTHON_ONLY",
                "simulation_goal": {
                    "fake_app": DEMO_PACKAGE,
                    "notes_created": notes,
                    "committed_action_receipts": device.receipt_count(),
                    "native_android_executed": False,
                    "approvals": "SYNTHETIC_TEST_ONLY_NOT_HUMAN_UI",
                },
                "jepa": first, "replay": ablation,
                "elapsed_seconds": round(time.monotonic() - started, 4),
                "active_model_promoted": False,
                "registered_t8_modified": False,
                "pretrained_gguf_modified": False,
                "claim_limit": (
                    "Synthetic UI and NumPy JEPA software only. No true Android "
                    "device actions, autonomous native permissions, model "
                    "token/s, AGI or pinned real-device retention proof."
                ),
            }
        finally:
            device.close()
            broker.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notes", type=int, default=24)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    result = probe(args.notes, args.seed, args.steps)
    data = (json.dumps(result, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")
    if args.report is not None:
        if (not args.report.parent.is_dir() or args.report.parent.is_symlink()
                or args.report.exists() or args.report.is_symlink()):
            raise ValueError("report destination must be a new private file")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(args.report, flags, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    print(data.decode("utf-8"), end="")


if __name__ == "__main__":
    main()
