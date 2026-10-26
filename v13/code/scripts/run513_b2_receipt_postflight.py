#!/usr/bin/env python3
"""Run513: read-only structural audit of one frozen Run511/512 B2 native stage.

This checks receipt consistency, not whether a model actually ran or learned.
A separate verified GitHub Actions native execution is needed for native claims.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

import run509_b2_rule_quote_prereg as frozen
import run511_b2_offer_collector as collector

SLOTS = ("history0", "history1", "history2", "current")
GATES = {
    "canonical_gate_pass": False,
    "step2_exit": "UTILITY_FAIL",
    "b3_l1": "FAIL",
    "body_jepa": "UNAVAILABLE",
    "jepa_weight": 0,
    "redmi_measured": False,
}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def no_constant(value):
    raise ValueError("NONFINITE_JSON_" + value)


def load_json(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "REQUIRED_FILE_MISSING")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=no_constant)


def load_jsonl(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "REQUIRED_JSONL_MISSING")
    raw = path.read_bytes()
    require(raw and raw.endswith(b"\n"), "INCOMPLETE_JSONL")
    lines = raw.decode("utf-8").splitlines()
    require(all(line.strip() for line in lines), "EMPTY_JSONL_LINE")
    return [json.loads(line, parse_constant=no_constant) for line in lines], raw


def sha_string(value):
    return type(value) is str and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def check_gates(row):
    require(all(k in row and type(row[k]) is type(v) and row[k] == v
                for k, v in GATES.items()), "NEGATIVE_GATE_DRIFT")


def check_slots(row, fixture):
    slots = row.get("source_slots")
    require(type(slots) is list and len(slots) == 4,
            "FOUR_SOURCE_SLOT_RECORDS_REQUIRED")
    originals = list(fixture["history"]) + [fixture["current"]]
    ids = []
    by_slot = {}
    for slot, original, rec in zip(SLOTS, originals, slots):
        require(type(rec) is dict and
                set(rec) == {"source_slot", "source_id", "source_sha256",
                             "char_start", "char_end", "source_text"} and
                rec["source_slot"] == slot and
                type(rec["source_id"]) is str and bool(rec["source_id"]) and
                rec["source_text"] == original and
                rec["source_sha256"] == digest(original.encode("utf-8")) and
                type(rec["char_start"]) is int and rec["char_start"] == 0 and
                type(rec["char_end"]) is int and rec["char_end"] == len(original),
                "SOURCE_SLOT_RECORD_DRIFT")
        ids.append(rec["source_id"])
        by_slot[slot] = rec
    require(len(set(ids)) == 4, "DUPLICATE_SOURCE_ID")
    require(row.get("source_history0_sha256") ==
            by_slot["history0"]["source_sha256"],
            "HISTORY0_HASH_DRIFT")
    return by_slot


def check_quotes(row, by_slot):
    refs = row.get("evidence_refs")
    quotes = row.get("quotes")
    require(type(refs) is list and type(quotes) is list and
            len(refs) == len(quotes), "QUOTE_REF_COUNT_MISMATCH")
    source_ids = {v["source_id"]: v for v in by_slot.values()}
    slots_by_id = {v["source_id"]: k for k, v in by_slot.items()}
    for ref, quote in zip(refs, quotes):
        require(type(ref) is dict and type(quote) is dict and
                set(quote) == {"source_slot", "source_sha256", "text"},
                "QUOTE_REF_SCHEMA_DRIFT")
        sid = ref.get("source_id")
        require(type(sid) is str and sid in source_ids,
                "QUOTE_UNKNOWN_SOURCE_ID")
        slot = slots_by_id[sid]
        source = source_ids[sid]
        start, end = ref.get("char_start"), ref.get("char_end")
        require(type(start) is int and type(end) is int and
                0 <= start < end <= len(source["source_text"]) and
                ref.get("sha256") == source["source_sha256"] and
                ref.get("modality") == "text" and
                quote["source_slot"] == slot and
                quote["source_sha256"] == source["source_sha256"] and
                type(quote["text"]) is str and bool(quote["text"]) and
                quote["text"] == source["source_text"][start:end],
                "QUOTE_EVIDENCE_OFFSET_OR_TEXT_DRIFT")


def check_prep(work, fixture, seed, preflight, rows):
    prep = load_json(work / f"RUN511_PREP_{fixture['id']}_s{seed}.json")
    require(prep.get("status") == "CLOSED_PREPARATION_SOURCE_ONLY" and
            prep.get("fixture") == fixture["id"] and
            type(prep.get("seed")) is int and prep["seed"] == seed and
            prep.get("model_sha256") == preflight["model_sha256"] and
            prep.get("runner_sha256") == preflight["runner_sha256"] and
            prep.get("runtime_library_sha256") ==
            preflight["runtime_library_sha256"] and
            type(prep.get("checkpoint_hashes")) is dict and
            bool(prep["checkpoint_hashes"]) and
            sha_string(prep.get("sealed_sha256")),
            "PREPARATION_RECEIPT_DRIFT")
    prior = prep.get("prior_event_source_refs")
    require(type(prior) is list and len(prior) == 3,
            "THREE_PRIOR_REFS_REQUIRED")
    for row in rows:
        for ref, slot in zip(prior, row["source_slots"][:3]):
            require(type(ref) is dict and
                    ref.get("source_id") == slot["source_id"] and
                    ref.get("sha256") == slot["source_sha256"] and
                    type(ref.get("char_start")) is int and
                    ref["char_start"] == slot["char_start"] and
                    type(ref.get("char_end")) is int and
                    ref["char_end"] == slot["char_end"] and
                    ref.get("modality") == "text",
                    "PREPARATION_SOURCE_REF_DRIFT")
    return prep


def audit(work, pair_index):
    work = Path(work)
    plan = collector.plan(pair_index)
    require(load_json(work / "RUN511_STAGE_PLAN.json") == plan,
            "FROZEN_STAGE_PLAN_DRIFT")
    preflight = load_json(work / "RUN511_INSTALLED_PREFLIGHT.json")
    require(type(preflight) is dict and
            preflight.get("model_sha256") ==
            frozen.registration()["model_sha256_expected_not_retrieved"] and
            preflight.get("runner_sha256") ==
            frozen.registration()["runner_sha256_expected_not_retrieved"] and
            type(preflight.get("runtime_library_sha256")) is dict and
            bool(preflight["runtime_library_sha256"]) and
            preflight.get("native_executed") is False,
            "INSTALLED_PREFLIGHT_RECEIPT_DRIFT")
    rows, raw = load_jsonl(work / "RUN511_OBSERVATIONS_RAW.jsonl")
    require(len(rows) == 12, "EXACT_TWELVE_ROWS_REQUIRED")
    keys = []
    metric_rows = []
    fixtures = {f["id"]: f for f in frozen.fixtures()}
    for row in rows:
        require(type(row) is dict and
                type(row.get("fixture")) is str and
                row["fixture"] in fixtures and
                row.get("arm") in frozen.ARMS and
                type(row.get("seed")) is int and
                row["seed"] in frozen.SEEDS and
                row.get("status") == "RECORDED" and
                row.get("native_executed") is True and
                row.get("oracle_visible_to_native") is False and
                type(row.get("model_revision")) is str and
                bool(row["model_revision"]) and
                type(row.get("native_metrics")) is dict and
                row["native_metrics"].get("status") == "FINAL" and
                type(row.get("raw_offer_quotes")) is list and
                type(row.get("rejected_quotes")) is int and
                row["rejected_quotes"] >= 0 and
                type(row.get("process_releases")) is list and
                bool(row["process_releases"]) and
                all(type(x) is dict and x.get("process_reaped") is True
                    for x in row["process_releases"]),
                "NATIVE_ROW_LIFECYCLE_DRIFT")
        fixture = fixtures[row["fixture"]]
        by_slot = check_slots(row, fixture)
        check_quotes(row, by_slot)
        keys.append([row["fixture"], row["arm"], row["seed"]])
        metric_rows.append({
            "fixture": row["fixture"], "arm": row["arm"],
            "seed": row["seed"], "status": "RECORDED",
            "source_history0_sha256": row["source_history0_sha256"],
            "quotes": row["quotes"],
        })
    require(keys == plan["row_keys"] and len(set(map(tuple, keys))) == 12,
            "ROW_KEYS_ORDER_OR_COVERAGE_DRIFT")
    progress, _ = load_jsonl(work / "RUN511_PROGRESS.jsonl")
    require(len(progress) == 24, "PROGRESS_EVENT_COUNT_DRIFT")
    n = 0
    for fixture_name in plan["fixture_ids"]:
        fixture = fixtures[fixture_name]
        for seed in frozen.SEEDS:
            group = rows[n:n+2]
            prep = check_prep(work, fixture, seed, preflight, group)
            expected = [
                ("PREP_STARTED", None), ("PREP_SEALED", None),
                ("OFFER_RECORDED", "BASE"),
                ("OFFER_RECORDED", "RULE_FOCUS"),
            ]
            for (state, arm), event in zip(expected, progress[n*2:n*2+4]):
                require(type(event) is dict and
                        event.get("state") == state and
                        event.get("fixture") == fixture_name and
                        type(event.get("seed")) is int and
                        event["seed"] == seed and
                        type(event.get("time_ns")) is int and
                        event["time_ns"] > 0 and
                        (arm is None or event.get("arm") == arm) and
                        (state != "PREP_SEALED" or
                         event.get("sealed_sha256") == prep["sealed_sha256"]),
                        "PROGRESS_ORDER_OR_BINDING_DRIFT")
            n += 2
    result = load_json(work / "RUN511_STAGE_RESULT.json")
    require(type(result) is dict and
            result.get("status") ==
            "RUN511_12_B2_NATIVE_OFFERS_STRUCTURALLY_VERIFIED_ONLY" and
            result.get("stage_id") == plan["stage_id"] and
            type(result.get("rows_verified")) is int and
            result["rows_verified"] == 12 and
            result.get("row_keys_sha256") == digest(canonical(keys)) and
            result.get("raw_observations_sha256") == digest(raw) and
            result.get("native_execution_performed") is True,
            "STAGE_RESULT_OR_RAW_HASH_DRIFT")
    check_gates(result)
    report = {
        "schema": "V13_RUN513_B2_RECEIPT_POSTFLIGHT_V1",
        "status": "SOURCE_REF_STRUCTURAL_RECEIPT_PASS_NOT_NATIVE_PROOF",
        "stage_id": plan["stage_id"],
        "row_keys_sha256": digest(canonical(keys)),
        "raw_observations_sha256": digest(raw),
        "source_bound_rows": 12,
        "exact_quote_ref_records": sum(len(row["quotes"]) for row in rows),
        "metric_rows_sha256": digest(canonical(metric_rows)),
        "native_execution_independently_confirmed": False,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "claim_limit": "Structural audit of supplied files only; verify actual native Actions and original model bytes separately.",
    }
    return report, metric_rows


def write_exclusive(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as out:
        out.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             indent=2, allow_nan=False) + "\n")
        out.flush()
        os.fsync(out.fileno())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--pair-index", type=int, required=True, choices=range(5))
    args = p.parse_args()
    report, metric_rows = audit(args.work, args.pair_index)
    write_exclusive(args.work / "RUN513_VERIFIED_METRIC_ROWS.json", metric_rows)
    write_exclusive(args.work / "RUN513_POSTFLIGHT.json", report)
    print(json.dumps({"status": report["status"], "source_bound_rows": 12,
                      "native_execution_independently_confirmed": False},
                     sort_keys=True))


if __name__ == "__main__":
    main()
