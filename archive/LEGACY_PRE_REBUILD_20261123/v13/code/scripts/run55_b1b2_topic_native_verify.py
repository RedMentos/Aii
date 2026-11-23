#!/usr/bin/env python3
"""Independent Run55 corrected B1/B2 native topic partition structural verifier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from v13.common import dumps
from scripts.run52_b1b2_cross_turn_native import load_fixture, FIXTURE_SHA256, ROLES
from scripts.run47_jef_c3_typed_receiver_native import NEGATIVE

B1_SHA = "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1"
B2_SHA = "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ROLE_FILES = {"B1_DETAIL": "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
              "B2_GIST": "Qwen3.5-0.8B-Q4_0.gguf"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(report_path, fixture_path):
    data = load_fixture(fixture_path)
    fixtures = {f["id"]:f for f in data["fixtures"]}
    report = json.loads(Path(report_path).read_text())
    errors = []
    def require(condition, reason):
        if not condition:
            errors.append(reason)
    require(report.get("schema") == "v13.run55.b1b2_topic_native_report.v1", "schema")
    require(report.get("seed") == 479 and report.get("fixture_sha256") == FIXTURE_SHA256, "fixture_pin")
    require(report.get("claim") == "ORIGINAL_RUN52_HARBOR_WILLOW_CORRECTIVE_STRUCTURAL_REPLAY_NOT_UTILITY", "claim")
    require(report.get("negative_gates") == NEGATIVE, "negative_gates")
    require(report.get("installed_binding_unchanged") is True, "binding_unchanged")
    binding = report.get("binding") or {}
    require((binding.get("model_sha256") or {}).get("B1_DETAIL") == B1_SHA, "b1_sha")
    require((binding.get("model_sha256") or {}).get("B2_GIST") == B2_SHA, "b2_sha")
    require(binding.get("runner_sha256") == RUNNER_SHA, "runner_sha")
    rows = report.get("rows")
    require(type(rows) is list and len(rows) == 1, "row_count")
    if type(rows) is not list or len(rows) != 1:
        return {"status":"STRUCTURAL_RED","errors":errors}
    row = rows[0]
    require((report.get("row_sha256") or {}).get("Harbor_Willow") == sha(dumps(row).encode()), "row_sha")
    require(row.get("schema") == "v13.run55.b1b2_topic_native_row.v1", "row_schema")
    require(row.get("status") == "RECORDED", "row_status")
    require(row.get("native_model") is True and row.get("semantic_utility_claim") is False, "claim_boundary")
    require(row.get("negative_gates") == NEGATIVE, "row_negative_gates")
    require(row.get("no_live_output") is True, "no_live_output")
    require(row.get("controls_no_packets") is True
            and (row.get("off_control") or {}).get("status") == "OFF"
            and (row.get("ambiguous_control") or {}).get("status") == "TOPIC_SCOPE_RED"
            and (row.get("replay_control") or {}).get("status") == "STALE_REPLAY_NO_OFFER"
            and row.get("post_replay_packet_count") == row.get("pre_native_packet_count",0)+16,
            "negative_controls")
    require(row.get("native_process_count",0) >= 8
            and row.get("processes_reaped") is True
            and (row.get("closed_store_audit") or {}).get("ok") is True, "process_sqlite")
    events = row.get("events") or {}
    for project in ("Harbor","Willow"):
        for phase in ("prior","current"):
            e = events.get(project+"_"+phase) or {}
            source = fixtures[project][phase]
            ref = e.get("source_ref") or {}
            require(e.get("text_sha256") == sha(source.encode())
                    and ref.get("sha256") == sha(source.encode())
                    and ref.get("char_start") == 0
                    and ref.get("char_end") == len(source), "event_source_"+project+"_"+phase)
    offers = row.get("offers")
    require(type(offers) is list and len(offers) == 8, "offer_count")
    if type(offers) is not list or len(offers) != 8:
        return {"status":"STRUCTURAL_RED","errors":errors}
    by_key = {(x.get("role"),x.get("project"),x.get("phase")):x for x in offers}
    captures = row.get("captures") or {}
    require(len({x.get("capture_key") for x in offers}) == 8, "capture_key_uniqueness")
    keys = {}
    for role in ROLES:
        for project in ("Harbor","Willow"):
            prior = by_key.get((role,project,"prior")) or {}
            current = by_key.get((role,project,"current")) or {}
            pk = prior.get("partition_key_sha256")
            require(type(pk) is str and len(pk) == 64
                    and current.get("partition_key_sha256") == pk, "partition_resume_"+role+project)
            keys[(role,project)] = pk
            for phase,entry in (("prior",prior),("current",current)):
                label = role+":"+project+"_"+phase
                offer = entry.get("offer") or {}
                metrics = offer.get("native_metrics") or {}
                require(entry.get("status") == "SHADOW_OFFER_PRODUCED"
                        and entry.get("topic_partitioned") is True
                        and metrics.get("status") == "FINAL"
                        and metrics.get("actual_model") == ROLE_FILES[role], "native_"+label)
                query = entry.get("query") or {}
                require(offer.get("event_id") == entry.get("event_id")
                        and offer.get("role") == role
                        and offer.get("query_packet_id") == query.get("packet_id")
                        and query.get("event_id") == entry.get("event_id")
                        and query.get("target_role") == role
                        and (offer.get("provenance") or [None])[0]
                        == events[project+"_"+phase]["source_ref"],
                        "persisted_offer_query_binding_"+label)
                refs = query.get("context_source_refs") or []
                expected = [] if phase == "prior" else [
                    events[project+"_prior"]["source_ref"]["source_id"]]
                require([r.get("source_id") for r in refs] == expected, "query_refs_"+label)
                require(query.get("target_role") == role, "query_role_"+label)
                capture = captures.get(entry.get("capture_key")) or {}
                messages = capture.get("messages") or []
                require(len(messages) == 2 and capture.get("messages_sha256")
                        == sha(dumps(messages).encode()) if messages else False, "prompt_sha_"+label)
                if len(messages) != 2:
                    continue
                try:
                    payload = json.loads(messages[1]["content"])
                except Exception:
                    errors.append("prompt_json_"+label)
                    continue
                if role == "B1_DETAIL":
                    expected_hypothesis = "" if phase == "prior" else (
                        (prior.get("offer") or {}).get("offer") or {}).get("summary","")[:240]
                    require(payload.get("prior_hypothesis") == expected_hypothesis,
                            "b1_prior_hypothesis_"+label)
                    recent = payload.get("recent_source") or []
                    require((not recent) if phase == "prior" else (
                        len(recent) == 1
                        and recent[0]["exact_source_excerpt"] in fixtures[project]["prior"]),
                        "b1_recent_source_"+label)
                else:
                    earlier = payload.get("earlier_context") or []
                    require((not earlier) if phase == "prior" else (
                        len(earlier) == 1
                        and earlier[0]["exact_source_excerpt"] in fixtures[project]["prior"]),
                        "b2_earlier_context_"+label)
    require(len(set(keys.values())) == 4, "role_topic_partition_collision")
    require(report.get("status") == "TOPIC_PARTITION_NATIVE_CORRECTIVE_STRUCTURAL_ONLY", "report_status")
    return {"status":"STRUCTURAL_PASS" if not errors else "STRUCTURAL_RED",
            "errors":errors,
            "claim":"ORIGINAL_RUN52_TWO_PROJECT_NATIVE_STATE_ISOLATION_NOT_UTILITY"}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--fixture",type=Path,required=True)
    a=p.parse_args()
    result=verify(a.report,a.fixture)
    print(json.dumps(result,sort_keys=True))
    if result["status"] != "STRUCTURAL_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
