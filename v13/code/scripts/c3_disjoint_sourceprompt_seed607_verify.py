#!/usr/bin/env python3
"""Independent source-bound replay of seed607 nine-call C3 native diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from v13.common import dumps
from scripts.run47_jef_c3_typed_receiver_native import NEGATIVE

FIXTURE_SHA256 = "3d90673610be4536029290756eb652c7eb08acf0c40b61c19c002f8d1d281eb4"
C3_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
C3_FILE = "LFM2.5-350M-QAD-Q4_0.gguf"
ARMS = ("PLAIN", "SOURCE_FIRST", "JSON_ENVELOPE")
IDS = ("Ambercrest", "Foxglove", "Northstarlet")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def score_again(output, project, amount):
    """Independent implementation of frozen numeric/strict scoring contract."""
    if not isinstance(output, str) or not output.strip():
        return {"numeric": 0, "strict": 0}
    text = output.casefold()
    amounts = re.findall(r"\b[0-9]{1,3}\b", text)
    wanted = str(amount)
    locations = [m.start() for m in re.finditer(r"\b" + re.escape(wanted) + r"\b", text)]
    wrong_project = any(other.casefold() in text for other in IDS if other != project)
    negated = any(re.search(r"\b(no|not|never)\b", text[max(0, pos-24):pos])
                  for pos in locations)
    numeric = bool(locations and set(amounts) == {wanted}
                   and not wrong_project and not negated)
    strict = bool(numeric and project.casefold() in text
                  and re.search(r"\beuros?\b", text))
    return {"numeric": int(numeric), "strict": int(strict)}


def verify(report_path, fixture_path):
    raw = Path(fixture_path).read_bytes()
    errors = []

    def require(ok, key):
        if not ok:
            errors.append(key)

    require(sha(raw) == FIXTURE_SHA256, "fixture_sha")
    try:
        fixture = json.loads(raw)
        report = json.loads(Path(report_path).read_text())
    except Exception:
        return {"status": "STRUCTURAL_RED", "errors": ["parse"]}
    require(fixture.get("seed") == 607 and len(fixture.get("cases", [])) == 3,
            "fixture_schema")
    require(report.get("schema") == "v13.c3_disjoint_sourceprompt_native.v1"
            and report.get("seed") == 607 and report.get("max_tokens") == 64
            and report.get("fixture_sha256") == FIXTURE_SHA256, "report_pin")
    require(report.get("claim") == "C3_DISJOINT_SOURCE_PROMPT_DIAGNOSTIC_NOT_SECOND_ATTEMPT",
            "claim")
    require(report.get("negative_gates") == NEGATIVE, "negative_gates")
    require(report.get("delivery_authority") == 0
            and report.get("learning_authority") == 0
            and report.get("tool_dispatches") == 0
            and report.get("no_live_output") is True, "no_delivery")
    binding = report.get("binding") or {}
    require((binding.get("model_sha256") or {}).get("C3_LANGUAGE") == C3_SHA,
            "model_pin")
    require(binding.get("runner_sha256") == RUNNER_SHA
            and report.get("installed_binding_unchanged") is True,
            "runner_pin")
    require((report.get("closed_store_audit") or {}).get("ok") is True,
            "closed_sqlite")
    require(report.get("native_process_count", 0) >= 9
            and report.get("processes_reaped") is True, "native_processes")
    releases = report.get("process_releases") or []
    require(sum(x.get("before") is not None for x in releases) >= 9
            and all(x.get("process_reaped") is True for x in releases),
            "process_release_raw")
    rows = report.get("rows") or []
    require(type(rows) is list and len(rows) == 9, "row_count")
    if type(rows) is not list or len(rows) != 9:
        return {"status": "STRUCTURAL_RED", "errors": errors}
    totals = {a: {"numeric": 0, "strict": 0} for a in ARMS}
    expected_order = [(c["id"], arm) for c in fixture["cases"] for arm in c["order"]]
    require([(r.get("case"), r.get("arm")) for r in rows] == expected_order,
            "latin_order")
    for case in fixture["cases"]:
        project, amount, source = case["id"], case["expected"], case["source"]
        for arm in case["order"]:
            row = next((r for r in rows if r.get("case") == project
                        and r.get("arm") == arm), None)
            if row is None:
                errors.append("missing_" + project + "_" + arm)
                continue
            key = project + ":" + arm
            require((report.get("row_sha256") or {}).get(key)
                    == sha(dumps(row).encode("utf-8")), "row_sha_" + key)
            ref = row.get("source_ref") or {}
            require(ref.get("sha256") == sha(source.encode("utf-8"))
                    and row.get("source_sha256") == sha(source.encode("utf-8"))
                    and ref.get("char_start") == 0
                    and ref.get("char_end") == len(source), "source_" + key)
            messages = row.get("input_messages") or []
            require(len(messages) == 2 and row.get("input_sha256")
                    == sha(dumps(messages).encode("utf-8")), "input_sha_" + key)
            if len(messages) == 2:
                user = messages[1].get("content", "")
                require(source in user, "input_source_" + key)
                if arm == "JSON_ENVELOPE":
                    try:
                        data = json.loads(user)
                        require(data["current_source"]["text"] == source
                                and data["body_observations"] == []
                                and data["body_hypotheses_are_facts"] is False,
                                "json_envelope_" + key)
                    except Exception:
                        errors.append("json_parse_" + key)
                elif arm == "SOURCE_FIRST":
                    require(user.startswith("Current user source: " + source),
                            "source_first_" + key)
                else:
                    require(user == source, "plain_" + key)
            metrics = row.get("native_metrics") or {}
            require(row.get("status") == "RECORDED"
                    and metrics.get("status") == "FINAL"
                    and metrics.get("actual_model") == C3_FILE, "native_" + key)
            output = row.get("output")
            require(type(output) is str and len(output.encode("utf-8")) > 0
                    and row.get("output_sha256") == sha(output.encode("utf-8"))
                    and row.get("output_bytes") == len(output.encode("utf-8")),
                    "output_" + key) if type(output) is str else errors.append("output_" + key)
            observed = score_again(output, project, amount)
            require(row.get("score") == observed, "score_" + key)
            for metric in ("numeric", "strict"):
                totals[arm][metric] += observed[metric]
    require(report.get("scores") == totals, "totals")
    utility = (totals["SOURCE_FIRST"]["numeric"] >= 2
               and totals["SOURCE_FIRST"]["numeric"] > totals["PLAIN"]["numeric"])
    expected_status = "UTILITY_GREEN_DIAGNOSTIC" if utility else "UTILITY_RED_DIAGNOSTIC"
    require(report.get("status") == expected_status, "utility_status")
    return {"status": "STRUCTURAL_RED" if errors else expected_status,
            "errors": errors, "scores": totals,
            "claim": "C3_DISJOINT_PROMPT_ONLY_NO_SECOND_ATTEMPT_OR_PROMOTION"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    result = verify(args.report, args.fixture)
    print(json.dumps(result, sort_keys=True))
    if result["status"] != "UTILITY_GREEN_DIAGNOSTIC":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
