#!/usr/bin/env python3
"""Run509 fresh source-only B2 quote-focus experiment registration; NO native."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import run491_step2_heldout10 as old
import step2_z2_timescale as z2
from v13.agi.eligibility import recipe

SPECS = (
    ("Arbor", "SPLIT", (117, 5, True), (64, 4, True), (52, 6, False)),
    ("Bracken", "SPLIT", (91, 4, False), (82, 5, True), (70, 3, False)),
    ("Cobalt", "SPLIT", (106, 7, True), (78, 6, False), (88, 7, True)),
    ("Dahlia", "SPLIT", (89, 3, True), (90, 2, True), (85, 4, True)),
    ("Eclipse", "SPLIT", (135, 8, False), (99, 6, True), (102, 5, False)),
    ("Fjord", "SPLIT", (72, 6, True), (63, 6, True), (58, 5, False)),
    ("Garnet", "RULE", (125, 4, True), (103, 3, True), (111, 2, True)),
    ("Harbor", "RULE", (94, 7, False), (84, 8, True), (76, 6, False)),
    ("Iris", "DETAIL", (108, 5, True), (93, 5, True), (86, 4, False)),
    ("Juniper", "DETAIL", (82, 6, False), (71, 6, False), (68, 7, True)),
)
SEEDS = (41, 42, 43)
ARMS = ("BASE", "RULE_FOCUS")
FOCUS_QUESTION = (
    "Which earlier project rules apply: budget, deadline, and local-only "
    "requirement? Quote the exact earlier source sentences for each, or "
    "explicitly say they are absent. Do not infer values."
)
EXPECTED_ACTIONS = ("A", "B", "B", "NONE", "A", "A", "A", "B", "A", "A")
# Set to a literal after source-only CI recomputes the deterministic bytes.
EXPECTED_FIXTURE_SHA256 = "ba659a2d64771ec1d43c412c23e97314333af7f89040f5fb69b6e7bccab0c726"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def fixtures():
    result = [z2.episode(*spec) for spec in SPECS]
    names = [x[0] for x in SPECS]
    prior = {x[0] for x in old.SPECS} | {x[0] for x in z2.EPISODES}
    require(len(names) == len(set(names)) == 10 and not prior.intersection(names),
            "FRESH_FIXTURE_ID_COLLISION")
    require([f["id"] for f in result] == names and
            [f["type"] for f in result] == ["SPLIT"] * 6 + ["RULE"] * 2 + ["DETAIL"] * 2,
            "FRESH_FIXTURE_ROLE_DRIFT")
    require(tuple(f["oracle"]["action"] for f in result) == EXPECTED_ACTIONS,
            "FRESH_ORACLE_ACTION_DRIFT")
    for spec, row in zip(SPECS, result):
        name, kind, rules, a, b = spec
        opts = [{"entity": e, "cost": o[0], "days": o[1], "local": o[2]}
                for e, o in (("A", a), ("B", b))]
        action, options = recipe(*rules, opts)
        require(row["oracle"] == {"project": name, "action": action, "options": options},
                "FRESH_ORACLE_RECOMPUTE_DRIFT")
        require(len(row["history"]) == 3 and "Project Zenith" in row["history"][1],
                "FRESH_HISTORY_DRIFT")
        exact_rules = z2.rules_text(*rules)
        if kind in ("SPLIT", "RULE"):
            require(exact_rules in row["history"][0] and
                    exact_rules not in row["current"], "OLD_RULE_SOURCE_DRIFT")
        else:
            require(exact_rules not in row["history"][0] and
                    "budget " in row["current"] and
                    "local-only requirement:" in row["current"],
                    "DETAIL_NEGATIVE_CONTROL_DRIFT")
    h = digest(result)
    if EXPECTED_FIXTURE_SHA256 is not None:
        require(h == EXPECTED_FIXTURE_SHA256, "FRESH_FIXTURE_HASH_DRIFT")
    return result


def focus_packet():
    require(not re.search(r"\d", FOCUS_QUESTION) and
            not any(name in FOCUS_QUESTION for name, *_ in SPECS),
            "FOCUS_LEAKS_FIXTURE_VALUE_OR_ID")
    return {
        "question": FOCUS_QUESTION,
        "kind": "FILL_GAP",
        "target_role": "B2_GIST",
        "reason": "RUN509_PREREGISTERED_RULE_QUOTE_FOCUS",
        "authority": "EXECUTIVE_QUESTION_NOT_FACT",
    }


def registration():
    rows = fixtures()
    packet = focus_packet()
    require(SEEDS == (41, 42, 43) and ARMS == ("BASE", "RULE_FOCUS"),
            "FROZEN_ARM_SEED_DRIFT")
    require(set(SEEDS).isdisjoint(old.SEEDS), "PRIOR_SEED_COLLISION")
    return {
        "schema": "V13_RUN509_B2_FRESH_QUOTE_FOCUS_SOURCE_ONLY_V1",
        "status": "SOURCE_ONLY_NO_NATIVE_SHA_PENDING" if EXPECTED_FIXTURE_SHA256 is None
                  else "SOURCE_ONLY_FROZEN_NO_NATIVE",
        "fixtures": rows,
        "fixture_sha256": digest(rows),
        "fixture_hash_frozen": EXPECTED_FIXTURE_SHA256 is not None,
        "arms": list(ARMS), "seeds": list(SEEDS),
        "focus_packet": packet,
        "baseline_focus_packet": None,
        "planned_b2_offer_observations": 60,
        "primary_subset_types": ["SPLIT", "RULE"],
        "negative_control_type": "DETAIL",
        "model_sha256_expected_not_retrieved": dict(old.MODEL_SHA256),
        "runner_sha256_expected_not_retrieved": old.RUNNER_SHA256,
        "native_executed": False, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
        "claim_limit": "Fresh source-only registration; no B2 inference or STEP2 promotion.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    value = registration()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": value["status"],
                      "fixture_sha256": value["fixture_sha256"],
                      "planned_b2_offer_observations": 60,
                      "native_executed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
