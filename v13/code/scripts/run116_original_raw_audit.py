#!/usr/bin/env python3
"""Independent stdlib-only audit of an ORIGINAL Run116 native artifact.

No model execution, no rescoring of the frozen original in place, no gates
promoted. Requires externally verified GitHub artifact SHA256.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

HEAD = "df08a4ce311317bdfd322ba7c7520d9fe8fb2b93"
FIXTURE_SHA = "e31e2d68331cc4280e161b2dbdbd022f493325ca234f050cda06065fa6775a69"
FIXTURE = "V13-Phone/docs/fixtures/RUN116_B1B2_JEF_C3_SEED1019.json"
PHONE_ZIP = "V13-Phone-Run116-Native.zip"
IDS = ("Ardent", "Birch", "Cetus", "Dawn", "Eider", "Fjord")
EXPECTED = (("A", 20), ("B", 60), ("NONE", None),
            ("A", 40), ("B", 60), ("NONE", None))
ARMS = ("RAW_TWO_SOURCE_ROLE", "TYPED_JEF_ROLE",
        "TYPED_JEF_WITH_BODY_ROLE")
EXITS = ("PACK", "ZIP", "PREFLIGHT", "INSTALL_C3", "INSTALL_BODIES",
         "NATIVE", "VERIFY", "PRIVACY", "DIFF")
BODY_MODELS = {"B1_DETAIL": ("LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf",
                              "6767265158422fb8a19c62ceb45f16f05363615b"),
               "B2_GIST": ("Qwen3.5-0.8B-Q4_0.gguf",
                           "8fea620810c4afa23dd6443f999a48574c1611a3")}
C3_MODEL = "LFM2.5-350M-QAD-Q4_0.gguf"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _need(ok, reason):
    if not ok:
        raise ValueError("RUN116_AUDIT_" + reason + "_RED")


def _json(data):
    return json.loads(data, parse_constant=lambda x: (_ for _ in ()).throw(
        ValueError("NONFINITE_JSON")), object_pairs_hook=_unique)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _pair(v):
    _need(type(v) is dict and set(v) == {"choice", "remaining"}, "PAIR_SHAPE")
    _need(v["choice"] in ("A", "B", "NONE"), "PAIR_CHOICE")
    _need((v["choice"] == "NONE" and v["remaining"] is None)
          or (v["choice"] != "NONE" and type(v["remaining"]) is int),
          "PAIR_REMAINING")
    return v["choice"], v["remaining"]


def _parse_output(raw):
    try:
        v = _json(raw)
        return v if type(v) is dict and set(v) == {"choice", "remaining"} and (
            v["choice"] in ("A", "B", "NONE", "UNKNOWN")) and (
            v["remaining"] is None or type(v["remaining"]) is int) else None
    except (TypeError, ValueError, OverflowError, KeyError):
        return None


def _ref(ref, text):
    return (type(ref) is dict
            and ref.get("char_start") == 0
            and type(ref.get("char_end")) is int
            and ref["char_end"] == len(text)
            and ref.get("sha256") == _sha(text.encode("utf-8"))
            and ref.get("modality") == "text")


def audit(path, *, expected_sha):
    _need(re.fullmatch("[0-9a-f]{64}", expected_sha) is not None,
          "EXPECTED_SHA_REQUIRED")
    raw = Path(path).read_bytes()
    _need(_sha(raw) == expected_sha, "OUTER_SHA")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        _need(len(names) == len(set(names)) and z.testzip() is None,
              "ZIP_CRC_OR_DUPLICATE")
        _need("SHA256SUMS" in names, "MANIFEST_MISSING")
        entries = {}
        for line in z.read("SHA256SUMS").decode().splitlines():
            parts = line.split("  ", 1)
            _need(len(parts) == 2, "MANIFEST_FORMAT")
            digest, name = parts
            name = name.removeprefix("./")
            _need(name not in entries and name != "SHA256SUMS", "MANIFEST_DUPLICATE")
            entries[name] = digest
        _need(set(entries) == set(names) - {"SHA256SUMS"}, "MANIFEST_COVERAGE")
        for name, digest in entries.items():
            _need(_sha(z.read(name)) == digest, "INNER_SHA")
        _need(z.read("HEAD.txt").decode().strip() == HEAD, "SOURCE_HEAD")
        for name in EXITS:
            _need(z.read(name + "_EXIT.txt").decode().strip() == "0",
                  "STAGE_" + name)
        result = _json(z.read("RESULT.json"))
        _need(result["head"] == HEAD
              and all(result["exits"][name] == 0 for name in EXITS)
              and result["native_attempted"] is True
              and all(result[k] is False for k in (
                  "native_c2_executed", "native_jef_executed",
                  "redmi_measured", "step2_promoted", "b3_promoted",
                  "body_jepa_promoted")), "RESULT_PROVENANCE_OR_GATE")
        with zipfile.ZipFile(io.BytesIO(z.read(PHONE_ZIP))) as phone:
            _need(phone.testzip() is None and
                  len(phone.namelist()) == len(set(phone.namelist())),
                  "PHONE_CRC")
            manifest = _json(phone.read("V13-Phone/WORKSPACE_FILES.json"))
            files = manifest["files"]
            _need(set(phone.namelist()) ==
                  {"V13-Phone/" + n for n in files} |
                  {"V13-Phone/WORKSPACE_FILES.json"}, "PHONE_MANIFEST_COVERAGE")
            for name, digest in files.items():
                _need(_sha(phone.read("V13-Phone/" + name)) == digest,
                      "PHONE_SOURCE_HASH")
            _need(FIXTURE in phone.namelist(), "PHONE_FIXTURE_MISSING")
            frozen = phone.read(FIXTURE)
            _need(_sha(frozen) == FIXTURE_SHA, "FIXTURE_SHA")
            fixture = _json(frozen)
            _need(fixture["seed"] == 1019 and fixture["arms"] == list(ARMS),
                  "FIXTURE_META")
            cases = fixture["rows"]
        report = _json(z.read("NATIVE_CASE/report.json"))
        _need(report["schema"] == "v13.run116.b1b2_jef_c3_native.v1"
              and report["fixture_sha256"] == FIXTURE_SHA
              and report["seed"] == 1019 and report["native"] is True
              and report["synthetic_body_observers"] is False
              and report["native_body_calls"] == 18
              and report["native_c3_calls"] == 18
              and report["native_c2_calls"] == 0
              and report["native_jef_calls"] == 0
              and len(report["rows"]) == len(cases) == 6,
              "NATIVE_REPORT_META")
        _need(report["status"] in (
              "NATIVE_COMPLETE_NONINTERFERENCE_SIGNAL",
              "NATIVE_COMPLETE_NO_NONINTERFERENCE_SIGNAL")
              and all(report[k] == 0 for k in (
                  "delivery_authority", "learning_authority",
                  "tool_dispatches", "jepa_weight"))
              and all(report[k] is False for k in (
                  "output_committed", "redmi_measured",
                  "whole_system_complete"))
              and report["age0"] == "RECORD_ONLY"
              and report["step2_exit"] == "EVIDENCE_NOT_PASSING"
              and report["b3"] == "NO_PROMOTION"
              and report["body_jepa"] == "UNAVAILABLE",
              "REPORT_AUTHORITY_OR_GATE")
        _need([r["id"] for r in report["rows"]] ==
              [c["id"] for c in cases] == list(IDS), "ROW_IDENTITY")
        scores = {arm: 0 for arm in ARMS}
        for i, (row, source) in enumerate(zip(report["rows"], cases)):
            oracle = source["oracle"]
            _need(_pair(oracle) == EXPECTED[i], "ORACLE")
            _need(row["status"] == "RECORDED"
                  and row["closed_store_ok"] is True
                  and row["no_live_output"] is True
                  and len(row["offers"]) == 3 and len(row["arms"]) == 3,
                  "ROW_STRUCTURE")
            refs = [row["prior_source_ref"], row["current_source_ref"]]
            _need(all(_ref(ref, text) for ref, text in
                      zip(refs, (source["prior"], source["current"]))),
                  "SOURCE_REFS")
            _need(type(row["verified_quote_count"]) is int
                  and row["verified_quote_count"] >= 0, "BODY_QUOTE_COUNT")
            _need([(o["role"], o["phase"]) for o in row["offers"]] ==
                  [("B2_GIST", "prior"), ("B1_DETAIL", "current"),
                   ("B2_GIST", "current")], "BODY_OFFER_ORDER")
            for offer in row["offers"]:
                role = offer["role"]
                expected_model, expected_revision = BODY_MODELS[role]
                _need(offer["status"] == "RECORDED"
                      and offer["process_reaped"] is True
                      and offer["native_metrics"]["status"] == "FINAL"
                      and offer["native_metrics"]["actual_model"] == expected_model
                      and offer["model_revision"] == expected_revision
                      and offer["source_ref"] ==
                      (refs[0] if offer["phase"] == "prior" else refs[1]),
                      "BODY_NATIVE_LIFECYCLE")
            _need({a["arm"] for a in row["arms"]} == set(ARMS),
                  "ARM_IDENTITY")
            for arm in row["arms"]:
                name = arm["arm"]
                _need(arm["status"] == "RECORDED"
                      and arm["native_final"] is True
                      and arm["process_reaped"] is True
                      and arm["native_metrics"]["status"] == "FINAL"
                      and arm["native_metrics"]["actual_model"] == C3_MODEL,
                      "C3_NATIVE_LIFECYCLE")
                messages = arm["messages"]
                _need(len(messages) == 2 and [m["role"] for m in messages] ==
                      ["system", "user"], "MESSAGE_ROLES")
                _need(source["prior"] not in messages[0]["content"]
                      and source["current"] not in messages[0]["content"]
                      and '"oracle"' not in messages[0]["content"].lower(),
                      "SYSTEM_SOURCE_OR_ORACLE_LEAK")
                payload = _json(messages[1]["content"])
                _need([s["text"] for s in payload["sources"]] ==
                      [source["prior"], source["current"]]
                      and [s["source_ref"] for s in payload["sources"]] == refs
                      and payload["body_model_quote_verified"] is False,
                      "SOURCE_ROLE_OR_LINEAGE")
                _need('"oracle"' not in messages[1]["content"].lower(),
                      "USER_ORACLE_LEAK")
                if name == ARMS[0]:
                    _need("typed_jef_candidate" not in payload
                          and "body_observations" not in payload,
                          "RAW_CONTROL_CONTAMINATION")
                else:
                    _need(_pair(payload["typed_jef_candidate"]) == EXPECTED[i]
                          and payload["typed_candidate_authority"] == 0,
                          "TYPED_CANDIDATE")
                    if name == ARMS[1]:
                        _need("body_observations" not in payload,
                              "TYPED_ONLY_CONTAMINATION")
                    else:
                        obs = payload["body_observations"]
                        _need([x["role"] for x in obs] ==
                              ["B1_DETAIL", "B2_GIST"]
                              and payload["body_hypotheses_are_facts"] is False
                              and all(x["hypothesis_authority"] ==
                                      "MODEL_HYPOTHESIS_NOT_FACT"
                                      and all(q["semantic_truth_authority"] is False
                                              for q in x["verified_quotes"])
                                      for x in obs), "BODY_HYPOTHESIS_AUTHORITY")
                parsed = _parse_output(arm["output"])
                _need(arm["score"]["parsed"] == parsed
                      and arm["score"]["valid_json"] is (parsed is not None)
                      and arm["score"]["correct"] ==
                      int(parsed == oracle), "ORIGINAL_SCORE_DISAGREES")
                scores[name] += int(parsed == oracle)
        _need(report["scores"] == scores, "AGGREGATE_SCORES")
        none_rows = [r for r in report["rows"] if r["id"] in ("Cetus", "Fjord")]
        no_false_none = all(_parse_output(next(
            a for a in r["arms"] if a["arm"] == ARMS[2])["output"]) ==
            {"choice": "NONE", "remaining": None} for r in none_rows)
        signal = (scores[ARMS[2]] >= 5 and
                  scores[ARMS[2]] >= scores[ARMS[1]] - 1 and no_false_none)
        _need(report["exploratory_noninterference_signal"] is signal
              and report["status"] ==
              ("NATIVE_COMPLETE_NONINTERFERENCE_SIGNAL" if signal else
               "NATIVE_COMPLETE_NO_NONINTERFERENCE_SIGNAL"), "SIGNAL")
        return {
            "status": "RUN116_ORIGINAL_NATIVE_AUDIT_PASS",
            "original_sha256": expected_sha, "source_head": HEAD,
            "inner_sha256_checked": len(entries),
            "phone_source_sha256_checked": len(files),
            "native_body_final_reaped": 18, "native_c3_final_reaped": 18,
            "scores": scores, "noninterference_exploratory_only": signal,
            "native_jef_c2": False, "redmi_measured": False,
            "step2_promoted": False, "whole_system_complete": False,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("original_zip", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.original_zip, expected_sha=args.sha256),
                     sort_keys=True))


if __name__ == "__main__":
    main()
