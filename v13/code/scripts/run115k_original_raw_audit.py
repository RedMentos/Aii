#!/usr/bin/env python3
"""Read-only, stdlib-only independent audit of frozen Run115J native ZIP.

This does not re-score or mutate the registered native experiment. It verifies
an original artifact and reports a strictly bounded, non-promoting pilot signal.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

ORIGINAL_SHA = "f09b40bf4e30c08f183a3421cbd0961951727117915d56319d6dc1879e4738de"
HEAD = "8b8321933a6d16c2b924283d22086f90858088bc"
FIXTURE_SHA = "3cfe98d4903aaef56dd412ad426d743941fa0115b346cdf77d9abeaf2fbeb2a0"
IDS = ("Kairo", "Lythos", "Oxara", "Perrin", "Sereon", "Valtor")
EXPECTED = (("A", 10), ("B", 60), ("NONE", None), ("A", 40), ("B", 30), ("NONE", None))
ARMS = ("RAW_SOURCE_ROLE", "TYPED_JEF_ROLE")
FIXTURE = "V13-Phone/docs/fixtures/RUN115J_TYPED_JEF_ROLE_SEED997.json"
EXIT_NAMES = ("DIFF", "INSTALL_C3", "NATIVE", "PACK", "PRIVACY", "VERIFY", "ZIP")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _require(condition, reason):
    if not condition:
        raise ValueError("RUN115K_" + reason + "_RED")


def _json(data):
    return json.loads(data)


def _pair(data):
    _require(type(data) is dict and set(data) == {"choice", "remaining"}, "ANSWER_SHAPE")
    _require(data["choice"] in ("A", "B", "NONE"), "ANSWER_CHOICE")
    _require((data["choice"] == "NONE" and data["remaining"] is None)
             or (data["choice"] != "NONE" and type(data["remaining"]) is int),
             "ANSWER_REMAINING")
    return data["choice"], data["remaining"]


def audit(path, *, expected_sha=ORIGINAL_SHA):
    raw = Path(path).read_bytes()
    _require(_sha(raw) == expected_sha, "OUTER_SHA")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        _require(len(names) == len(set(names)) and z.testzip() is None, "ZIP_CRC_OR_DUPLICATE")
        _require("SHA256SUMS" in names, "MISSING_MANIFEST")
        entries = {}
        for line in z.read("SHA256SUMS").decode("utf-8").splitlines():
            parts = line.split("  ", 1)
            _require(len(parts) == 2, "MANIFEST_FORMAT")
            digest, name = parts
            name = name.removeprefix("./")
            _require(name not in entries and name != "SHA256SUMS", "MANIFEST_DUPLICATE")
            entries[name] = digest
        _require(set(entries) == set(names) - {"SHA256SUMS"}, "MANIFEST_COVERAGE")
        for name, digest in entries.items():
            _require(_sha(z.read(name)) == digest, "INNER_HASH")
        _require(z.read("HEAD.txt").decode().strip() == HEAD, "HEAD")
        for stage in EXIT_NAMES:
            _require(z.read(stage + "_EXIT.txt").decode().strip() == "0", "STAGE_EXIT")
        result = _json(z.read("RESULT.json"))
        _require(result["head"] == HEAD and all(result["exits"][s] == 0 for s in EXIT_NAMES),
                 "RESULT_PROVENANCE")
        _require(all(result[k] is False for k in (
            "step2_promoted", "b3_promoted", "body_jepa_promoted", "redmi_measured",
            "native_b1_executed", "native_b2_executed", "native_c2_executed",
            "native_jef_executed")), "RESULT_GATE")
        with zipfile.ZipFile(io.BytesIO(z.read("V13-Phone-Run115J-Native.zip"))) as phone:
            _require(phone.testzip() is None and len(phone.namelist()) == len(set(phone.namelist())),
                     "PHONE_ZIP")
            _require("V13-Phone/WORKSPACE_FILES.json" in phone.namelist(),
                     "PHONE_MANIFEST_MISSING")
            manifest = _json(phone.read("V13-Phone/WORKSPACE_FILES.json"))
            files = manifest["files"]
            _require(set(phone.namelist()) ==
                     {"V13-Phone/" + name for name in files} |
                     {"V13-Phone/WORKSPACE_FILES.json"}, "PHONE_MANIFEST_COVERAGE")
            for name, digest in files.items():
                _require(_sha(phone.read("V13-Phone/" + name)) == digest,
                         "PHONE_SOURCE_HASH")
            _require(FIXTURE in phone.namelist(), "PHONE_FIXTURE_MISSING")
            frozen = phone.read(FIXTURE)
            _require(_sha(frozen) == FIXTURE_SHA, "FIXTURE_HASH")
            fixture = _json(frozen)
            _require(fixture["seed"] == 997 and fixture["arms"] == list(ARMS), "FIXTURE_META")
            cases = fixture["rows"]
        report = _json(z.read("NATIVE_CASE/report.json"))
        _require(report["fixture_sha256"] == FIXTURE_SHA and report["native"] is True
                 and report["native_c3_calls"] == 12 and len(report["rows"]) == 6,
                 "REPORT_META")
        _require(all(report[k] == 0 for k in ("native_b1_calls", "native_b2_calls",
                 "native_jef_calls", "delivery_authority", "learning_authority",
                 "tool_dispatches", "jepa_weight")), "REPORT_AUTHORITY")
        _require(all(report[k] is False for k in ("native_c2", "native_jef",
                 "output_committed", "redmi_measured", "whole_system_complete"))
                 and report["age0"] == "RECORD_ONLY", "REPORT_GATE")
        _require([r["id"] for r in report["rows"]] == list(IDS)
                 and [r["id"] for r in cases] == list(IDS), "ROW_IDENTITY")
        scores = {a: 0 for a in ARMS}
        for i, (row, source) in enumerate(zip(report["rows"], cases)):
            expected = EXPECTED[i]
            _require(_pair(source["oracle"]) == expected, "ORACLE")
            _require(row["status"] == "RECORDED" and row["closed_store_ok"] is True
                     and row["no_live_output"] is True and len(row["arms"]) == 2,
                     "ROW_STRUCTURE")
            _require(_pair(row["typed_jef_candidate"]) == expected, "JEF_CANDIDATE")
            _require({a["arm"] for a in row["arms"]} == set(ARMS), "ARM_SET")
            for arm in row["arms"]:
                name = arm["arm"]
                _require(arm["status"] == "RECORDED" and arm["native_final"] is True
                         and arm["process_reaped"] is True, "NATIVE_LIFECYCLE")
                _require(arm["native_metrics"]["status"] == "FINAL"
                         and arm["native_metrics"]["actual_model"] ==
                         "LFM2.5-350M-QAD-Q4_0.gguf", "NATIVE_MODEL")
                messages = arm["messages"]
                _require(len(messages) == 2 and [m["role"] for m in messages] ==
                         ["system", "user"], "MESSAGE_ROLES")
                _require(source["prior"] not in messages[0]["content"]
                         and source["current"] not in messages[0]["content"],
                         "SYSTEM_SOURCE_LEAK")
                payload = _json(messages[1]["content"])
                _require(payload["source_transport_only"] is True
                         and payload["body_model_quote_verified"] is False
                         and len(payload["sources"]) == 2, "SOURCE_DATA")
                _require([s["text"] for s in payload["sources"]] ==
                         [source["prior"], source["current"]], "SOURCE_TEXT")
                _require([s["source_ref"] for s in payload["sources"]] ==
                         row["source_refs"], "SOURCE_REFS")
                for s in payload["sources"]:
                    ref = s["source_ref"]
                    _require(ref["char_start"] == 0 and ref["char_end"] == len(s["text"])
                             and ref["sha256"] == _sha(s["text"].encode("utf-8")),
                             "SOURCE_HASH")
                _require('"oracle"' not in messages[1]["content"], "ORACLE_LEAK")
                if name == ARMS[0]:
                    _require("typed_jef_candidate" not in payload, "CONTROL_CONTAMINATION")
                else:
                    _require(_pair(payload["typed_jef_candidate"]) == expected
                             and payload["typed_candidate_authority"] == 0,
                             "TYPED_PAYLOAD")
                parsed = _pair(_json(arm["output"]))
                _require(_pair(arm["score"]["parsed"]) == parsed
                         and arm["score"]["correct"] == int(parsed == expected),
                         "ORIGINAL_SCORE_DISAGREES")
                scores[name] += int(parsed == expected)
        _require(report["scores"] == scores, "REPORT_SCORES")
        none_rows = [r for r in report["rows"] if r["id"] in ("Oxara", "Valtor")]
        no_false_none = all(_pair(_json(next(a for a in r["arms"]
            if a["arm"] == ARMS[1])["output"])) == ("NONE", None)
            for r in none_rows)
        signal = (scores[ARMS[1]] >= 5 and scores[ARMS[1]] - scores[ARMS[0]] >= 2
                  and no_false_none)
        _require(report["exploratory_role_signal"] is signal
                 and report["status"] == ("NATIVE_COMPLETE_TYPED_SIGNAL" if signal
                 else "NATIVE_COMPLETE_NO_GAIN"), "REPORT_SIGNAL")
        return {"status": "ORIGINAL_NATIVE_AUDIT_PASS", "outer_sha256": expected_sha,
                "source_head": HEAD, "inner_sha256_checked": len(entries),
                "phone_source_sha256_checked": len(files),
                "native_c3_final_reaped": 12, "scores": scores,
                "typed_signal_exploratory_only": signal,
                "scope": "six exact-grammar synthetic tasks; deterministic JEF copied by C3; no promotion"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("original_zip", type=Path)
    args = p.parse_args()
    print(json.dumps(audit(args.original_zip), sort_keys=True))


if __name__ == "__main__":
    main()
