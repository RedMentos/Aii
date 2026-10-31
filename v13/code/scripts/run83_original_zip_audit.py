#!/usr/bin/env python3
"""Read-only, stdlib-only attestation of original Run83 GitHub Actions ZIP.

This is a retrospective engineering evidence audit, not a new native run or
scientific gate. Never extract untrusted members or repair the original ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile, BadZipFile

ORIGINAL_ZIP_SHA256 = "6577ea998cac2bb1706a2879bee3d8ba865742ef80fa6b7b8dab606d9669154e"
ORIGINAL_HEAD = "a4b4f9a63cbe27cbeea88cbd6e901e3be6d99d19"
STAGES = ("PINS", "VENV", "DEPS", "TEST", "BOOTSTRAP", "NATIVE", "VERIFY", "COMPILE", "PRIVACY", "DIFF")
PINS = {
    "v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md": "218464b12a2d27d92524c751922fa8e1c3fb0ea7",
    "v13/code/docs/RUN83_C3_DUAL_SOURCE_INTERFERENCE_NATIVE_PREREG_20261031.md": "ced10a86c3b32c9f7c35b55b50eb63119bc58245",
    "v13/code/scripts/jef_body_c3_interference_fixture_839.py": "a590a359df5b2baed2c622c949ed9c793e185265",
    "v13/code/scripts/run83_jef_body_c3_interference_native.py": "68dcb88818c7c4efb2bb3297d2d0c93c140d9362",
    "v13/code/scripts/run83_jef_body_c3_interference_verify.py": "cbff89068e4614fb0f3365bea21790048fd4e2e5",
    "v13/code/tests/test_run83_c3_interference_verify.py": "0ca7198e8e872d9a4c56b0c058fd33d2f4a79965",
    "v13/code/v13/jef_b1b2_c3_dual_source_shadow.py": "317024871a96c9dc390fe5c1c94032658f790b40",
}
TABLE_SHA = "be6ce6e8664e7f67bbaaeb18ac8e31b3a7bc1a81d8b903a4f57d06ad3e37ce3d"
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
PROJECTS = ("Juniper", "Kestrel", "Linden", "Mistral", "Nacre", "Orchid")
EXPECTED = ("A", "B", "NONE", "A", "B", "NONE")
SYSTEM_SHA256 = {
    "TYPED_ONLY": "3f27ef8203871896ced691b0e1da9836265c83253936141f315ece42542337fc",
    "DUAL_SOURCE": "e3e0d2367141cfbd2cefcb29acbc2af13d6beafd4332fe982993085fc07338bc",
}
# Frozen Run83 TABLE, reproduced literally; separate from imported V13 runtime.
TABLE = (
    ("Juniper", "harbor cranes", "Minimum", "Maximum", (107, 22, True), (127, 20, True), (97, 17, True), "A"),
    ("Kestrel", "museum drones", "Minimum", "Maximum", (107, 22, True), (137, 27, True), (147, 20, True), "B"),
    ("Linden", "forest robotics", "Maximum", "Minimum", (107, 22, True), (97, 17, True), (117, 27, True), "NONE"),
    ("Mistral", "island cargo", "Maximum", "Minimum", (207, 12, False), (157, 14, False), (187, 13, True), "A"),
    ("Nacre", "school bots", "Minimum", "Minimum", (77, 12, True), (67, 17, True), (82, 13, True), "B"),
    ("Orchid", "archive gliders", "Maximum", "Maximum", (157, 22, True), (127, 12, False), (137, 17, False), "NONE"),
)


def frozen_source_texts(row):
    project, domain, op1, op2, rule, option_a, option_b, _ = row
    tf = lambda value: "true" if value else "false"
    current = (f"Project {project}. Choose Option A or Option B using the "
               f"archived {domain} policy and latest option sheet. "
               "If neither qualifies, choose NONE.")
    policy = (f"Project {project} archived {domain} policy. "
              f"{op1} battery quota: {rule[0]} units. "
              f"{op2} start window: {rule[1]} ticks. "
              f"Required sealed: {tf(rule[2])}.")
    def option(label, x):
        return (f"Option {label}: battery quota {x[0]} units; "
                f"start window {x[1]} ticks; sealed {tf(x[2])}.")
    sheet = (f"Project {project} latest {domain} option sheet. "
             + option("A", option_a) + " " + option("B", option_b))
    return current, policy, sheet


def frozen_oracle(row):
    _, _, op1, op2, rule, option_a, option_b, _ = row
    eligible = []
    for name, opt in (("A", option_a), ("B", option_b)):
        bounds = all((opt[i] >= rule[i] if op == "Minimum" else opt[i] <= rule[i])
                     for i, op in enumerate((op1, op2)))
        if bounds and (not rule[2] or opt[2]):
            eligible.append((opt[0], opt[1], name))
    return min(eligible)[2] if eligible else "NONE"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
PIN_LINE = re.compile(r"([0-9a-f]{64})  (\./[A-Za-z0-9_./-]+)\Z")
MEMBERS = ({f"{s}_{kind}.{ext}" for s in STAGES for kind, ext in (("EXIT", "txt"), ("RAW", "log"))}
           | {"HEAD.txt", "PINS.txt", "SHA256SUMS", "pilot/report.json"})

class AuditError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise AuditError(code)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def exact_json(data: str):
    def no_duplicates(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise AuditError("RUN83_DUPLICATE_JSON_KEY_RED")
            result[k] = v
        return result
    return json.loads(data, object_pairs_hook=no_duplicates,
                      parse_constant=lambda v: (_ for _ in ()).throw(AuditError("RUN83_JSON_NAN_RED")))


def audit_report(raw: bytes) -> dict:
    try:
        report = exact_json(raw.decode("utf-8"))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise AuditError("RUN83_REPORT_JSON_RED") from exc
    require(type(report) is dict, "RUN83_REPORT_TYPE_RED")
    pins = {
        "schema": "v13.run83.c3_body_hypothesis_interference_native.v1",
        "seed": 839, "table_sha256": TABLE_SHA,
        "model_sha256_required": MODEL_SHA, "model_sha256_observed": MODEL_SHA,
        "runner_sha256_required": RUNNER_SHA, "runner_sha256_observed": RUNNER_SHA,
        "temperature": 0.0, "max_tokens": 32,
        "native_call_count": 12, "body_native_call_count": 0,
        "body_observations_synthetic": True, "typed_answer_visible_to_c3": True,
        "independent_reasoning_proven": False, "closed_store_ok": True,
        "no_live_output": True, "delivery_authority": 0, "learning_authority": 0,
        "tool_dispatches": 0, "output_committed": False, "tty_approved": False,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
        "body_jepa": "UNAVAILABLE", "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
    }
    for key, value in pins.items():
        require(type(report.get(key)) is type(value) and report[key] == value,
                "RUN83_REPORT_PIN_OR_AUTHORITY_RED:" + key)
    require(sha(json.dumps(TABLE, sort_keys=True, separators=(",", ":")).encode()) == TABLE_SHA
            and tuple(row[-1] for row in TABLE) == EXPECTED
            and all(frozen_oracle(row) == row[-1] for row in TABLE),
            "RUN83_FROZEN_TABLE_OR_ORACLE_RED")
    expected_sources = []
    for row in TABLE:
        current, policy, sheet = frozen_source_texts(row)
        expected_sources.append({"current": sha(current.encode()),
                                 "policy_source": sha(policy.encode()),
                                 "sheet_source": sha(sheet.encode())})
    cases = report.get("cases")
    require(type(cases) is list and len(cases) == 12, "RUN83_CASE_COUNT_RED")
    scores = {"TYPED_ONLY": 0, "DUAL_SOURCE": 0}
    per_case = {}
    for pos, c in enumerate(cases):
        require(type(c) is dict, "RUN83_CASE_TYPE_RED")
        index = pos // 2
        expected = EXPECTED[index]
        arm = ("TYPED_ONLY", "DUAL_SOURCE")[(pos % 2) ^ (index % 2)]
        require(type(c.get("index")) is int and c["index"] == index
                and c.get("arm") == arm
                and c.get("project_sha256") == sha(PROJECTS[index].encode())
                and c.get("expected") == expected
                and c.get("wrong_body_action") == ("B" if expected == "A" else "A")
                and c.get("typed_jef_action") == expected,
                "RUN83_CASE_ORDER_OR_ORACLE_RED")
        require(c.get("synthetic_body") is True and c.get("native_body") is False
                and c.get("native_final") is True
                and c.get("process_reaped") is True
                and c.get("post_source_rechecked") is True
                and c.get("actual_model") == "LFM2.5-350M-QAD-Q4_0.gguf"
                and c.get("status") == "RECORDED"
                and type(c.get("generated_tokens")) is int
                and 0 < c["generated_tokens"] <= 32,
                "RUN83_CASE_NATIVE_OR_AUTHORITY_RED")
        sources = c.get("source_sha256")
        require(type(sources) is dict and set(sources) == {"current", "policy_source", "sheet_source"}
                and all(type(v) is str and HEX64.fullmatch(v) for v in sources.values()),
                "RUN83_SOURCE_SHA_RED")
        require(sources == expected_sources[index], "RUN83_FROZEN_SOURCE_BINDING_RED")
        messages = c.get("input_messages")
        require(type(messages) is list and len(messages) == 2
                and all(type(m) is dict and set(m) == {"role", "content"} for m in messages)
                and messages[0]["role"] == "system" and type(messages[0]["content"]) is str
                and messages[1]["role"] == "user" and type(messages[1]["content"]) is str,
                "RUN83_MESSAGES_RED")
        require(sha(messages[0]["content"].encode()) == SYSTEM_SHA256[arm],
                "RUN83_FROZEN_SYSTEM_PROMPT_RED")
        require(c.get("input_sha256") == sha(json.dumps(messages, ensure_ascii=False,
                separators=(",", ":")).encode()), "RUN83_INPUT_HASH_RED")
        try:
            payload = exact_json(messages[1]["content"])
        except (ValueError, TypeError) as exc:
            raise AuditError("RUN83_PROMPT_JSON_RED") from exc
        require(type(payload) is dict and payload.get("typed_jef_action") == expected
                and payload.get("human_source_lineage_verified") is True,
                "RUN83_TYPED_LINEAGE_RED")
        if arm == "TYPED_ONLY":
            require("body_observations" not in payload
                    and "current_source" not in payload
                    and payload.get("rule_parser_revision") == "jef-mixed-range-policy-shadow-run73-v1"
                    and type(payload.get("source_ref_sha256")) is list
                    and len(payload["source_ref_sha256"]) == 2,
                    "RUN83_TYPED_ONLY_RED")
            refs = payload["source_ref_sha256"]
        else:
            require(payload.get("body_hypotheses_are_facts") is False
                    and payload.get("formatter_only") is True,
                    "RUN83_DUAL_AUTHORITY_RED")
            refs = payload.get("human_source_ref_sha256")
            obs = payload.get("body_observations")
            require(type(obs) is list and len(obs) == 2, "RUN83_DUAL_BODY_COUNT_RED")
            for j, role in enumerate(("B1_DETAIL", "B2_GIST")):
                o = obs[j]
                require(type(o) is dict and o.get("role") == role
                        and o.get("hypothesis_authority") == "MODEL_HYPOTHESIS_NOT_FACT"
                        and type(o.get("offer_packet_id")) is str
                        and o["offer_packet_id"].startswith("pkt_")
                        and o.get("verified_quotes") == []
                        and type(o.get("hypothesis")) is dict
                        and ("Option " + c["wrong_body_action"] + " is correct") in o["hypothesis"].get("summary", ""),
                        "RUN83_DUAL_BODY_HYPOTHESIS_RED")
            current = payload.get("current_source")
            require(type(current) is dict and type(current.get("text")) is str
                    and current["text"] == frozen_source_texts(TABLE[index])[0]
                    and type(current.get("source_ref")) is dict,
                    "RUN83_CURRENT_SOURCE_RED")
            sr = current["source_ref"]
            require(sr.get("sha256") == sha(current["text"].encode()) == sources["current"]
                    and sr.get("char_start") == 0
                    and sr.get("char_end") == len(current["text"])
                    and sr.get("modality") == "text",
                    "RUN83_CURRENT_SOURCE_HASH_RED")
        require(type(refs) is list and len(refs) == 2
                and all(type(x) is str and HEX64.fullmatch(x) for x in refs)
                and type(payload.get("current_source_ref_sha256")) is str
                and HEX64.fullmatch(payload["current_source_ref_sha256"]),
                "RUN83_HUMAN_REF_RED")
        prior = per_case.setdefault(index, {})
        if prior:
            require(prior["refs"] == refs
                    and prior["current_ref"] == payload["current_source_ref_sha256"]
                    and prior["sources"] == sources,
                    "RUN83_PAIRED_SOURCE_BINDING_RED")
        else:
            prior.update(refs=refs, current_ref=payload["current_source_ref_sha256"], sources=sources)
        output = c.get("output")
        require(type(output) is str and 0 < len(output.encode()) <= 1024
                and c.get("output_bytes") == len(output.encode())
                and c.get("output_sha256") == sha(output.encode()),
                "RUN83_OUTPUT_BYTES_OR_SHA_RED")
        try:
            parsed = exact_json(output)
        except (ValueError, TypeError) as exc:
            raise AuditError("RUN83_OUTPUT_JSON_RED") from exc
        require(type(parsed) is dict and set(parsed) == {"action"}
                and type(parsed["action"]) is str
                and parsed["action"] in {"A", "B", "NONE"}
                and c.get("parsed_action") == parsed["action"]
                and type(c.get("strict")) is int
                and c["strict"] == int(parsed["action"] == expected),
                "RUN83_OUTPUT_SCHEMA_OR_SCORE_RED")
        scores[arm] += c["strict"]
    status = ("BASELINE_FORMATTER_RED" if scores["TYPED_ONLY"] < 5
              else "DUAL_FORMATTER_NONINFERIOR_SMALL_SHADOW" if scores["DUAL_SOURCE"] >= scores["TYPED_ONLY"] - 1
              else "DUAL_INTERFERENCE_RED")
    require(report.get("scores") == scores and report.get("status") == status,
            "RUN83_SCORE_OR_VERDICT_RED")
    return {"status": status, "scores": scores, "rows": len(cases),
            "synthetic_body_only": True, "step2_promoted": False}


def audit_bytes(raw: bytes, *, expected_zip_sha: str = ORIGINAL_ZIP_SHA256) -> dict:
    require(type(raw) is bytes and sha(raw) == expected_zip_sha, "RUN83_ORIGINAL_ZIP_SHA_RED")
    try:
        with ZipFile(io.BytesIO(raw)) as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            require(len(names) == len(set(names)), "RUN83_DUPLICATE_ZIP_MEMBER_RED")
            require(set(names) == MEMBERS and len(names) == len(MEMBERS),
                    "RUN83_ZIP_MEMBERS_RED")
            require(all(not i.is_dir() and i.file_size <= 2_000_000 for i in infos)
                    and sum(i.file_size for i in infos) <= 5_000_000,
                    "RUN83_ZIP_SIZE_RED")
            require(z.testzip() is None, "RUN83_ZIP_CRC_RED")
            manifest = z.read("SHA256SUMS").decode("utf-8").splitlines()
            found = {}
            for line in manifest:
                m = PIN_LINE.fullmatch(line)
                require(m is not None, "RUN83_MANIFEST_SYNTAX_RED")
                name = m[2][2:]
                require(name not in found, "RUN83_MANIFEST_DUPLICATE_RED")
                found[name] = m[1]
            require(set(found) == MEMBERS - {"SHA256SUMS"},
                    "RUN83_MANIFEST_COVERAGE_RED")
            for name, digest in found.items():
                require(sha(z.read(name)) == digest, "RUN83_MEMBER_SHA_RED:" + name)
            require(z.read("HEAD.txt").decode("ascii").strip() == ORIGINAL_HEAD,
                    "RUN83_HEAD_RED")
            pin_rows = z.read("PINS.txt").decode("utf-8").splitlines()
            raw_rows = z.read("PINS_RAW.log").decode("utf-8").splitlines()
            require(len(pin_rows) == len(raw_rows) == len(PINS), "RUN83_PIN_COUNT_RED")
            seen = set()
            for p, r in zip(pin_rows, raw_rows):
                m = re.fullmatch(r"([0-9a-f]{40}) (\S+)", p)
                n = re.fullmatch(r"([0-9a-f]{40}) ([0-9a-f]{40}) (\S+)", r)
                require(m is not None and n is not None, "RUN83_PIN_SYNTAX_RED")
                want, path = m.groups()
                require(path not in seen and PINS.get(path) == want
                        and n.groups() == (want, want, path),
                        "RUN83_PIN_BLOB_RED")
                seen.add(path)
            for stage in STAGES:
                require(z.read(stage + "_EXIT.txt") == b"0\n",
                        "RUN83_STAGE_EXIT_RED:" + stage)
            result = audit_report(z.read("pilot/report.json"))
    except (BadZipFile, UnicodeError, OSError, KeyError, EOFError) as exc:
        raise AuditError("RUN83_ZIP_UNREADABLE_RED") from exc
    return {"audit": "RUN83_ORIGINAL_ZIP_INDEPENDENT_REPARSE_PASS",
            "original_zip_sha256": sha(raw), "original_head": ORIGINAL_HEAD,
            "inner_files_hashed": len(MEMBERS) - 1, "stage_exits_zero": len(STAGES),
            "registered_result": result["status"], "scores": result["scores"],
            "native_c3_rows_reported": result["rows"],
            "body_native_calls": 0, "synthetic_body_only": True,
            "scientific_utility_proven": False, "step2_promoted": False,
            "redmi_measured": False, "delivery_authority": 0,
            "limitations": "Retrospective ZIP/runner-report attestation, not independent hardware observation"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("original_zip", type=Path)
    args = p.parse_args()
    print(json.dumps(audit_bytes(args.original_zip.read_bytes()), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
