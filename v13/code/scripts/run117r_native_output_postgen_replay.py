"""Replay Run116 recorded native C3 text through new Run117P SHADOW guard.

This is a software replay with a fresh real SQLite Store and intentionally
synthetic, fallible Body observations. No native model executes in this run;
original Run116 output bytes are read-only, hash-pinned external evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time
import zipfile

from scripts import run117q_native_attribution_readonly as audit
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.test_run115k_realstore_bridge_review import WrongQuoteRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer
from v13.jef_b1b2_c3_role_postgen_shadow_candidate import evaluate, PASS

SCHEMA = "v13.run117r.native_output_replay_postgen.v1"


def replay(original_zip):
    original_zip = Path(original_zip)
    attribution = audit.audit(original_zip)  # exact outer ZIP, source and fixture pins
    with zipfile.ZipFile(original_zip) as outer:
        original = json.loads(outer.read("NATIVE_CASE/report.json"))
        with zipfile.ZipFile(outer.open("V13-Phone-Run116-Native.zip")) as phone:
            fixture = json.loads(phone.read(audit.FIXTURE_PATH))
    rows = []
    for case, native in zip(fixture["rows"], original["rows"]):
        if case["id"] != native["id"]:
            raise ValueError("COHORT_ID_RED")
        with tempfile.TemporaryDirectory() as d:
            runtime = WrongQuoteRuntime(Path(d) / "home")
            try:
                runtime.cfg.update(OVERRIDES)
                consumer = TopicPartitionOfferConsumer(runtime)
                prior = runtime.store.event(runtime.session, case["prior"])
                for role in ("B1_DETAIL", "B2_GIST"):
                    x = consumer.guarded_offer(
                        role, prior, 0, time.monotonic() + 30,
                        operator_opt_in=True)
                    if x.get("status") != "SHADOW_OFFER_PRODUCED":
                        raise ValueError("SYNTHETIC_PRIOR_OFFER_RED")
                current = runtime.store.event(runtime.session, case["current"])
                ids = {}
                for role in ("B1_DETAIL", "B2_GIST"):
                    x = consumer.guarded_offer(
                        role, current, 0, time.monotonic() + 30,
                        operator_opt_in=True)
                    if x.get("status") != "SHADOW_OFFER_PRODUCED":
                        raise ValueError("SYNTHETIC_CURRENT_OFFER_RED")
                    ids[role] = x["offer_packet_id"]
                before_actions = runtime.store.one(
                    "SELECT COUNT(*) AS n FROM actions")["n"]
                native_arms = {a["arm"]: a for a in native["arms"]}
                outcomes = {}
                for arm in audit.ARMS:
                    output = native_arms[arm]["output"]
                    guard = evaluate(runtime, prior, current, ids,
                                     lambda _, frozen=output: frozen,
                                     operator_opt_in=True, callback_opt_in=True)
                    if (guard.get("callback_invoked") is not True
                            or guard.get("source_rechecked") is not True
                            or guard.get("output_committed") is not False
                            or guard.get("tool_dispatches") != 0
                            or guard.get("delivery_authority") != 0
                            or guard.get("learning_authority") != 0
                            or guard.get("native_proof") is not False
                            or guard.get("redmi_measured") is not False):
                        raise ValueError("POSTGEN_AUTHORITY_OR_RECHECK_RED")
                    expected = (PASS if native_arms[arm]["score"]["correct"]
                                else "FORMATTER_CANDIDATE_MISMATCH_RED")
                    if guard["status"] != expected:
                        raise ValueError("REPLAY_EXPECTED_GATE_MISMATCH_RED")
                    outcomes[arm] = guard["status"]
                if runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"] != before_actions:
                    raise ValueError("REPLAY_ACTION_SIDE_EFFECT_RED")
                rows.append({"id": case["id"], "statuses": outcomes,
                             "synthetic_body_observers": True,
                             "native_inference_this_run": False})
            finally:
                runtime.close()
    counts = {arm: sum(r["statuses"][arm] == PASS for r in rows)
              for arm in audit.ARMS}
    if counts != attribution["scores"]:
        raise ValueError("REPLAY_SCORE_MISMATCH_RED")
    return {"schema": SCHEMA, "status": "ORIGINAL_NATIVE_OUTPUT_REPLAY_SHADOW_PASS",
            "original_sha256": audit.ORIGINAL_SHA256,
            "original_source_head": audit.SOURCE_HEAD,
            "rows": rows, "accepted_counts": counts,
            "native_inference_this_run": False,
            "synthetic_body_observers": True,
            "real_sqlite_store": True,
            "output_committed": False, "tool_dispatches": 0,
            "delivery_authority": 0, "learning_authority": 0,
            "jepa_weight": 0, "step2_promoted": False,
            "body_jepa_promoted": False, "redmi_measured": False,
            "whole_system_complete": False,
            "claim": "SOFTWARE_REPLAY_OF_ORIGINAL_NATIVE_C3_TEXT_NOT_NEW_NATIVE"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--original-zip", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = replay(args.original_zip)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"],
                      "accepted_counts": result["accepted_counts"],
                      "native_inference_this_run": False}, sort_keys=True))


if __name__ == "__main__":
    main()
