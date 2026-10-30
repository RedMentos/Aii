"""Run12M: disjoint 16-turn native C2/C3/B1/B2 answer utility pilot.

Reuses the exact frozen Run11V native turn, source-bound scorers and seed.
Review-only; no runtime, model, learning, STEP2 or age promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import traceback

from v13.cognition import scaffold_route
from v13.config import initialize
from v13.models import ModelManager
from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts.c2_strict_native_compat_run12k import classify

SCHEMA = "v13.c2_c3_body.paired.run12m.v1"
FIXTURE_SCHEMA = "v13.c2_c3_body.paired.run12m.fixture.v1"
FIXTURE_SHA256 = "c2739d0e3a0a7e9bda8383e145a9c7c2cfa26d3ab86a7052030ff32679884b48"
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "F_NATIVE_AUTO")
ARM_ORDER = tuple(ARMS[i:] + ARMS[:i] for i in range(4))
ROLES = ("needle", "language", "body", "gist")


def fixture_hash(cases):
    return hashlib.sha256(json.dumps(tuple(cases), sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def load_fixture(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases")
    if (data.get("schema") != FIXTURE_SCHEMA or data.get("seed") != 181
            or type(cases) is not list or len(cases) != 4
            or fixture_hash(cases) != FIXTURE_SHA256
            or frozen.SEED != 181):
        raise ValueError("RUN12M_FROZEN_FIXTURE_MISMATCH")
    names = set()
    old_prompts = {frozen.prompt(f) for f in frozen.FIXTURES}
    for f in cases:
        if type(f) is not dict or set(f) != {
            "project", "budget", "a", "a_cost", "a_days",
            "b", "b_cost", "b_days",
        }:
            raise ValueError("RUN12M_FIXTURE_SCHEMA")
        if (type(f["project"]) is not str or not f["project"]
                or f["project"] in names or f["a"] == f["b"]
                or any(type(f[k]) is not int for k in (
                    "budget", "a_cost", "a_days", "b_cost", "b_days"))
                or not (0 < f["a_cost"] < f["budget"]
                        and 0 < f["b_cost"] < f["budget"]
                        and f["a_days"] > 0 and f["b_days"] > 0)):
            raise ValueError("RUN12M_INVALID_SOURCE")
        names.add(f["project"])
        prompt = frozen.prompt(f)
        if prompt in old_prompts or scaffold_route(prompt) != "simple":
            raise ValueError("RUN12M_NONDISJOINT_OR_SCAFFOLD")
        for key in ("a", "b"):
            remainder = f["budget"] - f[key + "_cost"]
            if re.search(rf"(?<!\d){remainder}(?!\d)", prompt):
                raise ValueError("RUN12M_ANSWER_LEAK")
    return data


def summarize(rows):
    totals = {arm: sum(row.get("score", {}).get("correct", 0)
                       for row in rows if row.get("arm") == arm)
              for arm in ARMS}
    secondary = {arm: sum(row.get("secondary_score", {}).get("correct", 0)
                          for row in rows if row.get("arm") == arm)
                 for arm in ARMS}
    f_rows = [r for r in rows if r.get("arm") == "F_NATIVE_AUTO"]
    invocations = sum(r.get("flags", {}).get("native_c2_invocation") is True
                      for r in f_rows)
    strict_matches = sum(r.get("strict_admission", {}).get("matches") is True
                         for r in f_rows)
    selected = sum(r.get("strict_admission", {}).get("selected") is True
                   for r in f_rows)
    valid = bool(len(rows) == 16 and len(f_rows) == 4
                 and all(r.get("flags", {}).get("valid_native") is True
                         for r in rows)
                 and invocations == 4 and strict_matches == 4)
    signal = bool(valid and selected >= 1 and
                  totals["F_NATIVE_AUTO"] >=
                  max(totals[a] for a in ARMS[:3]) + 2)
    return {
        "status": "PILOT_COMPLETE_NO_GATE" if valid else "PILOT_PARTIAL_RED",
        "score_totals_out_of_8": totals,
        "secondary_totals_out_of_8": secondary,
        "native_c2_invocations": invocations,
        "native_c2_strict_matches": strict_matches,
        "native_c2_selected": selected,
        "all_native_structurally_valid": valid,
        "native_auto_utility_pilot_signal_not_gate": signal,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "redmi_measured": False,
        "whole_system_complete": False, "comparative_utility_proven": False,
        "jepa_weight": 0, "learning_mode": "RECORD_ONLY",
    }


def run(home, out, fixture_path):
    home, out = Path(home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_DIRECTORY_REQUIRED")
    fixture = load_fixture(fixture_path)
    out.mkdir(parents=True)
    (out / "raw").mkdir()
    (out / "preclose").mkdir()
    report = {
        "schema": SCHEMA, "seed": frozen.SEED,
        "fixture_sha256": FIXTURE_SHA256,
        "fixtures": fixture["cases"], "arms": ARMS,
        "arm_order": ARM_ORDER, "rows": [],
        "model_verification": {},
        "status": "INCOMPLETE",
    }
    try:
        cfg = initialize(home)
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg["latents_enabled"] or cfg.get("jepa_weight", 0) != 0):
            raise ValueError("BASE_NOT_AGE0")
        verified = ModelManager(home).verify(deep=True)
        if not all(verified.get(k, {}).get("ok") is True
                   and verified[k].get("hash_checked") is True for k in ROLES):
            raise ValueError("MODEL_PINS_UNVERIFIED")
        report["model_verification"] = {
            k: {"ok": True, "hash_checked": True} for k in ROLES}
        for i, f in enumerate(fixture["cases"]):
            for arm in ARM_ORDER[i]:
                index = len(report["rows"])
                try:
                    row = frozen.fresh_turn(home, cfg, f, arm, index, out)
                    if arm == "F_NATIVE_AUTO":
                        raw = json.loads((out / "raw" / f"{index:02d}_{arm}.json").read_text())
                        row["strict_admission"] = classify({
                            "route_info": raw["route_info"],
                            "route": raw["flags"]["route"],
                        })
                        (out / "raw" / f"{index:02d}_STRICT_ADMISSION.json").write_text(
                            json.dumps(row["strict_admission"], sort_keys=True,
                                       allow_nan=False) + "\n")
                except BaseException as exc:
                    traceback.print_exc()
                    row = {"index": index, "fixture": f["project"], "arm": arm,
                           "error_type": type(exc).__name__,
                           "error": str(exc)[:240],
                           "flags": {"valid_native": False,
                                     "native_c2_invocation": False},
                           "score": {"a": False, "b": False,
                                     "correct": 0, "out_of": 2}}
                    (out / "raw" / f"{index:02d}_{arm}.json").write_text(
                        json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                report["rows"].append(row)
                (out / "progress.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True,
                               allow_nan=False) + "\n")
        report.update(summarize(report["rows"]))
    except BaseException as exc:
        traceback.print_exc()
        report.update(summarize(report["rows"]))
        report["status"] = "PILOT_SETUP_ERROR"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:240]
    finally:
        (out / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True,
                       allow_nan=False) + "\n")
    print(json.dumps({
        "status": report["status"],
        "totals": report["score_totals_out_of_8"],
        "native_auto_signal": report["native_auto_utility_pilot_signal_not_gate"],
    }, sort_keys=True))
    return report["all_native_structurally_valid"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args()
    return 0 if run(a.home, a.out, a.fixture) else 2


if __name__ == "__main__":
    raise SystemExit(main())
