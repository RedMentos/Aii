"""Run109: six fresh STEP2 long/revised fixtures, software-only.

No model execution, no mutation of frozen Z2/Z2d fixtures or canonical gates.
Prereg: docs/proofs/continuation-20261028/RUN109_STEP2_FRESH_FIXTURES_PREREG.md
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

from scripts import step2_z2_timescale as z2

SCHEMA = "v13.run109.step2_fresh_long_revised_fixtures.v1"
LONG = (
    ("Atlas", "SPLIT", (130, 6, True), (60, 3, True), (85, 4, False)),
    ("Borealis", "RULE", (95, 4, False), (50, 3, False), (70, 2, True)),
    ("Cygnus", "SPLIT", (115, 5, True), (80, 4, True), (75, 6, True)),
)
REVISED = (
    ("Delta", "SPLIT", (80, 7, True), (100, 5, False), (65, 4, False), (60, 6, True)),
    ("Epsilon", "RULE", (120, 6, False), (90, 4, True), (75, 3, True), (55, 5, True)),
    ("Fornax", "SPLIT", (70, 8, True), (110, 3, False), (80, 2, False), (65, 4, False)),
)
FILLER = "Supplier review item {i} is informational only."


def fixtures():
    result = []
    for name, kind, latest, a, b in LONG:
        f = deepcopy(z2.episode(name, kind, latest, a, b))
        f["history"][0] = (
            f"Project {name} kickoff notes. "
            + " ".join(FILLER.format(i=i) for i in range(12))
            + " " + z2.rules_text(*latest))
        f["fixture_kind"] = "LONG"
        result.append(f)
    for name, kind, old, latest, a, b in REVISED:
        f = deepcopy(z2.episode(name, kind, latest, a, b))
        f["history"][0] = (
            f"Project {name} kickoff notes. Historical rules (superseded): "
            + z2.rules_text(*old))
        f["history"][1] = (
            f"Project {name} revision (later than kickoff). New current rules: "
            + z2.rules_text(*latest))
        f["fixture_kind"] = "REVISED"
        f["old_rules"] = {
            "budget": old[0], "deadline": old[1], "local_only": old[2]}
        result.append(f)
    return result


def canonical_sha256(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def inspect():
    cases = fixtures()
    ids = [f["id"] for f in cases]
    original_ids = [f["id"] for f in z2.FIXTURES]
    checks = {
        "six_distinct_new_projects": len(ids) == 6 and len(set(ids)) == 6
            and not set(ids).intersection(original_ids),
        "three_long_three_revised": sum(f["fixture_kind"] == "LONG" for f in cases) == 3
            and sum(f["fixture_kind"] == "REVISED" for f in cases) == 3,
        "long_rule_beyond_b2_excerpt_240": all(
            f["history"][0].index("Budget ") >= 240
            for f in cases if f["fixture_kind"] == "LONG"),
        "revised_old_then_new_rules": all(
            f["old_rules"] != f["rules"]
            and z2.rules_text(f["old_rules"]["budget"],
                              f["old_rules"]["deadline"],
                              f["old_rules"]["local_only"]) in f["history"][0]
            and z2.rules_text(f["rules"]["budget"],
                              f["rules"]["deadline"],
                              f["rules"]["local_only"]) in f["history"][1]
            for f in cases if f["fixture_kind"] == "REVISED"),
        "latest_rule_oracles_consistent": True,
        "frozen_z2_unchanged": original_ids == [f["id"] for f in z2.FIXTURES],
    }
    for f in cases:
        opts = f["oracle"]["options"]
        action, expected = z2.recipe(
            f["rules"]["budget"], f["rules"]["deadline"],
            f["rules"]["local_only"], [
                {"entity": o["entity"], "cost": o["cost"],
                 "days": o["days"], "local": o["local"]}
                for o in opts])
        if f["oracle"]["action"] != action or f["oracle"]["options"] != expected:
            checks["latest_rule_oracles_consistent"] = False
    return {
        "schema": SCHEMA, "status": "FRESH_FIXTURES_READY_SOFTWARE_ONLY"
            if all(checks.values()) else "FIXTURE_VALIDATION_RED",
        "evidence_kind": "DETERMINISTIC_SOFTWARE_NO_MODEL",
        "fixture_sha256": canonical_sha256(cases),
        "count": len(cases), "checks": checks, "fixtures": cases,
        "native_calls": 0, "model_called": False,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "redmi_measured": False, "whole_system_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    out = args.out.expanduser().resolve()
    if out.exists():
        raise FileExistsError("FRESH_EVIDENCE_FILE_REQUIRED")
    out.parent.mkdir(parents=True, exist_ok=True)
    report = inspect()
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False,
                              sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"],
                      "fixture_sha256": report["fixture_sha256"],
                      "checks": report["checks"]}, sort_keys=True))
    return 0 if report["status"] == "FRESH_FIXTURES_READY_SOFTWARE_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
