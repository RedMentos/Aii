#!/usr/bin/env python3
"""Independent Run50 original native C3/C5/C6 DRAFT replay; preserve RED."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from scripts.run47_jef_c3_typed_receiver_verify import (
    MODELS, RUNNER_SHA, NEGATIVE, SYS_B, canonical, parse, score, sha)

FIXTURE_SHA = "7e05d20beb53653c86fe0ed83c12befba766ec0110be03ce9ea58569865e350c"
PROJECTS = ("Pine", "Orchid", "Slate", "Amber")


def require(condition, code):
    if not condition:
        raise ValueError("RUN50_REPLAY_" + code)


def replay(report_path, fixture_path):
    fixture_raw = Path(fixture_path).read_bytes()
    require(sha(fixture_raw) == FIXTURE_SHA, "FIXTURE_SHA")
    fixture = parse(fixture_raw)
    require(fixture.get("seed") == 443 and fixture.get("schema") ==
            "v13.run50.native_c3_c5_c6_draft_seed443.v1" and
            [f.get("id") for f in fixture.get("fixtures", [])] == list(PROJECTS), "FIXTURE")
    report = parse(Path(report_path).read_bytes())
    require(report.get("schema") == "v13.run50.native_c3_c5_c6_draft_result.v1"
            and report.get("fixture_sha256") == FIXTURE_SHA
            and report.get("seed") == 443 and report.get("registered") is True
            and report.get("negative_gates") == NEGATIVE, "REGISTRATION")
    binding = report.get("binding", {})
    require(binding.get("model_sha256") == MODELS and
            binding.get("runner_sha256") == RUNNER_SHA, "NATIVE_MODEL_RUNNER")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) <= 4 and
            [r.get("fixture") for r in rows] == list(PROJECTS[:len(rows)]), "ROW_ORDER")
    hashes = report.get("row_sha256")
    require(type(hashes) is dict and set(hashes) == {r["fixture"] for r in rows}, "ROW_MANIFEST")
    reasons = []
    correct = 0
    for row in rows:
        project = row["fixture"]
        f = next(f for f in fixture["fixtures"] if f["id"] == project)
        require(hashes[project] == sha(canonical(row)), "ROW_SHA")
        require(row.get("arm") == "B_JEF_TYPED_CANDIDATE" and
                row.get("oracle_visible_to_native") is False and
                row.get("prior_sha256") == sha(f["prior"].encode()) and
                row.get("current_sha256") == sha(f["current"].encode()), "SOURCE")
        if row.get("status") != "RECORDED":
            require(row.get("score", {}).get("correct") == 0, "RED_SCORE_ZERO")
            reasons.append(project + ":" + str(row.get("status")))
            continue
        prior, current = row.get("prior_source_ref"), row.get("current_source_ref")
        for ref, source in ((prior, f["prior"]), (current, f["current"])):
            require(type(ref) is dict and ref.get("sha256") == sha(source.encode())
                    and ref.get("char_start") == 0 and ref.get("char_end") == len(source)
                    and ref.get("modality") == "text", "SOURCE_REF")
        require(prior["source_id"] != current["source_id"], "SOURCE_ISOLATION")
        jef = row.get("jef_candidate", {})
        ref_digests = [sha(canonical(ref)) for ref in (prior, current)]
        require(jef.get("reason") == "EXACT_USER_SOURCE_RECIPE_SHADOW"
                and jef.get("status") == "SHADOW_NO_AUTHORITY"
                and jef.get("authority") == 0
                and jef.get("model_called") is False
                and jef.get("candidate") == f["oracle"]
                and jef.get("source_ref_sha256") == ref_digests
                and row.get("jef_matches_oracle") is True, "JEF")
        prompt = row.get("native_prompt")
        require(type(prompt) is list and len(prompt) == 2
                and prompt[0] == {"role": "system", "content": SYS_B}
                and prompt[1].get("role") == "user"
                and row.get("native_prompt_sha256") == sha(canonical(prompt)), "PROMPT")
        payload = parse(prompt[1]["content"])
        require(payload == {"current_source": f["current"],
                            "typed_jef_candidate": f["oracle"],
                            "source_ref_sha256": ref_digests,
                            "candidate_authority": 0}
                and "oracle" not in prompt[1]["content"], "PROMPT_PAYLOAD")
        require(row.get("native_c3_final") is True
                and row.get("native_c3_metrics", {}).get("status") == "FINAL"
                and row.get("processes_reaped") is True
                and type(row.get("process_releases")) is list
                and len(row["process_releases"]) > 0
                and all(x.get("process_reaped") is True for x in row["process_releases"]), "NATIVE_FINAL_REAP")
        native = row.get("native_answer", "")
        native_correct = score(native, f["oracle"])
        require(row.get("score", {}).get("correct") == native_correct, "NATIVE_SCORE")
        correct += native_correct
        event_id, session_id = row.get("current_event_id"), row.get("session_id")
        action_id, mid = row.get("c5_action_id"), row.get("c6_draft_id")
        action = row.get("c5_action", {})
        require(type(action_id) is str and action.get("id") == action_id
                and action.get("event_id") == event_id
                and action.get("kind") == "TEXT_REPORT"
                and action.get("status") == "DISPATCHED"
                and parse(action["expected"]) ==
                {"stream_owner": "C5_REPORT_BROKER", "type": "TEXT_REPORT"}, "C5_ACTION")
        packets = row.get("c5_packets")
        require(type(packets) is list and len(packets) == 2, "C5_PACKET_COUNT")
        pmap = {p["kind"]: p for p in packets}
        require(set(pmap) == {"ActionIntent", "CorollaryCopy"}, "C5_PACKET_KINDS")
        intent, copy = (parse(pmap[k]["payload"]) for k in ("ActionIntent", "CorollaryCopy"))
        generation = pmap["ActionIntent"]["generation_id"]
        require(pmap["CorollaryCopy"]["generation_id"] == generation
                and all(p["event_id"] == event_id for p in packets)
                and intent.get("packet_id") == pmap["ActionIntent"]["id"]
                and intent.get("producer_component") == "C5_REPORT_BROKER"
                and intent.get("brain_generation_id") == generation
                and intent.get("action_id") == action_id
                and intent.get("action_type") == "TEXT_REPORT"
                and intent.get("permission") == "local_text_only"
                and copy.get("packet_id") == pmap["CorollaryCopy"]["id"]
                and copy.get("producer_component") == "F3_SELF"
                and copy.get("brain_generation_id") == generation
                and copy.get("action_id") == action_id
                and copy.get("self_caused") is True
                and copy.get("expected") == parse(action["expected"])
                and action["corollary_id"] == pmap["CorollaryCopy"]["id"], "C5_PACKETS")
        draft = row.get("c6_draft_row", {})
        require(draft.get("id") == mid and draft.get("session_id") == session_id
                and draft.get("event_id") == event_id
                and draft.get("role") == "assistant" and draft.get("status") == "DRAFT"
                and draft.get("text") == native and parse(draft.get("metadata")) == {}, "C6_DRAFT")
        gate = row.get("draft_result", {})
        expected_digest = sha(canonical({"action": action_id,
                                         "intent": pmap["ActionIntent"]["id"],
                                         "copy": pmap["CorollaryCopy"]["id"],
                                         "event": event_id, "generation": generation}))
        require(gate.get("result") == "DRAFT_BOUND_SHADOW_NO_COMMIT"
                and gate.get("status") == "SHADOW_NO_AUTHORITY"
                and gate.get("delivery_authority") == 0
                and gate.get("live_enabled") is False
                and gate.get("user_approved") is False
                and gate.get("native_calls") == 0
                and gate.get("store_writes") == 0
                and gate.get("tool_dispatches") == 0
                and gate.get("draft_sha256") == sha(native.encode())
                and gate.get("matched_candidate_sha256") == sha(canonical(f["oracle"]))
                and gate.get("c5_binding_sha256") == expected_digest
                and row.get("draft_preflight_writes") == 0
                and row.get("draft_still_uncommitted") is True, "DRAFT_SHADOW")
    structural = len(rows) == 4 and not reasons
    signal = structural and correct >= 3 and report.get("installed_binding_unchanged") is True
    if structural:
        require(report.get("native_draft_copy_signal") is signal
                and report.get("status") ==
                ("NATIVE_DRAFT_COPY_SIGNAL_ONLY" if signal else "UTILITY_FAIL"), "AGGREGATE")
    else:
        require(report.get("status") in ("STRUCTURAL_RED", "RUNNING"), "STRUCTURAL_STATUS")
    return {"schema": "v13.run50.independent_replay.v1",
            "structural_valid": structural, "native_draft_copy_signal": signal,
            "native_correct": correct, "rows": len(rows), "reasons": reasons,
            "negative_gates": NEGATIVE,
            "scope": "LINUX_NATIVE_C3_C5_C6_DRAFT_ONLY_NO_OUTPUT_COMMIT_OR_AGE_PROMOTION"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    result = replay(args.report, args.fixture)
    print(json.dumps(result, sort_keys=True), flush=True)
    if not result["native_draft_copy_signal"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()