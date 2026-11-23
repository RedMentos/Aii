#!/usr/bin/env python3
"""Run117AG stdlib-only independent read-only original Run117AF native audit.

An audit PASS is not a fresh native inference. An original native RED stays
RED, including when the ZIP is structurally intact. No model imports.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from io import BytesIO
import argparse
import json
import re
import zipfile

HEAD = "f767480f5d79e8b8493f458e8579aefa78721ca5"
FIXTURE_SHA = "cbaa2e2f8e92c994a63f12fdb9ff165c5082dcd8a33ef2c7c311e512749f29cf"
IDS = ("Orion", "Petra", "Quill", "Rowan", "Sable", "Topaz")
ARMS = ("REAL_STORE_JEF_ONLY", "B1B2_JEF_CONTEXTOS")
STAGES = ("SOURCE", "DEPS", "PACK", "ZIP", "PREFLIGHT",
          "INSTALL_C3", "NATIVE", "VERIFY", "COMPILE", "PRIVACY", "DIFF")
POLICY = re.compile(
    r"Binding policy: budget (\d+) euros; deadline (\d+) days; local-only (true|false)\.")
OPTION = re.compile(
    r"Option ([AB]): cost (\d+) euros, duration (\d+) days, local (true|false)\.")


def require(ok, code):
    if not ok:
        raise ValueError(code)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY_RED")
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError("NONFINITE_JSON_RED")


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=_nonfinite)


def _oracle(row):
    m = POLICY.fullmatch(row["policy_span"])
    opts = list(OPTION.finditer(row["option_span"]))
    require(m is not None and len(opts) == 2
            and [o[1] for o in opts] == ["A", "B"], "FIXTURE_GRAMMAR_RED")
    budget, deadline, local = int(m[1]), int(m[2]), m[3] == "true"
    eligible = [(int(o[2]), o[1]) for o in opts
                if int(o[2]) <= budget and int(o[3]) <= deadline
                and (not local or o[4] == "true")]
    choice = min(eligible)[1] if eligible else "NONE"
    cost = next((x for x, label in eligible if label == choice), None)
    return {"choice":choice,
            "remaining":budget - cost if cost is not None else None}


def _score(raw, oracle):
    try:
        value = _json(raw)
        valid = (type(value) is dict
                 and set(value) == {"choice", "remaining"}
                 and type(value["choice"]) is str
                 and value["choice"] in ("A", "B", "NONE", "UNKNOWN")
                 and (value["remaining"] is None
                      or type(value["remaining"]) is int))
        return {"correct":int(valid and value == oracle),
                "valid_json":bool(valid), "parsed":value if valid else None}
    except (ValueError, TypeError, OverflowError, UnicodeError):
        return {"correct":0, "valid_json":False, "parsed":None}


def _read_sums(z):
    names = z.namelist()
    require(len(names) == len(set(names)), "OUTER_DUPLICATE_RED")
    require(z.testzip() is None, "OUTER_CRC_RED")
    lines = z.read("SHA256SUMS").decode().splitlines()
    seen = set()
    for line in lines:
        parts = line.split("  ./", 1)
        require(len(parts) == 2, "OUTER_SUM_FORMAT_RED")
        digest, path = parts
        require(path in names and path not in seen, "OUTER_SUM_PATH_RED")
        require(sha256(z.read(path)).hexdigest() == digest,
                "OUTER_SUM_HASH_RED")
        seen.add(path)
    require(seen == set(names) - {"SHA256SUMS"},
            "OUTER_SUM_COVERAGE_RED")
    return len(seen)


def audit(raw: bytes, *, expected_sha=None):
    if expected_sha is not None:
        require(sha256(raw).hexdigest() == expected_sha,
                "ORIGINAL_ARTIFACT_SHA_RED")
    with zipfile.ZipFile(BytesIO(raw)) as z:
        outer_count = _read_sums(z)
        require(z.read("HEAD.txt").decode().strip() == HEAD, "HEAD_RED")
        exits = {name:int(z.read(name + "_EXIT.txt").decode().strip())
                 for name in STAGES}
        result = _json(z.read("RESULT.json"))
        require(result["head"] == HEAD and result["seed"] == 1067
                and result["fixture_sha256"] == FIXTURE_SHA
                and result["exits"] == exits
                and result["step2_promoted"] is False
                and result["b3_promoted"] is False
                and result["jepa_weight"] == 0
                and result["redmi_measured"] is False
                and result["whole_system_complete"] is False,
                "WORKFLOW_RECEIPT_RED")
        phone = z.read("V13-Phone-Run117AF.zip")
        with zipfile.ZipFile(BytesIO(phone)) as n:
            require(n.testzip() is None, "PHONE_CRC_RED")
            names = n.namelist()
            require(len(names) == len(set(names)), "PHONE_DUPLICATE_RED")
            manifest = _json(n.read("V13-Phone/WORKSPACE_FILES.json"))
            files = manifest["files"]
            require(manifest["schema_version"] == 1 and len(files) >= 2200,
                    "PHONE_MANIFEST_RED")
            require(set("V13-Phone/" + p for p in files) ==
                    set(names) - {"V13-Phone/WORKSPACE_FILES.json"},
                    "PHONE_COVERAGE_RED")
            for path, digest in files.items():
                require(sha256(n.read("V13-Phone/" + path)).hexdigest() == digest,
                        "PHONE_HASH_RED:" + path)
            fixture_raw = n.read(
                "V13-Phone/docs/fixtures/RUN117AF_COMBINED_C3_NATIVE_SEED1067.json")
            require(sha256(fixture_raw).hexdigest() == FIXTURE_SHA,
                    "FROZEN_FIXTURE_SHA_RED")
            fixture = _json(fixture_raw)
        require(fixture["seed"] == 1067
                and fixture["arms"] == list(ARMS)
                and [r["id"] for r in fixture["rows"]] == list(IDS),
                "FROZEN_COHORT_RED")
        report = _json(z.read("NATIVE_CASE/report.json"))
        require(report["schema"] == "v13.run117af.combined_c3_native_seed1067.v1"
                and report["seed"] == 1067
                and report["fixture_sha256"] == FIXTURE_SHA
                and report["native_body_calls"] == 0
                and report["native_jef_calls"] == 0
                and report["native_c2_calls"] == 0
                and report["body_offers_synthetic"] is True
                and report["age0"] == "RECORD_ONLY"
                and report["step2_exit"] == "EVIDENCE_NOT_PASSING"
                and report["b3"] == "NO_PROMOTION"
                and report["body_jepa"] == "UNAVAILABLE"
                and report["jepa_weight"] == 0
                and report["redmi_measured"] is False
                and report["whole_system_complete"] is False
                and report["output_committed"] is False
                and report["tool_dispatches"] == 0
                and report["delivery_authority"] == 0
                and report["learning_authority"] == 0,
                "NATIVE_REPORT_NEGATIVE_GATES_RED")
        require(0 <= report["native_c3_calls"] <= 12
                and len(report["rows"]) <= 6, "NATIVE_COUNT_BOUNDS_RED")
        counts, scores = Counter(), Counter()
        for index, row in enumerate(report["rows"]):
            source = fixture["rows"][index]
            require(row["id"] == source["id"], "ROW_ORDER_RED")
            oracle = _oracle(source)
            require(source["oracle"] == oracle, "INDEPENDENT_ORACLE_RED")
            require(row.get("no_live_output") is True
                    and row.get("closed_fake_store_ok") is True,
                    "FAKE_STORE_OR_OUTPUT_RED")
            if row.get("status") == "RECORDED":
                require(row.get("closed_native_store_ok") is True,
                        "NATIVE_STORE_RED")
            require(len(row.get("arms", [])) <= 2, "ROW_ARMS_RED")
            for item in row["arms"]:
                arm = item["arm"]
                require(arm in ARMS, "ARM_ID_RED")
                if item.get("status") != "RECORDED":
                    continue
                require(item["native_final"] is True
                        and item["process_reaped"] is True,
                        "NATIVE_FINAL_REAP_RED")
                metrics = item["native_metrics"]
                require(metrics["status"] == "FINAL"
                        and metrics["actual_model"] ==
                        "LFM2.5-350M-QAD-Q4_0.gguf"
                        and metrics["role"] == "C3_LANGUAGE"
                        and metrics["input_message_count"] == 2
                        and metrics["CAN_TRAIN_BODY"] is False
                        and metrics["CAN_LATENT_INJECT"] is False,
                        "NATIVE_MODEL_METRICS_RED")
                messages = item["messages"]
                require([m["role"] for m in messages] == ["system", "user"],
                        "PROMPT_ROLES_RED")
                require(sha256(json.dumps(
                    messages, sort_keys=True,
                    separators=(",", ":")).encode()).hexdigest() ==
                    item["messages_sha256"], "PROMPT_SHA_RED")
                require(source["policy_span"] not in messages[0]["content"]
                        and source["option_span"] not in messages[0]["content"]
                        and '"oracle"' not in messages[1]["content"],
                        "PROMPT_ORACLE_OR_SYSTEM_LEAK_RED")
                payload = _json(messages[1]["content"])
                require(payload["source_role"] == "UNTRUSTED_EXACT_USER"
                        and payload["typed_jef_candidate"] == oracle
                        and payload["candidate_authority"] == 0
                        and payload["candidate_origin"] ==
                        "DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL",
                        "JEF_CANDIDATE_RED")
                for key, full, span in (("policy","prior","policy_span"),
                                        ("options","current","option_span")):
                    data = payload[key]
                    ref = data["source_ref"]
                    require(data["text"] == source[span]
                            and data["origin"] ==
                            "STORE_EXACT_USER_NOT_MODEL_QUOTE"
                            and ref["sha256"] ==
                            sha256(source[full].encode()).hexdigest()
                            and source[full][ref["char_start"]:ref["char_end"]] ==
                            data["text"], "SOURCE_REF_RED")
                if arm == ARMS[0]:
                    require("body_observations" not in payload
                            and "context_plan_packet_id" not in payload,
                            "BASE_BODY_LEAK_RED")
                else:
                    require(payload.get("body_hypotheses_are_facts") is False
                            and payload.get("body_model_quote_verified") is False
                            and payload.get("source_semantic_truth_authority") is False
                            and payload.get("context_plan_packet_id") ==
                            row.get("context_plan_packet_id")
                            and len(payload.get("body_observations", [])) == 2,
                            "COMBINED_BODY_BOUNDARY_RED")
                    for obs in payload["body_observations"]:
                        require(obs["hypothesis_authority"] ==
                                "MODEL_HYPOTHESIS_NOT_FACT"
                                and all(q["semantic_truth_authority"] is False
                                        for q in obs["verified_quotes"]),
                                "BODY_AUTHORITY_RED")
                recomputed = _score(item["output"], oracle)
                require(item["score"] == recomputed, "NATIVE_SCORE_FORGERY_RED")
                counts[arm] += 1
                scores[arm] += recomputed["correct"]
        complete = (report["status"] ==
                    "NATIVE_COMPLETE_EXPLORATORY_PAIRED_COMPARISON"
                    and set(exits.values()) == {0}
                    and report["native_c3_calls"] == 12
                    and len(report["rows"]) == 6
                    and dict(counts) == {a:6 for a in ARMS}
                    and all(row["status"] == "RECORDED"
                            and len(row["arms"]) == 2
                            for row in report["rows"]))
        if complete:
            require(report["scores"] == {a:scores[a] for a in ARMS}
                    and report["paired_difference"] ==
                    scores[ARMS[1]] - scores[ARMS[0]],
                    "NATIVE_TOTALS_RED")
        return {
            "status": ("INDEPENDENT_ORIGINAL_NATIVE_STRUCTURAL_PASS"
                       if complete else "INDEPENDENT_ORIGINAL_NATIVE_RED_PRESERVED"),
            "head": HEAD, "artifact_sha256":sha256(raw).hexdigest(),
            "outer_hashed_entries":outer_count,
            "phone_manifest_files":len(files),
            "native_c3_calls":report["native_c3_calls"],
            "recorded_by_arm":{a:counts[a] for a in ARMS},
            "scores":{a:scores[a] for a in ARMS},
            "original_status":report["status"],
            "original_exits":exits,
            "native_body_proven":False, "native_jef_proven":False,
            "native_c2_proven":False, "step2_promoted":False,
            "jepa_weight":0, "redmi_measured":False,
        }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("original_zip")
    p.add_argument("--expected-sha",required=True)
    args=p.parse_args()
    from pathlib import Path
    print(json.dumps(audit(Path(args.original_zip).read_bytes(),
                           expected_sha=args.expected_sha),sort_keys=True))


if __name__=="__main__":
    main()
