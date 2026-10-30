"""Fresh v3 counterbalanced STEP2 budget-remainder paired native pilot (review-only).

Arms A=C3-only, B=default B1/B2, C=B1/B2 with arithmetic-aware body
questions. Each task/arm has a fresh isolated Age0 Runtime and original pinned
models; all native calls are serialized. No original cohort or gate is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import time
import traceback

from v13.common import dumps
from v13.config import initialize, save_config
from v13.models import ModelManager
from v13.proofs import audit_event
from v13.runtime import Runtime
from scripts.step2_paired_raw_validator_audit_20261030 import semantic_diagnostic

SCHEMA = "v13.step2.budget_paired_native_pilot.v3"
CANON_BLOB = "218464b12a2d27d92524c751922fa8e1c3fb0ea7"
CATALOG_BLOB = "7af05962af41d0bc3f7dd18ef01d4eba55eabf99"
TOOLS_BLOB = "954a3f468f10195fbce12d27f68585ee7edee2c9"
SEED = 41
ARMS = ("A_C3_ONLY", "B_DEFAULT_BOTH", "C_ARITH_BOTH")
ARM_ORDER = (ARMS, (ARMS[1], ARMS[2], ARMS[0]), (ARMS[2], ARMS[0], ARMS[1]))
B1_CANDIDATE = (
    "Read the exact source budget and each option cost. Calculate the "
    "remaining budget for each named option as budget minus cost; state "
    "each exact remainder in Euro and cite the source numbers. Do not "
    "invent missing values.")
B2_CANDIDATE = (
    "Read the exact source for both options. State the local-only rule "
    "and compare the actual durations and costs, identifying whether "
    "the faster option is cheaper or more expensive. Quote the source "
    "figures, do not assume the expensive option is faster.")
FIXTURES = (
    {"project": "Meridian", "budget": 214, "a": "Amber", "a_cost": 127,
     "a_days": 3, "b": "Indigo", "b_cost": 192, "b_days": 6},
    {"project": "Boreal", "budget": 305, "a": "Pine", "a_cost": 244,
     "a_days": 8, "b": "Slate", "b_cost": 287, "b_days": 2},
    {"project": "Nimbus", "budget": 178, "a": "Pearl", "a_cost": 139,
     "a_days": 2, "b": "Copper", "b_cost": 164, "b_days": 5},
    {"project": "Delta", "budget": 267, "a": "Moss", "a_cost": 201,
     "a_days": 6, "b": "Coral", "b_cost": 249, "b_days": 1},
    {"project": "Orchid", "budget": 352, "a": "Silver", "a_cost": 286,
     "a_days": 4, "b": "Onyx", "b_cost": 329, "b_days": 7},
    {"project": "Prism", "budget": 196, "a": "Dawn", "a_cost": 137,
     "a_days": 7, "b": "Dusk", "b_cost": 185, "b_days": 3},
    {"project": "Summit", "budget": 421, "a": "Ruby", "a_cost": 344,
     "a_days": 2, "b": "Topaz", "b_cost": 399, "b_days": 9},
    {"project": "Fjord", "budget": 233, "a": "Ash", "a_cost": 172,
     "a_days": 9, "b": "Birch", "b_cost": 221, "b_days": 4},
    {"project": "Helix", "budget": 319, "a": "Cobalt", "a_cost": 268,
     "a_days": 5, "b": "Ivory", "b_cost": 301, "b_days": 2},
)
FIXTURE_SHA256 = "fe9b86fdf561778ad540dd4767111f04c10a147a8a44cf783fa16f0d2c8a45ca"
EXPECTED_MODELS = {
    ARMS[0]: "LFM2.5-350M-QAD-Q4_0.gguf",
    ARMS[1]: "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
    ARMS[2]: "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
}

def fixture_hash():
    return hashlib.sha256(json.dumps(FIXTURES, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def prompt(f):
    return (
        f"Compare options for Project {f['project']}. Budget: {f['budget']} Euro. "
        f"Option {f['a']} costs {f['a_cost']} Euro and takes {f['a_days']} days. "
        f"Option {f['b']} costs {f['b_cost']} Euro and takes {f['b_days']} days. "
        "Both options must be local, no cloud. State the remaining budget "
        "for each named option and briefly explain the time/cost tradeoff."
    )


def route_evidence(meta, arm):
    """Route override provenance is NOT proof of native Needle/C2 control."""
    expected = "simple" if arm == ARMS[0] else "both"
    return (arm in ARMS and type(meta) is dict
            and meta.get("route") == {"source": "OPERATOR_ROUTE_OVERRIDE"}
            and type(meta.get("c2_packet")) is dict
            and meta["c2_packet"].get("route") == expected)


def score_pair(f, answer):
    """Preregistered contradiction-vetoing option-bound source arithmetic."""
    d = semantic_diagnostic(f, answer)
    a, b = d["a"]["correct"], d["b"]["correct"]
    return {"a": a, "b": b, "correct": int(a) + int(b),
            "out_of": 2, "diagnostic": d}

def validate_fixtures():
    if (fixture_hash() != FIXTURE_SHA256 or len(FIXTURES) != 9
            or len({f["project"] for f in FIXTURES}) != 4):
        raise ValueError("FIXTURE_COUNT_OR_DUPLICATE")
    for f in FIXTURES:
        if (not 0 < f["a_cost"] < f["budget"]
                or not 0 < f["b_cost"] < f["budget"]
                or f["a"] == f["b"]
                or f["a_days"] == f["b_days"]):
            raise ValueError("INVALID_FIXED_FIXTURE")
        p = prompt(f)
        for remaining in (f["budget"] - f["a_cost"],
                          f["budget"] - f["b_cost"]):
            if re.search(rf"(?<!\d){remaining}(?!\d)", p):
                raise ValueError("ANSWER_LEAKED_IN_PROMPT")
    for f in FIXTURES:
        for remaining in (f["budget"] - f["a_cost"],
                          f["budget"] - f["b_cost"]):
            for question in (B1_CANDIDATE, B2_CANDIDATE):
                if re.search(rf"(?<!\\d){remaining}(?!\\d)", question):
                    raise ValueError("ANSWER_LEAKED_IN_BODY_QUESTIONS")
    return True


def _fresh_turn(base_home, base_cfg, fixture, arm, index, out):
    """One isolated real turn; no Runtime, session or learned state reused."""
    with tempfile.TemporaryDirectory(dir=base_home / "tmp",
                                     prefix="step2-paired-") as td:
        home = Path(td)
        cfg = initialize(home)
        cfg.update(base_cfg)
        cfg.update(learning_mode="RECORD_ONLY", system_stage=0,
                   user_stage_cap=0, teacher_enabled=False,
                   latents_enabled=False, jepa_weight=0,
                   seed=SEED, history_turns=0,
                   route_override=("simple" if arm == ARMS[0] else "both"),
                   observer_mode=("off" if arm == ARMS[0] else "background"))
        if arm == ARMS[2]:
            cfg["body_question_b1"] = B1_CANDIDATE
            cfg["body_question_b2"] = B2_CANDIDATE
        save_config(home, cfg)
        for name in ("models", "bin"):
            shutil.rmtree(home / name)
            (home / name).symlink_to(base_home / name, target_is_directory=True)
        shutil.copyfile(base_home / "config/models.json",
                        home / "config/models.json")
        runtime = Runtime(home)
        try:
            if arm == ARMS[0]:
                runtime.models.installed.pop("body", None)
                runtime.models.installed.pop("gist", None)
                runtime.models.save()
            eid = runtime.submit(prompt(fixture))
            end = time.monotonic() + runtime.cfg["deadline_seconds"] + 2 * runtime.cfg["observer_seconds"] + 15
            while not runtime.idle():
                if time.monotonic() > end:
                    runtime.cancel()
                    raise TimeoutError("NATIVE_TURN_DEADLINE")
                time.sleep(.05)
            audit = audit_event(runtime.store, eid)
            raw_path = out / "raw" / f"{index:02d}_{arm}.json"
            raw_path.write_text(json.dumps(audit, sort_keys=True, ensure_ascii=False,
                                           allow_nan=False) + "\n")
            meta = audit.get("output_metadata", {})
            offers = {p.get("role") for p in audit.get("offers", [])}
            # The original pilot incorrectly required route.native_control,
            # which is absent by design for explicit route_override. Prove
            # native C3/Body output separately; NEVER promote C2 native control.
            route_valid = route_evidence(meta, arm)
            runner = meta.get("runner", {})
            releases = list(runtime.pool.release_history)
            release_valid = (not releases if arm == ARMS[0] else
                             len(releases) == 2
                             and {x.get("role") for x in releases}
                                 == {"B1_DETAIL", "B2_GIST"}
                             and all(x.get("process_reaped") is True
                                     for x in releases))
            valid = (bool(audit.get("checks")) and all(audit["checks"].values())
                     and not audit.get("source_errors")
                     and meta.get("model_generated") is True
                     and runner.get("actual_model") == EXPECTED_MODELS[arm]
                     and route_valid and release_valid
                     and (not offers if arm == ARMS[0] else
                          offers == {"B1_DETAIL", "B2_GIST"})
                     and (runner.get("role") == "C3_LANGUAGE" if arm == ARMS[0]
                          else runner.get("role") in ("B1_DETAIL", "B2_GIST")))
            scored = score_pair(fixture, audit.get("output", "")) if valid else {
                "a": False, "b": False, "correct": 0, "out_of": 2}
            return {"fixture": fixture["project"], "arm": arm,
                    "event_id": eid, "valid_native": bool(valid),
                    "route_override_evidence_valid": route_valid,
                    "native_c2_control_proven": False,
                    "body_offer_roles": sorted(offers),
                    "runner_role": runner.get("role"),
                    "final_output": audit.get("output", ""),
                    "duration_s": meta.get("duration_s"),
                    "score": scored, "raw_file": raw_path.name,
                    "native_process_releases": releases}
        finally:
            runtime.close()


def run(base_home, out):
    base_home, out = Path(base_home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_DIRECTORY_REQUIRED")
    validate_fixtures()
    out.mkdir(parents=True)
    (out / "raw").mkdir()
    report = {
        "schema": SCHEMA, "status": "INCOMPLETE", "created_wall_time": time.time(),
        "fixture_sha256": fixture_hash(), "fixtures": FIXTURES,
        "arms": ARMS, "arm_order": ARM_ORDER, "seed": SEED, "rows": [],
        "native_linux_only": True, "redmi_measured": False,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "comparative_step2_gate_promoted": False,
        "native_c2_control_proven": False,
        "claim_limit": "Nine-task counterbalanced pilot only, no STEP2 complementarity or mobile utility gate",
    }
    try:
        cfg = initialize(base_home)
        if (cfg["learning_mode"] != "RECORD_ONLY"
                or cfg["system_stage"] != 0 or cfg["latents_enabled"]
                or cfg.get("jepa_weight", 0) != 0):
            raise ValueError("BASE_NOT_AGE0")
        verify = ModelManager(base_home).verify(deep=True)
        roles = ("needle", "language", "body", "gist")
        if not all(verify.get(x, {}).get("ok") and
                   verify[x].get("hash_checked") is True for x in roles):
            raise ValueError("PINNED_NATIVE_MODELS_NOT_VERIFIED")
        report["model_verification"] = {
            x: {"ok": verify[x]["ok"], "hash_checked": verify[x]["hash_checked"]}
            for x in roles}
        for i, fixture in enumerate(FIXTURES):
            for arm in ARM_ORDER[i % 3]:
                try:
                    row = _fresh_turn(base_home, cfg, fixture, arm, i, out)
                except BaseException as exc:
                    row = {"fixture": fixture["project"], "arm": arm,
                           "valid_native": False, "score": {
                               "a": False, "b": False, "correct": 0, "out_of": 2},
                           "error_type": type(exc).__name__,
                           "error": str(exc)[:320]}
                    traceback.print_exc()
                report["rows"].append(row)
                (out / "progress.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True,
                               ensure_ascii=False, allow_nan=False) + "\n")
        totals = {arm: sum(r["score"]["correct"] for r in report["rows"]
                           if r["arm"] == arm) for arm in ARMS}
        valid = all(r.get("valid_native") is True for r in report["rows"])
        report["score_totals_out_of_18"] = totals
        report["pilot_gain"] = (valid and totals[ARMS[2]] >= totals[ARMS[1]] + 3
                                and totals[ARMS[2]] >= totals[ARMS[0]] + 3)
        report["status"] = ("PILOT_COMPLETE_NO_GATE" if valid
                            else "PILOT_PARTIAL_RED")
    except BaseException as exc:
        report.update(status="PILOT_ERROR", error_type=type(exc).__name__,
                      error=str(exc)[:320])
        traceback.print_exc()
    finally:
        (out / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True,
                       ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"],
                      "score_totals_out_of_18": report.get("score_totals_out_of_18"),
                      "pilot_gain": report.get("pilot_gain", False)},
                     sort_keys=True))
    return report["status"] == "PILOT_COMPLETE_NO_GATE"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    return 0 if run(args.home, args.out) else 2


if __name__ == "__main__":
    raise SystemExit(main())
