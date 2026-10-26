#!/usr/bin/env python3
"""Run510: exact source-quote coverage scorer; never verifies native provenance."""
import argparse
import hashlib
import json
from pathlib import Path

import run509_b2_rule_quote_prereg as frozen

SLOTS = ("history0", "history1", "history2", "current")
PRIMARY_TYPES = ("SPLIT", "RULE")
EXPECTED_ROWS = 60
EXPECTED_PRIMARY_PAIRS = 24
MIN_ABSOLUTE_GAIN_ROWS = 6


def require(ok, why):
    if not ok:
        raise ValueError(why)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def slot_text(fixture, slot):
    require(slot in SLOTS, "INVALID_SOURCE_SLOT")
    if slot == "current":
        return fixture["current"]
    return fixture["history"][int(slot[-1])]


def rule_fragments(fixture):
    rules = fixture["rules"]
    return (
        f"Budget {rules['budget']} euros.",
        f"Deadline {rules['deadline']} days.",
        f"Local-only requirement: {str(rules['local_only']).lower()}.",
    )


def score(registration, observations):
    expected = frozen.registration()
    require(type(registration) is dict and registration == expected and
            registration["fixture_hash_frozen"] is True and
            registration["fixture_sha256"] == frozen.EXPECTED_FIXTURE_SHA256,
            "RUN509_FROZEN_REGISTRATION_REQUIRED")
    require(type(observations) is list and len(observations) == EXPECTED_ROWS,
            "EXACT_SIXTY_OBSERVATIONS_REQUIRED")
    fixtures = {f["id"]: f for f in expected["fixtures"]}
    arms = tuple(expected["arms"])
    seeds = tuple(expected["seeds"])
    expected_keys = {(fid, arm, seed) for fid in fixtures
                     for arm in arms for seed in seeds}
    seen = set()
    primary = {(arm, seed): [] for arm in arms for seed in seeds}
    by_fixture = {(arm, fid): [] for arm in arms for fid in fixtures}
    quotes_verified = 0
    all_three = {}
    for row in observations:
        require(type(row) is dict and
                set(row) == {"fixture", "arm", "seed", "status",
                             "source_history0_sha256", "quotes"},
                "OBSERVATION_SCHEMA_INVALID")
        key = (row["fixture"], row["arm"], row["seed"])
        require(key in expected_keys and key not in seen and
                type(row["seed"]) is int, "UNKNOWN_DUPLICATE_OR_INVALID_ROW")
        seen.add(key)
        fixture = fixtures[key[0]]
        require(row["status"] == "RECORDED" and
                row["source_history0_sha256"] ==
                digest_bytes(fixture["history"][0].encode("utf-8")),
                "OBSERVATION_SOURCE_HASH_DRIFT")
        quotes = row["quotes"]
        require(type(quotes) is list, "QUOTE_LIST_REQUIRED")
        verified_old_quotes = []
        for quote in quotes:
            require(type(quote) is dict and
                    set(quote) == {"source_slot", "source_sha256", "text"},
                    "QUOTE_SCHEMA_INVALID")
            slot = quote["source_slot"]
            source = slot_text(fixture, slot)
            value = quote["text"]
            require(type(value) is str and bool(value) and
                    quote["source_sha256"] == digest_bytes(source.encode("utf-8")) and
                    value in source, "FABRICATED_OR_UNVERIFIED_QUOTE")
            quotes_verified += 1
            if slot == "history0":
                verified_old_quotes.append(value)
        complete = all(any(fragment in quote for quote in verified_old_quotes)
                       for fragment in rule_fragments(fixture))
        if fixture["type"] == "DETAIL":
            require(not complete, "DETAIL_FALSE_PRIOR_RULE_COVERAGE")
        else:
            primary[(key[1], key[2])].append(int(complete))
        by_fixture[(key[1], key[0])].append(int(complete))
        all_three[key] = int(complete)
    require(seen == expected_keys, "INCOMPLETE_OR_OVERLAPPING_MATRIX")
    require(all(len(primary[(arm, seed)]) == 8 for arm in arms for seed in seeds),
            "PRIMARY_SUBSET_DRIFT")
    require(all(len(by_fixture[(arm, fid)]) == 3
                for arm in arms for fid in fixtures), "PER_FIXTURE_SEED_DRIFT")
    paired = [all_three[(fid, "RULE_FOCUS", seed)] -
              all_three[(fid, "BASE", seed)]
              for fid, fixture in fixtures.items()
              if fixture["type"] in PRIMARY_TYPES for seed in seeds]
    require(len(paired) == EXPECTED_PRIMARY_PAIRS, "PRIMARY_PAIRED_COUNT_DRIFT")
    focus = sum(primary[("RULE_FOCUS", seed)][i]
                for seed in seeds for i in range(8))
    base = sum(primary[("BASE", seed)][i]
               for seed in seeds for i in range(8))
    require(focus - base == sum(paired), "PAIRED_AGGREGATION_DRIFT")
    return {
        "schema": "V13_RUN510_STRICT_SOURCE_QUOTE_METRIC_V1",
        "status": "SOURCE_ONLY_QUOTE_MATRIX_VALIDATED_DIAGNOSTIC_ONLY",
        "registered_fixture_sha256": frozen.EXPECTED_FIXTURE_SHA256,
        "observations": EXPECTED_ROWS,
        "source_quote_records_verified": quotes_verified,
        "primary_paired_observations": EXPECTED_PRIMARY_PAIRS,
        "primary_all_three_rule_quotes": {"BASE": base, "RULE_FOCUS": focus},
        "primary_focus_minus_base_rows": focus - base,
        "primary_focus_minus_base_fraction": (focus - base) / EXPECTED_PRIMARY_PAIRS,
        "preregistered_descriptive_gain_reached":
            focus - base >= MIN_ABSOLUTE_GAIN_ROWS,
        "per_seed": {
            str(seed): {arm: sum(primary[(arm, seed)]) for arm in arms}
            for seed in seeds
        },
        "per_fixture": {
            fid: {arm: sum(by_fixture[(arm, fid)]) for arm in arms}
            for fid in fixtures
        },
        "native_evidence_verified": False,
        "false_prior_rule_assertions_in_summaries_evaluated": False,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "claim_limit": "Literal source-substring scorer only; future native evidence_refs and summary assertions require independent review.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = score(json.loads(args.registration.read_text()),
                   json.loads(args.observations.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True,
                                indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"],
                      "observations": result["observations"],
                      "native_evidence_verified": False}, sort_keys=True))


if __name__ == "__main__":
    main()
