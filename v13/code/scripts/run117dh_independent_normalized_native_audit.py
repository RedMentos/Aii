#!/usr/bin/env python3
"""Independent stdlib audit of frozen Run117DG original native ZIP.

No native inference, downloads, model calls, score tuning or gate promotion.
Requires an externally observed exact original ZIP SHA256 at invocation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import zipfile

SEED = 117061
TABLE_SHA256 = "81af85fb4a93baf8ea32c925f41548c6e9380ccd6025df43f2d4c346caad2e64"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ARMS = ("LFM_RAW", "QWEN_NORMALIZED", "LFM_NORMALIZED", "QWEN_RAW")
MODELS = {
    "LFM": ("lfm25_350m", "LFM2.5-350M-QAD-Q4_0.gguf",
            "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
            "657e078c94084481950a2d555a941481f715536b"),
    "QWEN": ("qwen35_0p8b", "Qwen3.5-0.8B-Q4_0.gguf",
             "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
             "8fea620810c4afa23dd6443f999a48574c1611a3"),
}
SOURCE_BLOBS = {
    "scripts/run117de_normalized_source_fixture.py": "04f79fb713344407c618fe736e94fb8549cc7121",
    "v13/jef_c3_normalized_source_shadow_candidate.py": "b625f989f7c3236652c7f646540f0e99d86cf016",
    "scripts/run117df_paired_source_preflight.py": "280c2f32e5ac707b8c0d3ca22cf9a1cf8d7255d1",
}
TABLE = (
 ('EB01','mesa turbines','Maximum','Minimum',(135,30,False),(130,36,True),(146,22,False),'A'),
 ('EB02','glacier telemetry','Minimum','Maximum',(215,15,True),(197,22,False),(217,14,True),'B'),
 ('EB03','port cranes','Maximum','Maximum',(165,25,True),(180,26,False),(171,32,False),'NONE'),
 ('EB04','reef surveyors','Minimum','Minimum',(125,30,False),(130,35,True),(140,40,False),'A'),
 ('EB05','rail beacons','Maximum','Minimum',(90,35,True),(104,34,False),(86,40,True),'B'),
 ('EB06','desert pumps','Minimum','Maximum',(205,25,True),(197,28,False),(194,29,False),'NONE'),
 ('EB07','marsh buoys','Maximum','Maximum',(95,25,False),(92,24,True),(107,32,False),'A'),
 ('EB08','solar trackers','Minimum','Minimum',(115,15,True),(140,25,True),(127,18,True),'B'),
 ('EB09','tunnel drones','Maximum','Minimum',(80,30,True),(94,29,False),(88,24,False),'NONE'),
 ('EB10','ridge relays','Minimum','Maximum',(185,15,False),(191,13,True),(191,15,False),'A'),
 ('EB11','orchard probes','Maximum','Maximum',(215,30,True),(199,29,True),(199,28,True),'B'),
 ('EB12','cave monitors','Minimum','Minimum',(80,15,True),(76,13,False),(62,9,False),'NONE'),
)

class AuditError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise AuditError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("DUPLICATE_JSON_KEY")
        obj[k] = v
    return obj


def decode(raw):
    if type(raw) is not str or not 0 < len(raw.encode("utf-8")) <= 1024:
        return None
    try:
        obj = json.loads(raw, object_pairs_hook=_unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE")))
    except (ValueError, TypeError, UnicodeError):
        return None
    if type(obj) is not dict or set(obj) != {"action"} or type(obj["action"]) is not str:
        return None
    return obj["action"] if obj["action"] in ("A", "B", "NONE") else None


def _oracle(row):
    _, _, op1, op2, rule, a, b, _ = row
    valid = []
    for name, opt in (("A", a), ("B", b)):
        bounds = all(opt[i] >= rule[i] if op == "Minimum" else opt[i] <= rule[i]
                     for i, op in enumerate((op1, op2)))
        if bounds and (not rule[2] or opt[2]):
            valid.append((opt[0], opt[1], name))
    return min(valid)[2] if valid else "NONE"


def _sources(row):
    project, domain, op1, op2, rule, a, b, _ = row
    tf = lambda x: "true" if x else "false"
    current = (f"Project {project}. Choose Option A or Option B using the "
               f"archived {domain} policy and latest option sheet. "
               "If neither qualifies, choose NONE.")
    policy = (f"Project {project} archived {domain} policy. "
              f"{op1} battery quota: {rule[0]} units. "
              f"{op2} start window: {rule[1]} ticks. Required sealed: {tf(rule[2])}.")
    opt = lambda name, x: (f"Option {name}: battery quota {x[0]} units; "
                           f"start window {x[1]} ticks; sealed {tf(x[2])}.")
    sheet = f"Project {project} latest {domain} option sheet. " + opt("A", a) + " " + opt("B", b)
    return {"current": sha(current.encode()), "policy_source": sha(policy.encode()),
            "sheet_source": sha(sheet.encode())}


def audit_report(r):
    need(sha(json.dumps(TABLE, sort_keys=True, separators=(",", ":")).encode()) == TABLE_SHA256,
         "FROZEN_TABLE_HASH_RED")
    need([_oracle(x) for x in TABLE] == [x[-1] for x in TABLE], "FROZEN_ORACLE_RED")
    need(r.get("schema") == "v13.run117dg.normalized_source_paired_native.v1"
         and r.get("seed") == SEED and r.get("table_sha256") == TABLE_SHA256,
         "COHORT_IDENTITY_RED")
    need(r.get("runner_sha256") == RUNNER_SHA256 and r.get("pins_unchanged") is True,
         "RUNNER_PIN_RED")
    pins = r.get("source_pins", {})
    need(all(pins.get(p) == sha1 for p, sha1 in SOURCE_BLOBS.items()), "SOURCE_PIN_RED")
    models = {m["id"]: m for m in r.get("model_pins", [])}
    need(set(models) == {x[0] for x in MODELS.values()}, "MODEL_SET_RED")
    for mid, name, model_sha, revision in MODELS.values():
        need(models[mid].get("local_name") == name
             and models[mid].get("sha256") == model_sha
             and models[mid].get("revision") == revision, "MODEL_PIN_RED")
    negative = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL", "b3": "NO_PROMOTION",
                "body_jepa": "UNAVAILABLE", "world_jepa": "SHADOW", "jepa_weight": 0,
                "redmi_measured": False, "whole_system_complete": False,
                "independent_generalization": False, "output_committed": False,
                "delivery_authority": 0, "learning_authority": 0, "tool_dispatches": 0,
                "native_b1_calls": 0, "native_b2_calls": 0, "native_body_calls": 0,
                "native_c2_calls": 0, "native_jef_calls": 0, "native_model_weight_updates": 0}
    need(all(r.get(k) == v and type(r.get(k)) is type(v)
             for k, v in negative.items()), "NEGATIVE_GATES_RED")
    need(r.get("native_proof") is True and r.get("native_calls_verified") == 48
         and r.get("model_callback_attempts") == 48
         and r.get("evidence_class") == "LINUX_NATIVE_C3_NEW_NORMALIZED_SOURCE_ABLATION",
         "NATIVE_RECEIPT_COUNT_RED")
    rows = r.get("rows")
    need(type(rows) is list and len(rows) == 12, "ROW_COUNT_RED")
    scores = {x[0]: {"RAW": 0, "NORMALIZED": 0} for x in MODELS.values()}
    non_none = copy.deepcopy(scores)
    none_count = copy.deepcopy(scores)
    paired = {x[0]: {"normalized_only": 0, "raw_only": 0} for x in MODELS.values()}
    for i, (row, frozen) in enumerate(zip(rows, TABLE)):
        order = ARMS[i % 4:] + ARMS[:i % 4]
        need(row.get("index") == i and row.get("project") == frozen[0]
             and row.get("expected") == frozen[-1]
             and row.get("source_sha256") == _sources(frozen)
             and row.get("arm_order") == list(order), "ROW_SOURCE_OR_ORDER_RED")
        need(type(row.get("source_ref_sha256")) is list
             and len(row["source_ref_sha256"]) == 2
             and all(type(x) is str and re.fullmatch("[0-9a-f]{64}", x)
                     for x in row["source_ref_sha256"])
             and type(row.get("current_source_ref_sha256")) is str
             and re.fullmatch("[0-9a-f]{64}", row["current_source_ref_sha256"]),
             "SOURCE_REF_SHAPE_RED")
        for mode in ("raw", "normalized"):
            need(type(row.get(mode + "_messages_sha256")) is str
                 and re.fullmatch("[0-9a-f]{64}", row[mode + "_messages_sha256"]),
                 "MESSAGE_HASH_SHAPE_RED")
        arms = row.get("arms")
        need(type(arms) is list and len(arms) == 4
             and [a.get("arm") for a in arms] == list(order), "ARM_ORDER_RED")
        by = {a["arm"]: a for a in arms}
        for a in arms:
            prefix, mode = a["arm"].split("_", 1)
            mid, name, _, _ = MODELS[prefix]
            need(a.get("model") == mid and a.get("mode") == mode
                 and a.get("messages_sha256") == row[mode.lower() + "_messages_sha256"]
                 and a.get("status") == "RECORDED"
                 and a.get("native_final") is True and a.get("process_reaped") is True
                 and a.get("error_type") is None
                 and a.get("native_metrics", {}).get("status") == "FINAL"
                 and a["native_metrics"].get("actual_model") == name,
                 "NATIVE_ARM_RECEIPT_RED")
            raw = a.get("native_output")
            need(type(raw) is str and a.get("raw_sha256") == sha(raw.encode()), "RAW_HASH_RED")
            decoded = decode(raw)
            exact = decoded == frozen[-1]
            need(a.get("parsed_action") == decoded and a.get("exact") is exact,
                 "STRICT_SCORER_RED")
            scores[mid][mode] += int(exact)
            non_none[mid][mode] += int(exact and frozen[-1] != "NONE")
            none_count[mid][mode] += int(decoded == "NONE")
        for prefix, (mid, _, _, _) in MODELS.items():
            raw_ok = by[prefix + "_RAW"]["exact"]
            normalized_ok = by[prefix + "_NORMALIZED"]["exact"]
            paired[mid]["normalized_only"] += int(normalized_ok and not raw_ok)
            paired[mid]["raw_only"] += int(raw_ok and not normalized_ok)
    signals = {m: scores[m]["NORMALIZED"] >= 7 and non_none[m]["NORMALIZED"] >= 5
               and paired[m]["normalized_only"] - paired[m]["raw_only"] >= 3
               for m in scores}
    summary = {"complete_native_receipts": True, "native_final": 48,
               "process_reaped": 48, "strict_scores": scores,
               "non_none_correct": non_none, "none_output_count": none_count,
               "paired": paired, "normalized_signal_by_model": signals}
    need(r.get("summary") == summary, "SUMMARY_RECOMPUTE_RED")
    status = ("EXPLORATORY_NORMALIZED_SOURCE_SIGNAL_NONPROMOTING" if any(signals.values())
              else "NO_EXPLORATORY_NORMALIZED_SOURCE_SIGNAL")
    need(r.get("status") == status, "STATUS_OR_PROMOTION_RED")
    return summary


def audit_zip(path, *, expected_sha256, expected_head):
    need(re.fullmatch("[0-9a-f]{64}", expected_sha256 or "") is not None,
         "EXTERNAL_ARCHIVE_PIN_REQUIRED")
    need(re.fullmatch("[0-9a-f]{40}", expected_head or "") is not None,
         "EXTERNAL_SOURCE_HEAD_REQUIRED")
    original_sha = sha(Path(path).read_bytes())
    need(original_sha == expected_sha256, "ORIGINAL_ARCHIVE_SHA_RED")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) and "SHA256SUMS" in names
             and all(not n.startswith("/") and ".." not in Path(n).parts
                     and not n.endswith("/") for n in names), "ZIP_NAMES_RED")
        need(z.testzip() is None, "ZIP_CRC_RED")
        declared = {}
        for line in z.read("SHA256SUMS").decode().splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  \./([^\n]+)", line)
            need(match is not None, "INNER_MANIFEST_SYNTAX_RED")
            name = match.group(2)
            need(name not in declared, "INNER_MANIFEST_DUPLICATE_RED")
            declared[name] = match.group(1)
        need(set(declared) == set(names) - {"SHA256SUMS"}, "INNER_MANIFEST_COVERAGE_RED")
        for name, digest in declared.items():
            need(sha(z.read(name)) == digest, "INNER_SHA_RED")
        need(z.read("HEAD.txt").decode().strip() == expected_head, "SOURCE_HEAD_RED")
        stages = ("PINS", "VENV", "DEPS", "PIP_CHECK", "COMPILE", "PREFLIGHT",
                  "INSTALL", "QWEN", "NATIVE", "VERIFY", "PRIVACY", "DIFF")
        need(all(z.read(stage + "_EXIT.txt").decode().strip() == "0" for stage in stages),
             "STAGE_EXIT_RED")
        report = json.loads(z.read("NATIVE_CASE/report.json"))
        summary = audit_report(report)
        return {"audit": "RUN117DG_ORIGINAL_NATIVE_ZIP_INDEPENDENTLY_VERIFIED",
                "archive_sha256": original_sha, "source_head": expected_head,
                "zip_entries": len(names), "inner_sha256_verified": len(declared),
                "native_final": 48, "process_reaped": 48,
                "status": report["status"], "summary": summary,
                "evidence_class": "LINUX_NATIVE_ONLY",
                "redmi_measured": False, "step2": "UTILITY_FAIL",
                "b3": "NO_PROMOTION", "jepa_weight": 0,
                "whole_system_complete": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--original-zip", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--expected-head", required=True)
    a = p.parse_args()
    print(json.dumps(audit_zip(a.original_zip, expected_sha256=a.expected_sha256,
                               expected_head=a.expected_head), sort_keys=True))


if __name__ == "__main__":
    main()
