#!/usr/bin/env python3
"""Run117DC explicit manual Termux C3 source-only probe, default OFF.

No download, production memory, output/tool delivery, learning or gate claim.
Android local runner manifest is self-consistent, NOT externally attested.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from scripts import run117cy_live_source_native as cy
from v13.common import atomic_write, dumps, file_hash
from v13.models import ModelManager, platform_tag

MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REV = "657e078c94084481950a2d555a941481f715536b"
MODEL_SIZE = 219312832
MODEL_FILE = "LFM2.5-350M-QAD-Q4_0.gguf"
RUNNER_TAG = "b10964"
PLATFORM = "android-arm64"
SCHEMA = "v13.run117dc.android_local_source_only_c3_unverified_runner.v1"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def android_pin(installed):
    """No silent 230M fallback or untrusted runner symlink escape."""
    if platform_tag() != PLATFORM:
        raise ValueError("RUN117DC_ANDROID_ONLY_NO_NATIVE_CLAIM")
    installed = Path(installed)
    manager = ModelManager(installed)
    model = manager.path_for("C3_LANGUAGE")
    if (not model.is_file() or model.is_symlink()
            or model.name != MODEL_FILE
            or model.stat().st_size != MODEL_SIZE
            or manager.revision("C3_LANGUAGE") != MODEL_REV
            or file_hash(model) != MODEL_SHA):
        raise ValueError("RUN117DC_C3_PIN_RED_UPGRADE_MANUALLY")
    binary = installed / "bin/llama-server"
    manifest = installed / "config/runner.json"
    if (not binary.is_symlink() or not manifest.is_file()
            or manifest.is_symlink()):
        raise ValueError("RUN117DC_RUNNER_MANIFEST_RED")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        direct = Path(os.readlink(binary))
        target = binary.resolve(strict=True)
        rel = target.relative_to((installed / "bin").resolve(strict=True))
        actual = file_hash(binary)
        if (data.get("tag") != RUNNER_TAG
                or data.get("platform") != PLATFORM
                or type(data.get("binary_sha256")) is not str
                or len(data["binary_sha256"]) != 64
                or data["binary_sha256"] != actual
                or not direct.is_absolute() or direct.is_symlink()
                or direct != target or not target.is_file()
                or target.is_symlink() or target.name != "llama-server"
                or len(rel.parts) < 3
                or not rel.parts[0].startswith(".llama-b10964-")):
            raise ValueError("RUN117DC_RUNNER_BINDING_RED")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("RUN117DC_RUNNER_BINDING_RED") from exc
    return model


def run_phone(installed, probe_home, out):
    """Explicit user invocation only. No injected fake runner accepted."""
    installed, probe_home, out = Path(installed), Path(probe_home), Path(out)
    if platform_tag() != PLATFORM:
        raise ValueError("RUN117DC_ANDROID_ONLY_NO_NATIVE_CLAIM")
    if (installed.resolve() == probe_home.resolve()
            or installed.resolve() == out.resolve()
            or probe_home.resolve() == out.resolve()):
        raise ValueError("RUN117DC_ISOLATED_PATHS_REQUIRED")
    if probe_home.exists() or out.exists():
        raise FileExistsError("RUN117DC_FRESH_PROBE_AND_OUTPUT_REQUIRED")
    model = android_pin(installed)
    binary = installed / "bin/llama-server"
    binary_hash = file_hash(binary)
    manifest_hash = file_hash(installed / "config/runner.json")
    # cy.run is the verified real Store source-only callback, but its injected
    # pin intentionally gives ZERO native proof. Do not override that gate.
    raw = cy.run(installed, probe_home, out, pin_factory=android_pin)
    structural = (
        raw.get("status") == "SYNTHETIC_STRUCTURAL_SMOKE_NON_PROMOTING"
        and raw.get("native_c3_calls") == 1
        and raw.get("native_final") is True
        and raw.get("process_reaped") is True
        and raw.get("source_rechecked") is True
        and raw.get("closed_store_ok") is True
        and raw.get("no_live_output") is True
        and raw.get("pins_unchanged") is True
        and raw.get("error_type") is None
        and raw.get("native_metrics", {}).get("actual_model") == MODEL_FILE
        and android_pin(installed) == model
        and file_hash(binary) == binary_hash
        and file_hash(installed / "config/runner.json") == manifest_hash
    )
    result = {
        "schema": SCHEMA,
        "status": ("ANDROID_LOCAL_NATIVE_UNVERIFIED_RUNNER_NONPROMOTING"
                   if structural else "ANDROID_LOCAL_STRUCTURAL_RED"),
        "evidence_class": "ANDROID_LOCAL_NATIVE_UNVERIFIED_RUNNER",
        "local_native_process_observed": bool(structural),
        "native_proof": False, "native_calls_verified": 0,
        "redmi_measured": False, "independent_generalization": False,
        "runner_binary_sha256_local_only": binary_hash,
        "runner_manifest_sha256_local_only": manifest_hash,
        "model_sha256": MODEL_SHA, "model_revision": MODEL_REV,
        "original_report_sha256": file_hash(out / "report.json"),
        "original_report_status": raw["status"],
        "native_c3_attempts": raw["native_c3_calls"],
        "native_final": raw["native_final"],
        "process_reaped": raw["process_reaped"],
        "source_rechecked": raw["source_rechecked"],
        "closed_store_ok": raw["closed_store_ok"],
        "offline_exact": raw.get("offline_exact"),
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "whole_system_complete": False, "output_committed": False,
        "learning_authority": 0, "delivery_authority": 0,
        "tool_dispatches": 0,
    }
    atomic_write(out / "phone_report.json", dumps(result))
    return result


def main():
    p = argparse.ArgumentParser(description="Manual Android C3 source-only synthetic probe; no live output")
    p.add_argument("--installed", type=Path, required=True)
    p.add_argument("--probe-home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = run_phone(a.installed, a.probe_home, a.out)
    print(dumps({"status": result["status"],
                 "local_native_process_observed": result["local_native_process_observed"],
                 "native_proof": False, "redmi_measured": False,
                 "output_committed": False}))
    return 0 if result["local_native_process_observed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
