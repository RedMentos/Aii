"""Run12L preregistered native C2 route-label proxy, no semantic utility claim."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import traceback

from v13.cognition import scaffold_route
from v13.common import file_hash
from v13.config import initialize
from v13.models import ModelManager
from scripts import c2_native_route_provenance_20261030 as original
from scripts import c2_strict_native_compat_run12k as strict
from scripts.c2_route_proxy_score_run12l import (
    FIXTURE_SHA256, PROMPTS_SHA256, load_fixture, score,
)

NEEDLE_SHA256 = "c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38"


def run(home, out, fixture_path):
    home, out = Path(home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_DIRECTORY_REQUIRED")
    fixture = load_fixture(fixture_path)
    cases = fixture["cases"]
    prompts = {c["prompt"] for c in cases}
    if (fixture["seed"] != original.SEED
            or prompts.intersection(original.PROMPTS)
            or prompts.intersection(strict.PROMPTS)
            or any(scaffold_route(c["prompt"]) != c["expected_scaffold"]
                   for c in cases)):
        raise ValueError("RUN12L_DISJOINT_OR_SCAFFOLD_MISMATCH")
    out.mkdir(parents=True)
    (out / "raw").mkdir()
    rows = []
    metadata = {
        "fixture_sha256": FIXTURE_SHA256,
        "prompts_sha256": PROMPTS_SHA256,
        "seed": original.SEED,
        "needle_model_sha256": None,
        "needle_worker_sha256": None,
        "native_runner": "original_c2_native_route_provenance._turn",
        "original_run12k_source_unchanged": True,
    }
    try:
        cfg = initialize(home)
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg["latents_enabled"] or cfg.get("jepa_weight", 0) != 0):
            raise ValueError("BASE_NOT_AGE0")
        manager = ModelManager(home)
        verified = manager.verify(deep=True)
        if (verified.get("needle", {}).get("ok") is not True
                or verified["needle"].get("hash_checked") is not True):
            raise ValueError("NEEDLE_NOT_VERIFIED")
        model_sha = file_hash(manager.path_for("C2_CONTROL"))
        if model_sha != NEEDLE_SHA256:
            raise ValueError("NEEDLE_SHA_MISMATCH")
        metadata["needle_model_sha256"] = model_sha
        metadata["needle_worker_sha256"] = file_hash(home / "bin/needle-worker")
        for i, case in enumerate(cases):
            try:
                row = original._turn(home, cfg, case["prompt"], i, out)
                row["strict_admission"] = strict.classify(row)
                (out / "raw" / f"{i:02d}_STRICT_ADMISSION.json").write_text(
                    json.dumps(row["strict_admission"], sort_keys=True,
                               allow_nan=False) + "\n", encoding="utf-8")
            except BaseException as exc:
                row = {
                    "index": i, "prompt": case["prompt"],
                    "native_c2_invocation_valid_before_release": False,
                    "needle_process_reaped": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:200],
                }
                traceback.print_exc()
            rows.append(row)
            (out / "progress.json").write_text(json.dumps({
                **metadata, "status": "INCOMPLETE", "rows": rows,
            }, sort_keys=True, indent=2, ensure_ascii=False,
                allow_nan=False) + "\n", encoding="utf-8")
        result = score(fixture, rows)
    except BaseException as exc:
        traceback.print_exc()
        result = score(fixture, rows)
        result["status"] = "NATIVE_ROUTE_PROXY_SETUP_ERROR"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)[:200]
    finally:
        (out / "report.json").write_text(json.dumps({
            **metadata, **result, "rows": rows,
        }, sort_keys=True, indent=2, ensure_ascii=False,
            allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "native_c2_proven": result["native_c2_proven"],
        "proxy_threshold_met": result["proxy_threshold_met"],
        "net_correct_gain_first12": result["net_correct_gain_first12"],
    }, sort_keys=True))
    return result["proxy_threshold_met"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args()
    return 0 if run(a.home, a.out, a.fixture) else 2


if __name__ == "__main__":
    raise SystemExit(main())
