"""Independent read-only verification of exported P0X prompts and answer keys.

No imports from the P0X generator. Software/structural evidence only.
Usage: python -m scripts.p0x_export_independent_verify --directory OUT
       --fixture-sha256 PINNED_FIXTURE_SHA256
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

SCHEMA = "v13.p0x.150_export_independent_audit.v1"
ARMS = {"c3_only", "b1_only", "b2_only", "both_exact", "shuffled"}
ID = r"P0X[0-9A-F]{16}"


def require(condition, reason):
    if not condition:
        raise ValueError("P0X_AUDIT_" + reason + "_RED")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_lines(raw):
    result = []
    for line in raw.splitlines():
        require(bool(line), "BLANK_LINE")
        obj = json.loads(line)
        require(type(obj) is dict, "NONOBJECT")
        result.append(obj)
    return result


def source_id(source):
    match = re.match(r"^Project (" + ID + r")\b", source)
    return match.group(1) if match else None


def split_exact(message, label):
    marker = "\n\n" + label + ":\n"
    require(message.count(marker) == 1, "SOURCE_DELIMITER")
    return message.split(marker, 1)


def parse_both(message, project):
    first, b1 = split_exact(message, "B1 exact source")
    current, b2 = split_exact(first, "B2 exact source")
    require(source_id(b1) == project and source_id(b2) == project, "SOURCE_IDENTITY")
    current_domain = re.search(r" archived ([a-z ]+) policy and latest option sheet", current)
    policy_domain = re.search(r" archived ([a-z ]+) policy\.", b2)
    sheet_domain = re.search(r" latest ([a-z ]+) option sheet\.", b1)
    require(current_domain is not None and policy_domain is not None and sheet_domain is not None
            and current_domain.group(1) == policy_domain.group(1) == sheet_domain.group(1),
            "DOMAIN_IDENTITY")
    maximums = re.findall(r"Maximum [^:]+: (\d+) [^.]+\.", b2)
    required = re.findall(r"Required [^:]+: (true|false)\.", b2)
    require(len(maximums) == 2 and len(required) == 1, "POLICY_PARSE")
    limit1, limit2 = map(int, maximums)
    need_flag = required[0] == "true"
    eligible = []
    for name in "AB":
        found = re.findall(r"Option " + name + r": ([^.]+)\.", b1)
        require(len(found) == 1, "OPTION_PARSE")
        numbers = re.findall(r"\b\d+\b", found[0])
        flags = re.findall(r"\b(true|false)\b", found[0])
        require(len(numbers) == 2 and len(flags) == 1, "OPTION_FIELDS")
        value1, value2 = map(int, numbers)
        if value1 <= limit1 and value2 <= limit2 and (not need_flag or flags[0] == "true"):
            eligible.append((value1, value2, name))
    return (min(eligible)[2] if eligible else "NONE"), current, b1, b2


def verify(directory, expected_fixture_sha256, *, inputs_sha256=None, answers_sha256=None):
    root = Path(directory)
    require(root.is_dir() and not root.is_symlink(), "DIRECTORY")
    require(re.fullmatch(r"[0-9a-f]{64}", expected_fixture_sha256) is not None,
            "EXTERNAL_PIN")
    raw_manifest = (root / "manifest.json").read_bytes()
    manifest = json.loads(raw_manifest)
    require(manifest["schema"] == "v13.p0x.150_source_holdout.v1.export.v1"
            and manifest["fixture_sha256"] == expected_fixture_sha256,
            "MANIFEST_PIN")
    require(manifest["status"] == "P0X_SOURCE_ONLY_NO_NATIVE_NO_GATE"
            and manifest["canonical_gate_pass"] is False
            and manifest["whole_system_complete"] is False
            and manifest["redmi_measured"] is False
            and manifest["step2_status"] == "UTILITY_FAIL"
            and manifest["jepa_weight"] == 0, "NEGATIVE_GATES")
    require((inputs_sha256 is None) == (answers_sha256 is None), "PARTIAL_EXPORT_PIN")
    if inputs_sha256 is not None:
        require(re.fullmatch(r"[0-9a-f]{64}", inputs_sha256) is not None
                and re.fullmatch(r"[0-9a-f]{64}", answers_sha256) is not None,
                "EXPORT_PIN_FORMAT")
        require(manifest["sha256"]["inputs.jsonl"] == inputs_sha256
                and manifest["sha256"]["answers.jsonl"] == answers_sha256,
                "EXTERNAL_EXPORT_PIN")
    require(manifest["model_inputs"] == 750 and manifest["answers"] == 150
            and manifest["holdout_rows"] == 150 and manifest["calibration_rows"] == 30,
            "COUNTS")
    files = {}
    for name in ("inputs.jsonl", "answers.jsonl"):
        path = root / name
        require(path.is_file() and not path.is_symlink(), "INPUT_PATH")
        raw = path.read_bytes()
        require(len(raw) < 4_000_000 and digest(raw) == manifest["sha256"][name],
                "CONTENT_HASH")
        files[name] = load_lines(raw)
    prompts, answers = files["inputs.jsonl"], files["answers.jsonl"]
    require(len(prompts) == 750 and len(answers) == 150, "ROW_COUNTS")
    answer_map = {}
    for answer in answers:
        require(set(answer) == {"id", "oracle_action"}
                and re.fullmatch(ID, answer["id"]) is not None
                and answer["id"] not in answer_map
                and answer["oracle_action"] in ("A", "B", "NONE"), "ANSWER_SHAPE")
        answer_map[answer["id"]] = answer["oracle_action"]
    require(sorted(answer_map.values()).count("A") == 50
            and sorted(answer_map.values()).count("B") == 50
            and sorted(answer_map.values()).count("NONE") == 50, "ANSWER_BALANCE")
    grouped = {}
    for p in prompts:
        require(set(p) == {"id", "arm", "messages"} and p["id"] in answer_map
                and p["arm"] in ARMS and type(p["messages"]) is list
                and len(p["messages"]) == 1
                and set(p["messages"][0]) == {"role", "content"}
                and p["messages"][0]["role"] == "user"
                and type(p["messages"][0]["content"]) is str, "PROMPT_SHAPE")
        message = p["messages"][0]["content"]
        require("oracle_action" not in message and "rule_index" not in message
                and "sheet_index" not in message, "ANSWER_LEAK")
        require(message.startswith("Current request:\nProject " + p["id"] + ". "),
                "CURRENT_IDENTITY")
        key = (p["id"], p["arm"])
        require(key not in grouped, "DUPLICATE_ARM")
        grouped[key] = message
    require(len(grouped) == 750, "ARM_COUNT")
    exact_sources = {}
    for project in answer_map:
        _, _, b1, _ = parse_both(grouped[(project, "both_exact")], project)
        exact_sources[project] = b1
    for project, answer in answer_map.items():
        both = grouped[(project, "both_exact")]
        observed, current, b1, b2 = parse_both(both, project)
        require(observed == answer, "INDEPENDENT_ORACLE")
        require(grouped[(project, "c3_only")] == current, "C3_LEAK")
        require(grouped[(project, "b1_only")] == current + "\n\nB1 exact source:\n" + b1,
                "B1_ARM")
        require(grouped[(project, "b2_only")] == current + "\n\nB2 exact source:\n" + b2,
                "B2_ARM")
        shuffled, foreign = split_exact(grouped[(project, "shuffled")], "FOREIGN B1 source")
        require(shuffled == current + "\n\nB2 exact source:\n" + b2,
                "SHUFFLED_POLICY")
        require(source_id(foreign) is not None and source_id(foreign) != project
                and foreign != b1, "SHUFFLED_FOREIGN")
        require(source_id(foreign) in exact_sources
                and foreign == exact_sources[source_id(foreign)], "SHUFFLED_COHORT")
    return {"schema": SCHEMA, "status": "INDEPENDENT_SOFTWARE_ONLY_NO_NATIVE",
            "fixture_sha256": expected_fixture_sha256,
            "inputs_sha256": manifest["sha256"]["inputs.jsonl"],
            "answers_sha256": manifest["sha256"]["answers.jsonl"],
            "checked_prompts": 750, "checked_answers": 150,
            "oracle_matches": 150,
            "external_export_pins_verified": inputs_sha256 is not None,
            "canonical_gate_pass": False,
            "step2_status": "UTILITY_FAIL", "whole_system_complete": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--inputs-sha256", required=True)
    parser.add_argument("--answers-sha256", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.directory, args.fixture_sha256,
                            inputs_sha256=args.inputs_sha256,
                            answers_sha256=args.answers_sha256), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
