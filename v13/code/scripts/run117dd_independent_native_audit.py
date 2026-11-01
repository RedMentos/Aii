#!/usr/bin/env python3
"""Read-only, stdlib-only independent audit of immutable Run117DA native ZIP.

No model download, no inference, no changed scorer and no promotion. The
original artifact stays outside the public repository. Only aggregates print.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import zipfile

ARTIFACT_SHA256 = "71b2337a0fb012cbf0842417092311d666b52f19110e95646054d01f8bb35568"
SOURCE_HEAD = "895c2680563647d9684670d9890ee0cff6ffaf26"
TABLE_SHA256 = "78ec82002dafa54bcd9bb09456a0351123d2974bf12222fa6b20794d44f2edfb"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ARMS = ("LFM_SCHEMA", "QWEN_UNCONSTRAINED", "LFM_UNCONSTRAINED", "QWEN_SCHEMA")
MODELS = {"LFM": ("lfm25_350m", "LFM2.5-350M-QAD-Q4_0.gguf",
                  "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"),
          "QWEN": ("qwen35_0p8b", "Qwen3.5-0.8B-Q4_0.gguf",
                   "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf")}
# Independently transcribed from the preregistration, not the report's labels.
TABLE = (
 ("DA01","harbor buoys","Minimum","Maximum",(100,20,True),(120,15,True),(90,10,True),"A"),
 ("DA02","canal tugs","Minimum","Maximum",(80,15,True),(70,12,True),(90,14,True),"B"),
 ("DA03","cliff beacons","Maximum","Minimum",(120,20,True),(100,15,True),(130,25,True),"NONE"),
 ("DA04","wind probes","Maximum","Minimum",(200,10,False),(150,12,False),(180,11,True),"A"),
 ("DA05","river gauges","Minimum","Minimum",(70,10,True),(60,15,True),(75,11,True),"B"),
 ("DA06","lab samplers","Maximum","Maximum",(150,20,True),(120,10,False),(130,15,False),"NONE"),
 ("DA07","forest sensors","Minimum","Minimum",(100,15,False),(105,16,False),(115,18,False),"A"),
 ("DA08","archive skiffs","Maximum","Maximum",(140,25,False),(130,30,True),(135,20,False),"B"),
 ("DA09","polar monitors","Minimum","Maximum",(200,10,True),(210,12,True),(190,9,True),"NONE"),
 ("DA10","urban relays","Maximum","Maximum",(160,30,True),(140,25,True),(150,20,True),"A"),
 ("DA11","desert robots","Maximum","Minimum",(90,18,False),(100,25,True),(85,19,False),"B"),
 ("DA12","island rovers","Minimum","Minimum",(120,30,True),(125,25,True),(115,35,True),"NONE"),
)

class AuditError(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise AuditError(code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_KEY")
        out[key] = value
    return out


def decode(raw):
    if type(raw) is not str or not 0 < len(raw.encode("utf-8")) <= 1024:
        return None
    try:
        value = json.loads(raw, object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE")))
    except (ValueError, TypeError, UnicodeError):
        return None
    if (type(value) is not dict or set(value) != {"action"}
            or type(value["action"]) is not str):
        return None
    return value["action"] if value["action"] in ("A", "B", "NONE") else None


def _sources(row):
    project, domain, op1, op2, rule, a, b, _ = row
    tf = lambda v: "true" if v else "false"
    current = (f"Project {project}. Choose Option A or Option B using the "
               f"archived {domain} policy and latest option sheet. "
               "If neither qualifies, choose NONE.")
    policy = (f"Project {project} archived {domain} policy. "
              f"{op1} battery quota: {rule[0]} units. "
              f"{op2} start window: {rule[1]} ticks. "
              f"Required sealed: {tf(rule[2])}.")
    opt = lambda name, x: (f"Option {name}: battery quota {x[0]} units; "
                           f"start window {x[1]} ticks; sealed {tf(x[2])}.")
    sheet = f"Project {project} latest {domain} option sheet. " + opt("A", a) + " " + opt("B", b)
    return {"current": digest(current.encode()), "policy_source": digest(policy.encode()),
            "sheet_source": digest(sheet.encode())}


def _oracle(row):
    _, _, op1, op2, rule, a, b, _ = row
    eligible = []
    for name, opt in (("A", a), ("B", b)):
        bounds = all(opt[i] >= rule[i] if op == "Minimum" else opt[i] <= rule[i]
                     for i, op in enumerate((op1, op2)))
        if bounds and (not rule[2] or opt[2]):
            eligible.append((opt[0], opt[1], name))
    return min(eligible)[2] if eligible else "NONE"


def audit_report(report):
    need(digest(json.dumps(TABLE, sort_keys=True, separators=(",", ":")).encode()) == TABLE_SHA256,
         "FROZEN_TABLE_SHA_RED")
    need([_oracle(row) for row in TABLE] == [row[-1] for row in TABLE], "PREREG_ORACLE_RED")
    need(report.get("schema") == "v13.run117da.disjoint_source_only_schema_ablation_native.v1"
         and report.get("seed") == 117053 and report.get("table_sha256") == TABLE_SHA256,
         "COHORT_IDENTITY_RED")
    need(report.get("runner_sha256") == RUNNER_SHA256 and report.get("pins_unchanged") is True,
         "RUNNER_PIN_RED")
    model_pins = {x["id"]: x for x in report.get("model_pins", [])}
    need(set(model_pins) == {m[0] for m in MODELS.values()}, "MODEL_SET_RED")
    for _, (mid, filename, model_sha) in MODELS.items():
        need(model_pins[mid].get("local_name") == filename
             and model_pins[mid].get("sha256") == model_sha, "MODEL_PIN_RED")
    need(report.get("source_pins", {}).get("scripts/run117da_disjoint_schema_fixture.py")
         == "58b17a8e785724d12d22cc7aa07b9e8bc57aa3c4", "SOURCE_PIN_RED")
    need(report.get("source_pins", {}).get("scripts/run117da_source_only_preflight.py")
         == "f0b7dd008798b8ab7c36d1f716eda85ecf6d78c4", "SOURCE_PIN_RED")
    negative = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
                "body_jepa": "UNAVAILABLE", "world_jepa": "SHADOW", "jepa_weight": 0,
                "redmi_measured": False, "whole_system_complete": False,
                "independent_generalization": False, "output_committed": False,
                "delivery_authority": 0, "learning_authority": 0, "tool_dispatches": 0,
                "native_b1_calls": 0, "native_b2_calls": 0, "native_body_calls": 0,
                "native_c2_calls": 0, "native_jef_calls": 0, "native_model_weight_updates": 0}
    need(all(report.get(k) == v and type(report.get(k)) is type(v)
             for k, v in negative.items()), "NEGATIVE_GATES_RED")
    need(report.get("native_proof") is True and report.get("native_calls_verified") == 48
         and report.get("model_callback_attempts") == 48, "NATIVE_RECEIPT_COUNT_RED")
    need(report.get("evidence_class") == "LINUX_NATIVE_C3_DISJOINT_SCHEMA_ABLATION",
         "EVIDENCE_CLASS_RED")
    rows = report.get("rows")
    need(type(rows) is list and len(rows) == 12, "ROW_COUNT_RED")
    scores = {m[0]: {"SCHEMA": 0, "UNCONSTRAINED": 0} for m in MODELS.values()}
    non_none = copy.deepcopy(scores)
    none_count = copy.deepcopy(scores)
    paired = {m[0]: {"schema_only": 0, "unconstrained_only": 0} for m in MODELS.values()}
    for i, (actual, frozen) in enumerate(zip(rows, TABLE)):
        expected = frozen[-1]
        order = ARMS[i % 4:] + ARMS[:i % 4]
        need(actual.get("index") == i and actual.get("project") == frozen[0]
             and actual.get("expected") == expected
             and actual.get("source_sha256") == _sources(frozen)
             and actual.get("arm_order") == list(order), "ROW_SOURCE_OR_ORDER_RED")
        message_sha = actual.get("messages_sha256")
        need(type(message_sha) is str and re.fullmatch("[0-9a-f]{64}", message_sha),
             "MESSAGE_DIGEST_SHAPE_RED")
        arms = actual.get("arms")
        need(type(arms) is list and len(arms) == 4
             and [a.get("arm") for a in arms] == list(order), "ARM_ORDER_RED")
        by = {a["arm"]: a for a in arms}
        for a in arms:
            prefix, mode = a["arm"].split("_", 1)
            mid, filename, _ = MODELS[prefix]
            need(a.get("model") == mid and a.get("mode") == mode
                 and a.get("messages_sha256") == message_sha
                 and a.get("status") == "RECORDED"
                 and a.get("native_final") is True and a.get("process_reaped") is True
                 and a.get("error_type") is None
                 and a.get("native_metrics", {}).get("status") == "FINAL"
                 and a["native_metrics"].get("actual_model") == filename,
                 "NATIVE_ARM_RECEIPT_RED")
            raw = a.get("native_output")
            need(type(raw) is str and a.get("raw_sha256") == digest(raw.encode()),
                 "RAW_HASH_RED")
            decoded = decode(raw)
            exact = decoded == expected
            need(a.get("parsed_action") == decoded and a.get("exact") is exact,
                 "FROZEN_STRICT_SCORE_RED")
            scores[mid][mode] += int(exact)
            non_none[mid][mode] += int(exact and expected != "NONE")
            none_count[mid][mode] += int(decoded == "NONE")
        for prefix, (mid, _, _) in MODELS.items():
            schema = by[prefix + "_SCHEMA"]["exact"]
            free = by[prefix + "_UNCONSTRAINED"]["exact"]
            paired[mid]["schema_only"] += int(schema and not free)
            paired[mid]["unconstrained_only"] += int(free and not schema)
    signals = {m: scores[m]["UNCONSTRAINED"] >= 7
               and non_none[m]["UNCONSTRAINED"] >= 5
               and paired[m]["unconstrained_only"] - paired[m]["schema_only"] >= 3
               for m in scores}
    computed = {"complete_native_receipts": True, "native_final": 48,
                "process_reaped": 48, "strict_scores": scores,
                "non_none_correct": non_none, "none_output_count": none_count,
                "paired": paired, "schema_signal_by_model": signals}
    need(report.get("summary") == computed, "SUMMARY_RECOMPUTE_RED")
    need(report.get("status") == "NO_EXPLORATORY_SCHEMA_SIGNAL"
         and not any(signals.values()), "NON_PROMOTION_RED")
    return computed


def audit_zip(path, expected_sha=ARTIFACT_SHA256):
    path = Path(path)
    archive_sha = digest(path.read_bytes())
    if expected_sha is not None:
        need(archive_sha == expected_sha, "ORIGINAL_ARCHIVE_SHA_RED")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) and "SHA256SUMS" in names
             and all(not n.startswith("/") and ".." not in Path(n).parts
                     and not n.endswith("/") for n in names), "ZIP_NAMES_RED")
        need(z.testzip() is None, "ZIP_CRC_RED")
        lines = z.read("SHA256SUMS").decode().splitlines()
        declared = {}
        for line in lines:
            match = re.fullmatch(r"([0-9a-f]{64})  \./([^\n]+)", line)
            need(match is not None, "INNER_MANIFEST_SYNTAX_RED")
            name = match.group(2)
            need(name not in declared, "INNER_MANIFEST_DUPLICATE_RED")
            declared[name] = match.group(1)
        need(set(declared) == set(names) - {"SHA256SUMS"}, "INNER_MANIFEST_COVERAGE_RED")
        for name, expected in declared.items():
            need(digest(z.read(name)) == expected, "INNER_SHA_RED")
        need(z.read("HEAD.txt").decode().strip() == SOURCE_HEAD, "SOURCE_HEAD_RED")
        stages = ("PREREG", "VENV", "DEPS", "PIP_CHECK", "COMPILE", "PREFLIGHT",
                  "INSTALL", "QWEN", "NATIVE", "VERIFY", "PRIVACY", "DIFF")
        need(all(z.read(stage + "_EXIT.txt").decode().strip() == "0" for stage in stages),
             "STAGE_EXIT_RED")
        report = json.loads(z.read("NATIVE_CASE/report.json"))
        summary = audit_report(report)
        return {"audit": "INDEPENDENT_ORIGINAL_NATIVE_ZIP_VERIFIED",
                "archive_sha256": archive_sha, "source_head": SOURCE_HEAD,
                "zip_entries": len(names), "inner_sha256_verified": len(declared),
                "native_calls": 48, "native_final": 48, "process_reaped": 48,
                "result": report["status"], "summary": summary,
                "evidence": "LINUX_NATIVE_ONLY", "redmi_measured": False,
                "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
                "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
                "whole_system_complete": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-zip", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_zip(args.original_zip), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()