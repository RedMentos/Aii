#!/usr/bin/env python3
"""Run511: frozen 2-fixture/12-observation B2 offer collector; native opt-in only.

This PR runs source-only tests and --plan, never --execute. Native use requires
a separate preregistered workflow after an exclusive heavy-owner check.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

import run509_b2_rule_quote_prereg as frozen
import step2_z2_timescale as z2

PAIRS = (
    ("Arbor", "Bracken"),
    ("Cobalt", "Dahlia"),
    ("Eclipse", "Fjord"),
    ("Garnet", "Harbor"),
    ("Iris", "Juniper"),
)
EXPECTED_PER_STAGE = 12


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def append_fsync(path, value):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def write_exclusive(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def plan(pair_index):
    require(type(pair_index) is int and 0 <= pair_index < len(PAIRS),
            "PAIR_INDEX_OUT_OF_RANGE")
    registration = frozen.registration()
    require(registration["fixture_hash_frozen"] is True and
            registration["fixture_sha256"] == frozen.EXPECTED_FIXTURE_SHA256,
            "FROZEN_RUN509_SHA_REQUIRED")
    names = [f["id"] for f in registration["fixtures"]]
    require(names == [name for pair in PAIRS for name in pair],
            "FROZEN_FIVE_PAIR_PARTITION_DRIFT")
    selected = PAIRS[pair_index]
    keys = [[name, arm, seed] for name in selected
            for arm in frozen.ARMS for seed in frozen.SEEDS]
    require(len(keys) == len({tuple(k) for k in keys}) == EXPECTED_PER_STAGE,
            "FROZEN_STAGE_KEY_DRIFT")
    return {
        "schema": "V13_RUN511_B2_OFFER_PAIR_STAGE_V1",
        "status": "SOURCE_ONLY_NO_NATIVE",
        "stage_id": f"p{pair_index:02d}",
        "pair_index": pair_index,
        "fixture_ids": list(selected),
        "row_keys": keys, "row_keys_sha256": sha(canonical(keys)),
        "expected_observations": EXPECTED_PER_STAGE,
        "run509_fixture_sha256": frozen.EXPECTED_FIXTURE_SHA256,
        "run509_registration_sha256": sha(canonical(registration)),
        "seeds": list(frozen.SEEDS), "arms": list(frozen.ARMS),
        "model_sha256_expected_not_retrieved":
            registration["model_sha256_expected_not_retrieved"],
        "runner_sha256_expected_not_retrieved":
            registration["runner_sha256_expected_not_retrieved"],
        "native_executed": False, "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL", "b3_l1": "FAIL",
        "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
        "redmi_measured": False,
    }


def source_slot_map(prep, current_event):
    require(len(prep["prior_events"]) == 3, "THREE_PRIOR_EVENTS_REQUIRED")
    refs = [x["source_ref"] for x in prep["prior_events"]] + [
        current_event["source_ref"]]
    slots = ("history0", "history1", "history2", "current")
    mapping = {}
    for slot, ref in zip(slots, refs):
        source_id = ref["source_id"]
        require(type(source_id) is str and source_id not in mapping,
                "SOURCE_ID_COLLISION")
        mapping[source_id] = slot
    return mapping


def collect_verified_quote_records(offer, store, fixture, mapping):
    require(offer["role"] == "B2_GIST" and
            offer["native_metrics"].get("status") == "FINAL",
            "B2_NATIVE_OFFER_NOT_FINAL")
    quotes = []
    raw_refs = offer["evidence_refs"]
    require(type(raw_refs) is list, "EVIDENCE_REFS_INVALID")
    for ref in raw_refs:
        require(type(ref) is dict and ref.get("source_id") in mapping,
                "UNREGISTERED_EVIDENCE_SOURCE")
        slot = mapping[ref["source_id"]]
        original = fixture["current"] if slot == "current" else (
            fixture["history"][int(slot[-1])])
        full_sha = sha(original.encode("utf-8"))
        require(ref.get("sha256") == full_sha, "EVIDENCE_SOURCE_HASH_DRIFT")
        text = store.read_source(ref)
        require(type(text) is str and bool(text) and text in original,
                "UNVERIFIED_SOURCE_EXCERPT")
        quotes.append({"source_slot": slot,
                       "source_sha256": full_sha, "text": text})
    return quotes


def native_config(installed, seed):
    from v13.config import initialize
    cfg = initialize(installed) | z2.ARMS["C"] | {
        "seed": seed, "learning_mode": "RECORD_ONLY",
        "teacher_enabled": False, "history_turns": 0,
        "memory_top_k": 0, "observer_mode": "off",
    }
    require(cfg["b2_control"] == "two_body" and
            cfg["b2_offer_body_state"] is False and
            cfg["offer_quote_context_chars"] == 200 and
            cfg["b1_recent_source_chars"] == 600,
            "FROZEN_SOURCE_WINDOW_CONFIG_DRIFT")
    return cfg


def native_pair_seed(harness, installed, work, fixture, seed, progress):
    from v13.runtime import Runtime
    base = work / f"base-{fixture['id']}-s{seed}"
    require(not base.exists() and not base.is_symlink(),
            "REFUSE_EXISTING_PREPARATION")
    cfg = native_config(installed, seed)
    append_fsync(progress, {"state": "PREP_STARTED",
                            "fixture": fixture["id"], "seed": seed,
                            "time_ns": time.time_ns()})
    prep = harness.prepare_base(base, installed, cfg, fixture)
    require(prep["status"] == "RECORDED" and
            prep["integrity_before_restart"] is True,
            "NATIVE_PRIOR_PREPARATION_FAILED")
    expected = harness.checkpoint_hashes(base)
    sealed = harness.seal_checkpoint(base, expected)
    append_fsync(progress, {"state": "PREP_SEALED",
                            "fixture": fixture["id"], "seed": seed,
                            "sealed_sha256": sealed["sha256"],
                            "time_ns": time.time_ns()})
    rows = []
    for arm in frozen.ARMS:
        home = work / f"arm-{fixture['id']}-s{seed}-{arm}"
        require(not home.exists() and not home.is_symlink(),
                "REFUSE_EXISTING_ARM_CLONE")
        clone = harness.clone_base(base, home, installed, expected, sealed)
        r = Runtime(home)
        row = None
        try:
            require(harness.same_persisted_state(
                harness.states(r), prep["state_before_restart"]),
                "PREPARED_STATE_CLONE_DRIFT")
            event = r.store.event(r.session, fixture["current"])
            mapping = source_slot_map(prep, event)
            deadline = time.monotonic() + cfg["observer_seconds"]
            focus = frozen.focus_packet() if arm == "RULE_FOCUS" else None
            offer = r.cognition.offer("B2_GIST", event, 0, deadline,
                                      focus=focus)
            quotes = collect_verified_quote_records(
                offer, r.store, fixture, mapping)
            row = {
                "fixture": fixture["id"], "arm": arm, "seed": seed,
                "status": "RECORDED",
                "source_history0_sha256":
                    sha(fixture["history"][0].encode("utf-8")),
                "quotes": quotes,
                "native_metrics": offer["native_metrics"],
                "model_revision": offer["model_revision"],
                "raw_offer_quotes": offer["offer"].get("quotes", []),
                "rejected_quotes": offer["rejected_quotes"],
                "evidence_refs": offer["evidence_refs"],
                "clone": clone,
                "oracle_visible_to_native": False,
                "native_executed": True,
            }
        finally:
            r.close()
            releases = list(r.pool.release_history)
        require(bool(releases) and
                all(release["process_reaped"] for release in releases),
                "NATIVE_PROCESS_RELEASE_NOT_PROVEN")
        row["process_releases"] = releases
        rows.append(row)
        append_fsync(progress, {"state": "OFFER_RECORDED",
                                "fixture": fixture["id"], "seed": seed,
                                "arm": arm, "time_ns": time.time_ns()})
        shutil.rmtree(home)
    shutil.rmtree(base)
    return rows


def execute(work, pair_index, installed_home):
    import run496_heldout10_native_pilot as pinned
    import step2_z2b_seeds as z2b
    work = Path(work)
    expected = plan(pair_index)
    plan_file = work / "RUN511_STAGE_PLAN.json"
    require(plan_file.is_file() and
            json.loads(plan_file.read_text(encoding="utf-8")) == expected,
            "RUN511_FROZEN_STAGE_PLAN_REQUIRED")
    installed = Path(installed_home).resolve()
    require(installed.is_dir(), "INSTALLED_HOME_REQUIRED")
    raw = work / "RUN511_OBSERVATIONS_RAW.jsonl"
    progress = work / "RUN511_PROGRESS.jsonl"
    result_path = work / "RUN511_STAGE_RESULT.json"
    preflight = work / "RUN511_INSTALLED_PREFLIGHT.json"
    require(not any(x.exists() or x.is_symlink()
                    for x in (raw, progress, result_path, preflight)),
            "REFUSE_NATIVE_RERUN_OR_PARTIAL")
    pinned_result = pinned.verify_installed(installed)
    write_exclusive(preflight, pinned_result)
    registration = frozen.registration()
    by_name = {f["id"]: f for f in registration["fixtures"]}
    harness = z2.harness()
    harness.FIXTURES = registration["fixtures"]
    rows = []
    with z2b.Patches(harness, False):
        for name in PAIRS[pair_index]:
            for seed in frozen.SEEDS:
                fresh = native_pair_seed(
                    harness, installed, work, by_name[name], seed, progress)
                for row in fresh:
                    append_fsync(raw, row)
                    rows.append(row)
    keys = [[r["fixture"], r["arm"], r["seed"]] for r in rows]
    require(keys == expected["row_keys"] and len(rows) == EXPECTED_PER_STAGE,
            "NATIVE_STAGE_COVERAGE_DRIFT")
    result = {
        "status": "RUN511_12_B2_NATIVE_OFFERS_STRUCTURALLY_VERIFIED_ONLY",
        "stage_id": expected["stage_id"],
        "row_keys_sha256": sha(canonical(keys)),
        "rows_verified": len(rows),
        "raw_observations_sha256": sha(raw.read_bytes()),
        "native_execution_performed": True,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
    }
    write_exclusive(result_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--pair-index", required=True, type=int,
                        choices=range(5))
    parser.add_argument("--installed-home", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    require(args.plan != args.execute, "EXACTLY_ONE_MODE_REQUIRED")
    if args.plan:
        require(args.installed_home is None, "PLAN_FORBIDS_INSTALLED_HOME")
        value = plan(args.pair_index)
        write_exclusive(args.work / "RUN511_STAGE_PLAN.json", value)
        print(json.dumps({"status": value["status"],
                          "stage_id": value["stage_id"],
                          "expected_observations": EXPECTED_PER_STAGE,
                          "native_executed": False}, sort_keys=True))
        return
    require(args.installed_home is not None, "NATIVE_REQUIRES_INSTALLED_HOME")
    print(json.dumps(execute(args.work, args.pair_index, args.installed_home),
                     sort_keys=True))


if __name__ == "__main__":
    main()
