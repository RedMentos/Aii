#!/usr/bin/env python3
"""Run496: frozen Run491 held-out STEP2 pilot harness (source-only until --execute).

Two preregistered episodes Vesper/Willow, arm C, seed 31, seven variants each.
Does not modify any frozen source file, fixture hash, model/runner pin or gate.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path

import run491_step2_heldout10 as frozen

PILOT_IDS = ("Vesper", "Willow")
PILOT_ARM = "C"
PILOT_SEED = 31
EXPECTED_ROWS = 14
EXPECTED_VARIANTS = frozenset(frozen.VARIANTS)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def pilot_registration():
    full = frozen.registration()  # verifies all ten original fixture bytes
    require(full["fixture_sha256"] == frozen.FIXTURE_SHA256, "FROZEN_FULL_FIXTURE_CHANGED")
    require(tuple(full["seeds"]) == (31, 32, 33) and
            tuple(full["arms"]) == ("A", "B", "C", "D", "E") and
            tuple(full["variants"]) == frozen.VARIANTS, "FROZEN_COHORT_CHANGED")
    subset = [f for f in full["fixtures"] if f["id"] in PILOT_IDS]
    require(tuple(f["id"] for f in subset) == PILOT_IDS, "PILOT_SUBSET_CHANGED")
    return {
        "schema": "V13_RUN496_FROZEN_RUN491_PILOT_V1",
        "status": "SOURCE_ONLY_PILOT_READY_NO_NATIVE",
        "full_fixture_sha256": frozen.FIXTURE_SHA256,
        "pilot_fixture_sha256": hashlib.sha256(canonical(subset)).hexdigest(),
        "pilot_ids": list(PILOT_IDS),
        "pilot_fixtures": subset,
        "seed": PILOT_SEED,
        "arm": PILOT_ARM,
        "variants": list(frozen.VARIANTS),
        "expected_rows": EXPECTED_ROWS,
        "model_sha256_expected_not_retrieved": frozen.MODEL_SHA256,
        "runner_sha256_expected_not_retrieved": frozen.RUNNER_SHA256,
        "native_executed": False, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
    }


@contextmanager
def pilot_modules():
    """Patch only in-memory private harness globals; always restore originals."""
    import step2_z2_timescale as z2
    import step2_z2b_seeds as z2b
    saved_fixtures = z2.FIXTURES
    saved_arms = dict(z2b.ARMS)
    saved_seeds = z2b.SEEDS
    reg = pilot_registration()
    require(set(z2.ARMS) == set(frozen.ARMS), "ORIGINAL_FIVE_ARMS_CHANGED")
    require(z2.ARMS[PILOT_ARM]["b1_recent_source_chars"] == 600 and
            z2.ARMS[PILOT_ARM]["offer_quote_context_chars"] == 200,
            "PILOT_ARM_C_SETTINGS_CHANGED")
    try:
        z2.FIXTURES = reg["pilot_fixtures"]
        z2b.ARMS.clear()
        z2b.ARMS.update({arm: {"base": arm, "query": False} for arm in frozen.ARMS})
        z2b.SEEDS = frozen.SEEDS
        yield z2, z2b
    finally:
        z2.FIXTURES = saved_fixtures
        z2b.ARMS.clear()
        z2b.ARMS.update(saved_arms)
        z2b.SEEDS = saved_seeds


def verify_installed(installed):
    """Actual byte-level model and executable preflight, not HF API metadata."""
    from v13.models import ModelManager, catalog
    from v13.common import file_hash
    from v13.memory_server import runtime_library_hashes
    home = Path(installed)
    manager = ModelManager(home)
    checks = manager.verify(deep=True)
    require(all(checks[k]["ok"] and checks[k]["hash_checked"]
                for k in ("needle", "language", "body", "gist")),
            "INSTALLED_MODEL_DEEP_HASH_FAILED")
    for role, expected in frozen.MODEL_SHA256.items():
        require(file_hash(manager.path_for(role)) == expected,
                "INSTALLED_MODEL_SHA_CHANGED_" + role)
    require(all(manager.installed[k]["exact_revision"] == catalog()["models"][k]["revision"]
                for k in ("needle", "language", "body", "gist")),
            "INSTALLED_MODEL_REVISION_CHANGED")
    runner = home / "bin" / "llama-server"
    require(runner.is_file() and not runner.is_symlink() and
            file_hash(runner) == frozen.RUNNER_SHA256, "PINNED_RUNNER_BINARY_CHANGED")
    runner_meta = json.loads((home / "config" / "runner.json").read_text())
    require(runner_meta["tag"] == "b10964" and
            runner_meta["binary_sha256"] == frozen.RUNNER_SHA256,
            "PINNED_RUNNER_METADATA_CHANGED")
    libraries = runtime_library_hashes(runner)
    require(type(libraries) is dict and libraries,
            "NATIVE_RUNNER_LIBRARIES_UNVERIFIED")
    return {"model_sha256": dict(frozen.MODEL_SHA256),
            "runner_sha256": frozen.RUNNER_SHA256,
            "runtime_library_sha256": libraries,
            "native_executed": False}


def verify_rows(tool, summary):
    """Independent structural/authority checks; cannot certify semantic utility."""
    require(type(tool) is dict and type(summary) is dict, "NATIVE_REPORT_SCHEMA")
    require(tool.get("installed_artifacts_unchanged") is True,
            "INSTALLED_ARTIFACTS_CHANGED")
    rows = tool.get("rows")
    require(type(rows) is list and len(rows) == EXPECTED_ROWS,
            "NATIVE_PILOT_ROW_COUNT")
    expected = {(fid, v) for fid in PILOT_IDS for v in EXPECTED_VARIANTS}
    keys = {(r.get("fixture"), r.get("variant")) for r in rows if type(r) is dict}
    require(len(keys) == EXPECTED_ROWS and keys == expected,
            "NATIVE_PILOT_VARIANT_COVERAGE")
    for row in rows:
        score = row.get("score")
        require(type(score) is dict and
                type(score.get("utility")) in (int, float) and
                math.isfinite(score["utility"]) and
                0 <= score["utility"] <= 1,
                "NATIVE_PILOT_UTILITY_INVALID")
    require(summary.get("run") == "C_s31" and summary.get("arm") == PILOT_ARM and
            summary.get("seed") == PILOT_SEED, "NATIVE_PILOT_IDENTITY_CHANGED")
    require(summary.get("tool_status") != "STRUCTURAL_FAIL" and
            summary.get("step2_status") != "DIAGNOSTIC_INCOMPLETE",
            "NATIVE_PILOT_STRUCTURAL_FAIL")
    tool_summary = summary.get("tool_summary")
    require(type(tool_summary) is dict and
            all(type(s) is dict and s.get("wrong_committed") == 0
                for s in tool_summary.values()), "NATIVE_PILOT_WRONG_COMMITTED")
    return {"status": "PILOT_14_ROWS_STRUCTURALLY_VERIFIED_ONLY",
            "rows_verified": EXPECTED_ROWS,
            "arm": PILOT_ARM, "seed": PILOT_SEED,
            "native_execution_performed": True,
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "b3_l1": "FAIL", "jepa_weight": 0, "redmi_measured": False}


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--installed-home", type=Path)
    p.add_argument("--fixture-only", action="store_true")
    p.add_argument("--execute", action="store_true")
    a = p.parse_args()
    require(a.fixture_only != a.execute, "EXACTLY_ONE_MODE_REQUIRED")
    reg = pilot_registration()
    manifest = a.work / "RUN496_PILOT_PREREG.json"
    if a.fixture_only:
        write_new(manifest, reg)
        print(json.dumps({"status": reg["status"], "pilot_ids": list(PILOT_IDS),
                          "rows": EXPECTED_ROWS, "native_executed": False}))
        return
    require(a.installed_home is not None, "NATIVE_INSTALLED_HOME_REQUIRED")
    require(manifest.is_file() and json.loads(manifest.read_text()) == reg,
            "PILOT_PREREG_NOT_FROZEN")
    require(not (a.work / "RUN496_PILOT_RESULT.json").exists(),
            "REFUSE_OVERWRITE_NATIVE_PILOT")
    preflight = verify_installed(a.installed_home)
    write_new(a.work / "RUN496_INSTALLED_PREFLIGHT.json", preflight)
    with pilot_modules() as (_z2, z2b):
        summary = z2b.run_one(a.installed_home, a.work, PILOT_ARM, PILOT_SEED)
    tool_path = a.work / "tool_C_s31.json"
    tool = json.loads(tool_path.read_text())
    result = verify_rows(tool, summary)
    result["tool_sha256"] = hashlib.sha256(tool_path.read_bytes()).hexdigest()
    result["summary_sha256"] = hashlib.sha256(
        (a.work / "summary_C_s31.json").read_bytes()).hexdigest()
    write_new(a.work / "RUN496_PILOT_RESULT.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
