"""Read-only independent posthoc audit of original P0X 150-call C3 native evidence.

No import of generator, native executor, model manager, or native verifier.
No native execution. Only original artifact/parent hashes accepted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
import zipfile

SCHEMA = "v13.p0x.native150_independent_raw_review.v1"
HEAD = "577366b0059d8367f5c5446afc62b0d524d35768"
ZIP_SHA = "f115796e45e14d1fd1ff86b241222666ab8023b734a391dfa244ae26ccf833c4"
FIXTURE = "ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e"
MODEL = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
RAW_SHA = "79be6584d465b0fc3ccd33294d882a41bb1990920f3098ed39203b7aef7d18a1"
SCORE_SHA = "7c603158c6d821592d5777d46bb4723503f74c063c5c30fcc0f72fe2720b836e"
INPUTS_SHA = "f8ddddb51bc92a73cf3224489073f21a101f0ec61e1a665a26497097ae9abbf5"
ANSWERS_SHA = "9c6f32638ee455e083467ed04201f5f9ddf657105977066907ba1cf93efe2a71"
STAGES = ("SOURCE", "PARENT_SOURCE_DOWNLOAD", "PARENT_MOCK_DOWNLOAD",
          "PARENT_VERIFY", "RESOURCE", "DEPS", "COMPILE", "FOCUSED",
          "INSTALL", "NATIVE", "VERIFY", "PRIVACY", "DIFF")
ACTIONS = ("A", "B", "NONE", "UNKNOWN")


def require(ok, why):
    if not ok:
        raise ValueError("P0X_NATIVE_INDEPENDENT_" + why + "_RED")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def safe_file(root, rel):
    require(type(rel) is str and not rel.startswith("/")
            and ".." not in Path(rel).parts, "UNSAFE_PATH")
    target = root / rel
    require(target.is_file() and not target.is_symlink()
            and target.resolve().is_relative_to(root.resolve()), "FILE_PATH")
    return target


def checksums(root):
    totals = {}
    for directory in (root, root / "parent-source", root / "parent-mock"):
        file = safe_file(root, str((directory / "SHA256SUMS.txt").relative_to(root)))
        lines = file.read_text().splitlines()
        require(len(lines) > 0, "CHECKSUM_EMPTY")
        seen = set()
        for line in lines:
            require("  " in line, "CHECKSUM_FORMAT")
            digest, relative = line.split("  ", 1)
            relative = relative.removeprefix("./")
            require(relative not in seen and re.fullmatch(r"[0-9a-f]{64}", digest),
                    "CHECKSUM_DUPLICATE")
            seen.add(relative)
            require(sha(safe_file(directory, relative).read_bytes()) == digest,
                    "CHECKSUM_MISMATCH")
        totals[str(directory.relative_to(root))] = len(lines)
    return totals


def read_json(root, rel, expected_sha):
    data = safe_file(root, rel).read_bytes()
    require(sha(data) == expected_sha, "EVIDENCE_HASH")
    return json.loads(data)


def audit(root):
    root = Path(root).resolve()
    require(root.is_dir() and (root / "HEAD.txt").read_text().strip() == HEAD,
            "HEAD")
    totals = checksums(root)
    for stage in STAGES:
        require(safe_file(root, stage + "_EXIT.txt").read_text().strip() == "0",
                "STAGE_" + stage)
    require("CLEAN" in safe_file(root, "PRIVACY_RAW.log").read_text(),
            "PRIVACY")
    require(safe_file(root, "parent-source/HEAD.txt").read_text().strip()
            == "9cd2a432193232d9ee807f26604bda1efd323d45", "PARENT_SOURCE")
    require(safe_file(root, "parent-mock/HEAD.txt").read_text().strip()
            == "f1ebd717a7377e3176e21065043d7ef381d2c839", "PARENT_MOCK")
    receipt = json.loads(safe_file(root, "evidence/RECEIPT.json").read_bytes())
    raw = read_json(root, "evidence/RAW.json", RAW_SHA)
    score = read_json(root, "evidence/SCORE.json", SCORE_SHA)
    inputs = read_json(root, "evidence/INPUTS.json", INPUTS_SHA)
    answers = read_json(root, "evidence/ANSWERS.json", ANSWERS_SHA)
    for name, digest in (("raw_sha256", RAW_SHA), ("score_sha256", SCORE_SHA),
                         ("inputs_sha256", INPUTS_SHA), ("answers_sha256", ANSWERS_SHA)):
        require(receipt.get(name) == digest, "RECEIPT_HASH")
    require(receipt.get("status") == "RECORDED_LINUX_NATIVE_P0X_C3_ONLY_BASELINE_NO_GATE"
            and receipt.get("schema") == "v13.p0x.c3_150_native_baseline.v1"
            and receipt.get("expected_calls") == receipt.get("recorded_calls") == 150
            and receipt.get("fixture_sha256") == FIXTURE
            and receipt.get("model_sha256_before") == receipt.get("model_sha256_after") == MODEL
            and receipt.get("runner_sha256_before") == receipt.get("runner_sha256_after") == RUNNER
            and receipt.get("seed") == 13 and receipt.get("c3_sampling") == "off"
            and receipt.get("weight_updates") is False
            and receipt.get("age_authority") == 0 and receipt.get("jepa_weight") == 0
            and receipt.get("process_reaped") is True
            and receipt.get("redmi_measured") is False
            and receipt.get("canonical_gate_pass") is False
            and receipt.get("whole_system_complete") is False,
            "RECEIPT")
    require(raw.get("status") == receipt["status"] and raw.get("fixture_sha256") == FIXTURE
            and len(raw.get("rows", [])) == len(inputs) == len(answers) == 150,
            "RAW_COUNT")
    observed = {"A": 0, "B": 0, "NONE": 0, "UNKNOWN": 0}
    truth = {"A": 0, "B": 0, "NONE": 0}
    exact = wrong = unknown = unparseable = 0
    for row, plan, answer in zip(raw["rows"], inputs, answers):
        require(row.get("id") == plan.get("id") == answer.get("id")
                and re.fullmatch(r"P0X[0-9A-F]{16}", row["id"]) is not None,
                "ROW_IDENTITY")
        require(type(plan.get("messages")) is list and len(plan["messages"]) == 2
                and plan["messages"][0]["role"] == "system"
                and plan["messages"][1]["role"] == "user", "MESSAGE_SHAPE")
        user = plan["messages"][1]["content"]
        require(user.startswith("Current request:\nProject " + row["id"] + ". ")
                and not any(term in user for term in ("B1 exact source", "B2 exact source",
                   "FOREIGN B1 source", "oracle_action", "sheet_index", "rule_index")),
                "MODEL_SOURCE_LEAK")
        require(row.get("input_sha256") == sha(canonical(plan["messages"]))
                and row.get("status") == "FINAL" and row.get("model_called") is True
                and row.get("native_calls") == 1 and row.get("seed") == 13
                and row.get("model_sha256") == MODEL
                and type(row.get("metrics")) is dict
                and row["metrics"].get("status") == "FINAL"
                and type(row.get("duration_s")) in (int, float)
                and math.isfinite(row["duration_s"])
                and 0 <= row["duration_s"] <= 100, "ROW_NATIVE_BINDING")
        label = "UNPARSEABLE"
        try:
            parsed = json.loads(row["output"])
            if type(parsed) is dict and set(parsed) == {"action"} and parsed["action"] in ACTIONS:
                label = parsed["action"]
        except (ValueError, TypeError):
            pass
        truth_label = answer["oracle_action"]
        require(truth_label in truth, "ANSWER_LABEL")
        truth[truth_label] += 1
        if label == "UNPARSEABLE":
            unparseable += 1
        else:
            observed[label] += 1
            if label == truth_label:
                exact += 1
            elif label == "UNKNOWN":
                unknown += 1
            else:
                wrong += 1
    require(truth == {"A": 50, "B": 50, "NONE": 50}, "ORACLE_BALANCE")
    require(observed == {"A": 0, "B": 0, "NONE": 150, "UNKNOWN": 0}
            and (exact, wrong, unknown, unparseable) == (50, 100, 0, 0),
            "OBSERVED_NEGATIVE_RESULT")
    require(score.get("oracle_headroom") == 100
            and score.get("per_arm", {}).get("c3_only", {}) ==
            {"exact": 50, "wrong_committed": 100, "unknown": 0, "unparseable": 0}
            and score.get("canonical_gate_pass") is False
            and score.get("step2_status") == "UTILITY_FAIL"
            and score.get("b3_status") == "FAIL"
            and score.get("body_jepa_status") == "UNAVAILABLE"
            and score.get("lp3_status") == "FAIL"
            and score.get("jepa_weight") == 0
            and score.get("redmi_measured") is False
            and score.get("whole_system_complete") is False,
            "SCORE_NEGATIVE_GATES")
    return {"schema": SCHEMA, "status": "ORIGINAL_NATIVE_RAW_INDEPENDENTLY_RECHECKED_NO_GATE",
            "source_head": HEAD, "checksums": totals, "native_rows": 150,
            "model_output_labels": observed, "oracle_labels": truth,
            "exact": exact, "wrong_committed": wrong, "unknown": unknown,
            "unparseable": unparseable, "oracle_headroom": 100,
            "claim_limit": "Original Linux-native C3-only, 150 NONE outputs; no source-use or complementarity proof",
            "step2_status": "UTILITY_FAIL", "canonical_gate_pass": False,
            "redmi_measured": False, "whole_system_complete": False}


def audit_zip(path):
    path = Path(path)
    require(sha(path.read_bytes()) == ZIP_SHA, "ZIP_PIN")
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, "ZIP_CRC")
        for member in archive.infolist():
            require(not member.filename.startswith("/") and
                    ".." not in Path(member.filename).parts, "ZIP_PATH")
        with tempfile.TemporaryDirectory() as tmp:
            archive.extractall(tmp)
            return audit(tmp)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--root", type=Path)
    group.add_argument("--zip", type=Path)
    args = parser.parse_args(argv)
    result = audit_zip(args.zip) if args.zip else audit(args.root)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
