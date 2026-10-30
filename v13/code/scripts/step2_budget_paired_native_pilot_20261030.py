"""Fresh disjoint STEP2 budget-remainder paired native pilot (review-only).

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

SCHEMA = "v13.step2.budget_paired_native_pilot.v1"
CANON_BLOB = "218464b12a2d27d92524c751922fa8e1c3fb0ea7"
CATALOG_BLOB = "7af05962af41d0bc3f7dd18ef01d4eba55eabf99"
TOOLS_BLOB = "954a3f468f10195fbce12d27f68585ee7edee2c9"
SEED = 13
ARMS = ("A_C3_ONLY", "B_DEFAULT_BOTH", "C_ARITH_BOTH")
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
    {"project": "Vega", "budget": 145, "a": "Amber", "a_cost": 95,
     "a_days": 3, "b": "Cobalt", "b_cost": 125, "b_days": 1},
    {"project": "Lyra", "budget": 210, "a": "Copper", "a_cost": 150,
     "a_days": 2, "b": "Silver", "b_cost": 190, "b_days": 4},
    {"project": "Nadir", "budget": 180, "a": "Pine", "a_cost": 130,
     "a_days": 5, "b": "Birch", "b_cost": 165, "b_days": 2},
    {"project": "Orion", "budget": 275, "a": "Jade", "a_cost": 205,
     "a_days": 6, "b": "Coral", "b_cost": 250, "b_days": 3},
)
_LEFT = re.compile(r"\b(?:remain(?:s|ing)?|left|remainder|balance|rest|"
                   r"übrig|bleib(?:t|en)|verbleib(?:t|en))\b", re.I)


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


def _bound(text, label, foreign, amount):
    if not isinstance(text, str) or not isinstance(amount, int):
        return False
    label, foreign = re.escape(label), re.escape(foreign)
    number = rf"(?<!\d){amount}(?!\d|[.,]\d)\s*(?:euros?|eur|€)(?!\w)"
    between = rf"(?:(?!\b{foreign}\b)[^.!?;\n]){{0,90}}?"
    after = rf"(?:(?!\b{foreign}\b)[^.!?;\n]){{0,60}}"
    for pattern in (rf"\b{label}\b{between}{number}{after}",
                    rf"{number}{between}\b{label}\b{after}"):
        for match in re.finditer(pattern, text, re.I):
            if _LEFT.search(match.group(0)):
                return True
    return False


def score_pair(f, answer):
    a = _bound(answer, f["a"], f["b"], f["budget"] - f["a_cost"])
    b = _bound(answer, f["b"], f["a"], f["budget"] - f["b_cost"])
    return {"a": a, "b": b, "correct": int(a) + int(b), "out_of": 2}


def validate_fixtures():
    if len(FIXTURES) != 4 or len({f["project"] for f in FIXTURES}) != 4:
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
    if any(re.search(r"\b(?:50|60|20|15|70|25)\s*Euro\b", q, re.I)
           for q in (B1_CANDIDATE, B2_CANDIDATE)):
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
            native_control = isinstance(meta.get("route", {}).get("native_control"), dict)
            runner = meta.get("runner", {})
            valid = (bool(audit.get("checks")) and all(audit["checks"].values())
                     and not audit.get("source_errors")
                     and native_control
                     and (not offers if arm == ARMS[0] else
                          offers == {"B1_DETAIL", "B2_GIST"})
                     and (runner.get("role") == "C3_LANGUAGE" if arm == ARMS[0]
                          else runner.get("role") in ("B1_DETAIL", "B2_GIST")))
            scored = score_pair(fixture, audit.get("output", "")) if valid else {
                "a": False, "b": False, "correct": 0, "out_of": 2}
            return {"fixture": fixture["project"], "arm": arm,
                    "event_id": eid, "valid_native": bool(valid),
                    "native_control": native_control,
                    "body_offer_roles": sorted(offers),
                    "runner_role": runner.get("role"),
                    "final_output": audit.get("output", ""),
                    "duration_s": meta.get("duration_s"),
                    "score": scored, "raw_file": raw_path.name,
                    "native_process_releases": list(runtime.pool.release_history)}
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
        "arms": ARMS, "seed": SEED, "rows": [],
        "native_linux_only": True, "redmi_measured": False,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "comparative_step2_gate_promoted": False,
        "claim_limit": "Four-task pilot only, no STEP2 complementarity or mobile utility gate",
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
            for arm in ARMS:
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
        report["score_totals_out_of_8"] = totals
        report["pilot_gain"] = (valid and totals[ARMS[2]] >= totals[ARMS[1]] + 2
                                and totals[ARMS[2]] >= totals[ARMS[0]] + 2)
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
                      "score_totals_out_of_8": report.get("score_totals_out_of_8"),
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
