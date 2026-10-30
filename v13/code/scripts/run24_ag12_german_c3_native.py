"""Run24 pinned Linux-native C3 AG12 German then English full-suite observation.

Only public immutable model/runner artifacts. No training, model weight changes,
raw holdout prompt export, tool calls, Age promotion or phone claim.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time

from v13.bootstrap import extract
from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize
from v13.models import ModelManager, catalog, download_file, platform_tag
from v13.runtime import Runtime
from v13.agi import hub
from v13.agi import solver as sv
from v13.agi.language_compare import compare_languages

MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_TAR_SHA = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
MODEL_REV = "657e078c94084481950a2d555a941481f715536b"
MODEL_ID = "LiquidAI/LFM2.5-350M-GGUF"
RUNNER_TAG = "b10964"
MODEL_BYTES = 219312832
RUNNER_BYTES = 16825086
PER_LANGUAGE_DEADLINE_S = 720


def _pinned_catalog():
    specs = catalog()
    model = specs["models"]["language"]
    file = model["files"][0]
    runner = specs["runner"]["linux_binaries"]["linux-x86_64"]
    if (model["model_id"] != MODEL_ID or model["revision"] != MODEL_REV
            or model["license_id"] != "LFM Open License 1.0"
            or file["size"] != MODEL_BYTES or file["sha256"] != MODEL_SHA
            or specs["runner"]["tag"] != RUNNER_TAG
            or runner["size"] != RUNNER_BYTES or runner["sha256"] != RUNNER_TAR_SHA):
        raise ValueError("RUN24_PINNED_PUBLIC_ARTIFACT_IDENTITY_RED")
    return specs, model, runner


def _install(home):
    specs, model, runner_spec = _pinned_catalog()
    initialize(home)
    manager = ModelManager(home)
    manager.install("language")
    model_path = manager.path_for("C3_LANGUAGE")
    if file_hash(model_path) != MODEL_SHA:
        raise ValueError("RUN24_C3_BYTES_RED")
    archive = home / "tmp/llama-native.tar.gz"
    download_file(runner_spec, archive)
    if file_hash(archive) != RUNNER_TAR_SHA:
        raise ValueError("RUN24_RUNNER_BYTES_RED")
    dest = home / "bin" / RUNNER_TAG
    extract(archive, dest)
    servers = [p for p in dest.rglob("llama-server") if p.is_file()]
    if len(servers) != 1:
        raise ValueError("RUN24_RUNNER_UNIQUE_BINARY_RED")
    server = servers[0]
    server.chmod(0o700)
    link = home / "bin/llama-server"
    if link.exists() or link.is_symlink():
        raise FileExistsError("RUN24_FRESH_RUNNER_REQUIRED")
    link.symlink_to(server)
    version = subprocess.run([str(link), "--version"], capture_output=True,
                             text=True, timeout=15)
    if version.returncode:
        raise RuntimeError("RUN24_RUNNER_VERSION_RED:" + version.stderr[-250:])
    atomic_write(home / "config/runner.json", dumps({
        "tag": RUNNER_TAG, "platform": platform_tag(),
        "binary_sha256": file_hash(link),
        "version": (version.stdout + version.stderr).strip(),
        "phone_runner_proof": None,
    }))
    return model_path, archive, link


def run(home, out):
    home, out = Path(home), Path(out)
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise ValueError("RUN24_LINUX_X86_64_ONLY")
    if home.exists() or out.exists():
        raise FileExistsError("RUN24_FRESH_PATHS_REQUIRED")
    out.mkdir(parents=True)
    report = {
        "schema": "v13.run24.ag12_german_english_c3_linux_native.v1",
        "evidence_kind": "LINUX_NATIVE_C3_AG12_ONLY",
        "platform": platform.platform(),
        "model_id": MODEL_ID, "model_revision": MODEL_REV,
        "license_id": "LFM Open License 1.0",
        "model_sha256": None, "runner_tar_sha256": None,
        "actual_llama_server_sha256": None,
        "seed": 13, "expected_items_per_language": 88,
        "language_order": ["de", "en"],
        "per_language_deadline_s": PER_LANGUAGE_DEADLINE_S,
        "runs": {}, "comparison": None,
        "learning_mode": "RECORD_ONLY",
        "jepa_weight": 0, "b3_promoted": False,
        "step2_promoted": False, "body_jepa_promoted": False,
        "redmi_measured": False, "whole_system_complete": False,
        "model_revision_bound_to_comparison": False,
        "learned_german_transfer_proven": False,
    }
    runtime = None
    started = time.monotonic()
    try:
        model, archive, binary = _install(home)
        report.update(model_sha256=file_hash(model),
                      runner_tar_sha256=file_hash(archive),
                      actual_llama_server_sha256=file_hash(binary))
        runtime = Runtime(home)
        runtime.sleep.cycle.set_policy("enabled", "off")
        cfg = runtime.cfg
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg.get("jepa_weight", 0) != 0 or cfg["latents_enabled"]):
            raise ValueError("RUN24_AGE0_NEGATIVE_GATE_RED")
        if runtime.models.path_for("C3_LANGUAGE") != model:
            raise ValueError("RUN24_MODEL_PATH_RED")
        growth = hub(runtime)
        before = runtime.store.one("SELECT COUNT(*) n FROM events")["n"]
        for lang in ("de", "en"):
            began = time.monotonic()
            result = sv.run(growth, runtime, "c3", lang=lang,
                            label="run24-linux-native",
                            deadline=time.monotonic() + PER_LANGUAGE_DEADLINE_S)
            report["runs"][lang] = result | {"elapsed_s": round(time.monotonic()-began, 3)}
            export = home / "exports" / ("generality-last-de.json" if lang == "de" else "generality-last.json")
            if export.is_file():
                shutil.copy2(export, out / ("AG12_" + lang.upper() + "_ROWS.json"))
            # A failed native stage remains in the report; never replace it with
            # a synthetic/fake runner or call the partial result full completion.
            if result["status"] != "DONE":
                break
        report["comparison"] = compare_languages(runtime.store, solver="c3")
        after = runtime.store.one("SELECT COUNT(*) n FROM events")["n"]
        report["events_before"] = before
        report["events_after"] = after
        report["no_holdout_prompts_in_events"] = before == after
        report["native_role"] = "C3_LANGUAGE"
        report["native_calls_observed"] = sum(
            (entry.get("stats") or {}).get("C3_LANGUAGE", {}).get("items", 0)
            for entry in report["runs"].values()
        )
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)[:400]
    finally:
        if runtime is not None:
            try:
                runtime.close()
                report["runtime_closed"] = True
            except Exception as exc:
                report["runtime_closed"] = False
                report["close_error"] = type(exc).__name__ + ": " + str(exc)[:200]
        report["elapsed_s"] = round(time.monotonic()-started, 3)
        (out / "REPORT.json").write_text(
            json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
            encoding="utf-8")
    if (report.get("error") or report.get("runtime_closed") is not True
            or report.get("no_holdout_prompts_in_events") is not True
            or report.get("native_calls_observed", 0) <= 0
            or any(report["runs"].get(lang, {}).get("status") != "DONE"
                   for lang in ("de", "en"))):
        raise RuntimeError("RUN24_NATIVE_INCOMPLETE_OR_RED; closed report retained")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.home, args.out)
    print(json.dumps({"evidence_kind": result["evidence_kind"],
                      "native_calls_observed": result["native_calls_observed"],
                      "comparison_status": result["comparison"]["status"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
