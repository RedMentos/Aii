"""Independent read-only P0X 600-call native source-arm raw auditor.

No import of original generator/executor/scorer. Requires externally registered
exact evidence SHA256 pins; cannot attest that a model physically ran.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

SCHEMA = "v13.p0x.native600_independent_raw_audit.v1"
HEAD = "4a98235e7e17c0dfd0e9a9cc3cb8478f99d9abac"
FIXTURE = "ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e"
MODEL = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
BASE_RAW = "79be6584d465b0fc3ccd33294d882a41bb1990920f3098ed39203b7aef7d18a1"
BASE_SCORE = "7c603158c6d821592d5777d46bb4723503f74c063c5c30fcc0f72fe2720b836e"
ARMS = ("b1_only", "b2_only", "both_exact", "shuffled")
STAGES = ("SOURCE", "PARENT_BASELINE_DOWNLOAD", "PARENT_SOURCE_DOWNLOAD",
          "PARENT_MOCK_DOWNLOAD", "PARENT_VERIFY", "RESOURCE", "DEPS",
          "COMPILE", "FOCUSED", "INSTALL", "NATIVE", "VERIFY", "PRIVACY", "DIFF")
LABELS = ("A", "B", "NONE", "UNKNOWN", "UNPARSEABLE")


def need(ok, reason):
    if not ok:
        raise ValueError("P0X_600_INDEPENDENT_" + reason + "_RED")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def safe_file(root, name):
    need(type(name) is str and not name.startswith("/")
         and ".." not in Path(name).parts, "UNSAFE_PATH")
    p = root / name
    need(p.is_file() and not p.is_symlink()
         and p.resolve().is_relative_to(root.resolve()), "FILE_PATH")
    return p


def check_sha_list(root):
    counts = {}
    for sub in (".", "parent-baseline", "parent-source", "parent-mock"):
        directory = root / sub
        lines = safe_file(directory, "SHA256SUMS.txt").read_text().splitlines()
        need(len(lines) > 0, "EMPTY_CHECKSUMS")
        seen = set()
        for line in lines:
            need("  " in line, "CHECKSUM_FORMAT")
            digest, rel = line.split("  ", 1)
            rel = rel.removeprefix("./")
            need(re.fullmatch(r"[0-9a-f]{64}", digest) is not None
                 and rel not in seen, "CHECKSUM_DUPLICATE")
            seen.add(rel)
            need(sha(safe_file(directory, rel).read_bytes()) == digest,
                 "CHECKSUM_MISMATCH")
        counts[sub] = len(lines)
    return counts


def source_id(s):
    m = re.match(r"^Project (P0X[0-9A-F]{16})\b", s)
    return m.group(1) if m else None


def split(message, label):
    marker = "\n\n" + label + ":\n"
    need(message.count(marker) == 1, "SOURCE_DELIMITER")
    return message.split(marker, 1)


def strict_action(output):
    if type(output) is not str:
        return "UNPARSEABLE"
    try:
        parsed = json.loads(output)
    except (ValueError, TypeError):
        return "UNPARSEABLE"
    if type(parsed) is dict and set(parsed) == {"action"} and parsed["action"] in LABELS[:4]:
        return parsed["action"]
    return "UNPARSEABLE"


def load_pinned(root, name, digest):
    raw = safe_file(root, name).read_bytes()
    need(sha(raw) == digest, "EVIDENCE_HASH")
    return json.loads(raw)


def verify(root, pins):
    root = Path(root).resolve()
    need(root.is_dir() and safe_file(root, "HEAD.txt").read_text().strip() == HEAD,
         "HEAD")
    need(type(pins) is dict and pins.get("schema") ==
         "v13.p0x.native600_external_pins.v1", "PINS_SCHEMA")
    required = ("raw_sha256", "score_sha256", "comparison_sha256",
                "inputs_sha256", "answers_sha256")
    need(all(re.fullmatch(r"[0-9a-f]{64}", pins.get(k, "")) is not None
             for k in required), "PINS_MISSING")
    counts = check_sha_list(root)
    for stage in STAGES:
        need(safe_file(root, stage + "_EXIT.txt").read_text().strip() == "0",
             "STAGE_" + stage)
    need("CLEAN" in safe_file(root, "PRIVACY_RAW.log").read_text(),
         "PRIVACY")
    for directory, expected in (("parent-baseline", "577366b0059d8367f5c5446afc62b0d524d35768"),
                                ("parent-source", "a86405e9ee897db09cb046f269ca59529ccbd604"),
                                ("parent-mock", "90d904c9c8fe144cad23c516a18006a3c78a5b18")):
        need(safe_file(root, directory + "/HEAD.txt").read_text().strip() == expected,
             "PARENT_IDENTITY")
    base_raw = safe_file(root, "parent-baseline/evidence/RAW.json").read_bytes()
    base_score = safe_file(root, "parent-baseline/evidence/SCORE.json").read_bytes()
    need(sha(base_raw) == BASE_RAW and sha(base_score) == BASE_SCORE,
         "BASELINE_PIN")
    base = json.loads(base_score)
    need(base["per_arm"]["c3_only"] == {"exact": 50, "wrong_committed": 100,
                                       "unknown": 0, "unparseable": 0},
         "BASELINE_SCORE")
    receipt = json.loads(safe_file(root, "evidence/RECEIPT.json").read_bytes())
    raw = load_pinned(root, "evidence/RAW.json", pins["raw_sha256"])
    score = load_pinned(root, "evidence/SCORE.json", pins["score_sha256"])
    comparison = load_pinned(root, "evidence/COMPARISON.json", pins["comparison_sha256"])
    inputs = load_pinned(root, "evidence/INPUTS.json", pins["inputs_sha256"])
    answers = load_pinned(root, "evidence/ANSWERS.json", pins["answers_sha256"])
    need(all(receipt.get(k) == pins[k] for k in required), "RECEIPT_HASH")
    need(receipt.get("schema") == "v13.p0x.c3_600_native_source_arms.v1"
         and receipt.get("status") == "RECORDED_LINUX_NATIVE_P0X_C3_SOURCE_ABLATIONS_NO_GATE"
         and receipt.get("expected_calls") == receipt.get("recorded_calls") == 600
         and receipt.get("baseline_raw_sha256") == BASE_RAW
         and receipt.get("baseline_score_sha256") == BASE_SCORE
         and receipt.get("fixture_sha256") == FIXTURE
         and receipt.get("model_sha256_before") == receipt.get("model_sha256_after") == MODEL
         and receipt.get("runner_sha256_before") == receipt.get("runner_sha256_after") == RUNNER
         and receipt.get("seed") == 13 and receipt.get("c3_sampling") == "off"
         and receipt.get("weight_updates") is False and receipt.get("age_authority") == 0
         and receipt.get("jepa_weight") == 0 and receipt.get("process_reaped") is True
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False, "RECEIPT")
    need(raw.get("status") == receipt["status"]
         and raw.get("fixture_sha256") == FIXTURE
         and raw.get("baseline_raw_sha256") == BASE_RAW
         and len(raw.get("rows", [])) == len(inputs) == 600
         and len(answers) == 150, "RAW_COUNT")
    answer_map = {}
    for a in answers:
        need(type(a) is dict and set(a) == {"id", "oracle_action"}
             and a["id"] not in answer_map
             and re.fullmatch(r"P0X[0-9A-F]{16}", a["id"]) is not None
             and a["oracle_action"] in ("A", "B", "NONE"), "ANSWER_SHAPE")
        answer_map[a["id"]] = a["oracle_action"]
    need(Counter(answer_map.values()) == {"A": 50, "B": 50, "NONE": 50},
         "ANSWER_BALANCE")
    messages = {}
    scores = {arm: {"exact": 0, "wrong_committed": 0, "unknown": 0,
                    "unparseable": 0} for arm in ARMS}
    labels = {arm: {key: 0 for key in LABELS} for arm in ARMS}
    for i, (row, plan) in enumerate(zip(raw["rows"], inputs)):
        id_, arm = row.get("id"), row.get("arm")
        need(id_ == plan.get("id") and arm == plan.get("arm")
             and id_ in answer_map and arm == ARMS[i % 4],
             "ROW_IDENTITY")
        need(type(plan.get("messages")) is list and len(plan["messages"]) == 2
             and plan["messages"][0]["role"] == "system"
             and plan["messages"][1]["role"] == "user", "MESSAGE_SHAPE")
        user = plan["messages"][1]["content"]
        need(user.startswith("Current request:\nProject " + id_ + ". ")
             and not any(x in user for x in ("oracle_action", "sheet_index",
                                            "rule_index", "max_first", "max_second")),
             "MODEL_ORACLE_LEAK")
        need(row.get("input_sha256") == sha(canonical(plan["messages"]))
             and row.get("schema_sha256") == sha(canonical(plan["schema"]))
             and row.get("status") == "FINAL"
             and row.get("model_called") is True
             and row.get("native_calls") == 1 and row.get("seed") == 13
             and row.get("model_sha256") == MODEL
             and type(row.get("metrics")) is dict
             and row["metrics"].get("status") == "FINAL"
             and type(row.get("duration_s")) in (int, float)
             and math.isfinite(row["duration_s"])
             and 0 <= row["duration_s"] <= 100, "NATIVE_ROW_BINDING")
        key = (id_, arm)
        need(key not in messages, "DUPLICATE_ARM")
        messages[key] = user
        label = strict_action(row.get("output"))
        truth = answer_map[id_]
        kind = ("exact" if label == truth else
                "wrong_committed" if label in ("A", "B", "NONE") else
                "unknown" if label == "UNKNOWN" else "unparseable")
        scores[arm][kind] += 1
        labels[arm][label] += 1
        detail = score["details"][i]
        need(detail == {"id_sha256": sha(id_.encode()), "arm": arm,
                        "parsed": label, "oracle": truth}, "DETAIL_BINDING")
    need(len(messages) == 600 and all(sum(s.values()) == 150 for s in scores.values()),
         "ARM_COVERAGE")
    need(score.get("per_arm") == scores and score.get("output_labels") == labels,
         "SCORE_RECOMPUTE")
    for id_ in answer_map:
        both = messages[(id_, "both_exact")]
        part, b1 = split(both, "B1 exact source")
        current, b2 = split(part, "B2 exact source")
        need(source_id(b1) == source_id(b2) == id_, "BOTH_SOURCE_IDENTITY")
        need(messages[(id_, "b1_only")] == current + "\n\nB1 exact source:\n" + b1,
             "B1_SEPARATION")
        need(messages[(id_, "b2_only")] == current + "\n\nB2 exact source:\n" + b2,
             "B2_SEPARATION")
        first, foreign = split(messages[(id_, "shuffled")], "FOREIGN B1 source")
        need(first == current + "\n\nB2 exact source:\n" + b2
             and source_id(foreign) in answer_map
             and source_id(foreign) != id_, "FOREIGN_SEPARATION")
        need(foreign == split(messages[(source_id(foreign), "both_exact")],
                             "B1 exact source")[1], "FOREIGN_COHORT")
    both_exact = scores["both_exact"]["exact"]
    need(comparison.get("baseline_exact") == 50
         and comparison.get("both_exact") == both_exact
         and comparison.get("improvement") == both_exact - 50
         and comparison.get("threshold") == 15
         and comparison.get("threshold_met") == (both_exact - 50 >= 15)
         and comparison.get("both_exceeds_singles") ==
             all(both_exact > scores[a]["exact"] for a in ("b1_only", "b2_only"))
         and comparison.get("shuffled_wrong_committed") ==
             scores["shuffled"]["wrong_committed"], "COMPARISON_RECOMPUTE")
    need(all(score.get(k) == value for k, value in
             (("canonical_gate_pass", False), ("step2_status", "UTILITY_FAIL"),
              ("b3_status", "FAIL"), ("body_jepa_status", "UNAVAILABLE"),
              ("lp3_status", "FAIL"), ("jepa_weight", 0),
              ("redmi_measured", False), ("whole_system_complete", False))),
         "NEGATIVE_GATES")
    return {"schema": SCHEMA,
            "status": "ORIGINAL_600_RAW_INDEPENDENTLY_RECHECKED_NO_GATE",
            "source_head": HEAD, "checksums": counts,
            "native_rows": 600, "per_arm": scores, "labels": labels,
            "comparison": comparison, "canonical_gate_pass": False,
            "step2_status": "UTILITY_FAIL", "redmi_measured": False,
            "whole_system_complete": False,
            "claim_limit": "Public synthetic C3 source-view ablation, no B1/B2 native generated source or causal cache-order control"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--pins-json", required=True, type=Path)
    args = ap.parse_args(argv)
    print(json.dumps(verify(args.root, json.loads(args.pins_json.read_bytes())),
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
