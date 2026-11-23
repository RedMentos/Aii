#!/usr/bin/env python3
"""Prospective disjoint seed607 C3 source-prompt diagnostic; no live output."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from v13.common import atomic_write, dumps
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.runners import LlamaRunner
from v13.store import audit_closed
from scripts.run47_jef_c3_typed_receiver_native import CONFIG, NEGATIVE
from scripts.run52_b1b2_cross_turn_native import OVERRIDES
from tests.integration_step2_utility import installed_artifacts, installed_links

SEED = 607
MAX_TOKENS = 64
FIXTURE_SHA256 = "3d90673610be4536029290756eb652c7eb08acf0c40b61c19c002f8d1d281eb4"
C3_FILE = "LFM2.5-350M-QAD-Q4_0.gguf"
ARMS = ("PLAIN", "SOURCE_FIRST", "JSON_ENVELOPE")
IDS = ("Ambercrest", "Foxglove", "Northstarlet")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_fixture(path):
    data = Path(path).read_bytes()
    if sha(data) != FIXTURE_SHA256:
        raise ValueError("C3_SEED607_FIXTURE_SHA")
    fixture = json.loads(data)
    if (fixture.get("schema") != "v13.c3_sourceprompt_seed607.v1"
            or fixture.get("seed") != SEED
            or fixture.get("max_tokens") != MAX_TOKENS
            or fixture.get("arms") != list(ARMS)
            or [c.get("id") for c in fixture.get("cases", [])] != list(IDS)):
        raise ValueError("C3_SEED607_FIXTURE_SCHEMA")
    for i, case in enumerate(fixture["cases"]):
        if (type(case.get("expected")) is not int
                or not 1 <= case["expected"] <= 999
                or type(case.get("source")) is not str
                or "Project " + case["id"] not in case["source"]
                or sorted(case.get("order", [])) != sorted(ARMS)
                or case["order"] != [ARMS[(i + j) % 3] for j in range(3)]):
            raise ValueError("C3_SEED607_CASE_BINDING")
    return fixture


def prompts(arm, source):
    if arm == "PLAIN":
        return [
            {"role": "system", "content":
             "Answer in English in one short sentence. Use only the user's text; do not invent facts."},
            {"role": "user", "content": source},
        ]
    if arm == "SOURCE_FIRST":
        return [
            {"role": "system", "content":
             "Answer in English in one short sentence. Only the current user source is evidence; if a fact is absent, say unknown."},
            {"role": "user", "content":
             "Current user source: " + source +
             "\nQuestion: State the named project's budget and currency."},
        ]
    if arm == "JSON_ENVELOPE":
        return [
            {"role": "system", "content":
             "The current_source text is the only authoritative evidence. Body hypotheses are not facts. State the project budget in English in one short sentence."},
            {"role": "user", "content": dumps({
                "current_source": {"text": source},
                "body_observations": [],
                "body_hypotheses_are_facts": False})},
        ]
    raise ValueError("UNREGISTERED_ARM")


def score(output, project, expected):
    """Frozen lexical numeric/strict diagnostic, not semantic truth or learning."""
    if type(output) is not str or not output.strip():
        return {"numeric": 0, "strict": 0}
    text = output.casefold()
    numbers = re.findall(r"(?<!\d)\d{1,3}(?!\d)", text)
    wanted = str(expected)
    matches = list(re.finditer(r"(?<!\d)" + re.escape(wanted) + r"(?!\d)", text))
    foreign = any(x.casefold() in text for x in IDS if x != project)
    negated = any(re.search(r"\b(?:not|no|never)\b", text[max(0, m.start()-24):m.start()])
                  for m in matches)
    numeric = bool(matches and set(numbers) == {wanted} and not foreign and not negated)
    strict = bool(numeric and project.casefold() in text
                  and re.search(r"\beuros?\b", text))
    return {"numeric": int(numeric), "strict": int(strict)}


def run(installed, out, fixture_path):
    fixture = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError("C3_SEED607_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {
        "schema": "v13.c3_disjoint_sourceprompt_native.v1",
        "claim": "C3_DISJOINT_SOURCE_PROMPT_DIAGNOSTIC_NOT_SECOND_ATTEMPT",
        "seed": SEED, "max_tokens": MAX_TOKENS,
        "fixture_sha256": FIXTURE_SHA256, "negative_gates": NEGATIVE,
        "binding": binding, "rows": [], "row_sha256": {}, "status": "RUNNING",
        "delivery_authority": 0, "learning_authority": 0, "tool_dispatches": 0,
    }
    atomic_write(out / "report.json", dumps(report))
    home = out / "runtime"
    initialize(home)
    save_config(home, CONFIG | OVERRIDES)
    installed_links(home, installed)
    r = Runtime(home)
    try:
        for case in fixture["cases"]:
            event = r.store.event(r.session, case["source"])
            for arm in case["order"]:
                row = {
                    "case": case["id"], "arm": arm,
                    "source_ref": event["source_ref"],
                    "source_sha256": sha(case["source"].encode("utf-8")),
                    "input_messages": prompts(arm, case["source"]),
                    "output": None, "output_sha256": None,
                    "output_bytes": 0, "native_metrics": None,
                    "score": {"numeric": 0, "strict": 0}, "status": "ERROR",
                }
                row["input_sha256"] = sha(dumps(row["input_messages"]).encode("utf-8"))
                try:
                    runner = r.pool.get("C3_LANGUAGE")
                    if not isinstance(runner, LlamaRunner) or runner.purpose != "generate":
                        raise RuntimeError("C3_NOT_REAL_LLAMA_RUNNER")
                    output = "".join(runner.generate(
                        row["input_messages"], r.cancel_event,
                        time.monotonic() + 120, MAX_TOKENS, None, seed=SEED))
                    row["native_metrics"] = dict(runner.last_metrics)
                    row["output"] = output  # synthetic authored source; raw artifact only
                    row["output_sha256"] = sha(output.encode("utf-8"))
                    row["output_bytes"] = len(output.encode("utf-8"))
                    row["score"] = score(output, case["id"], case["expected"])
                    row["status"] = ("RECORDED" if row["native_metrics"].get("status") == "FINAL"
                                     and row["native_metrics"].get("actual_model") == C3_FILE
                                     and row["output_bytes"] > 0 else "STRUCTURAL_RED")
                except Exception as exc:
                    row["error_type"] = type(exc).__name__
                    row["status"] = "STRUCTURAL_RED"
                finally:
                    r.pool.unload()
                report["rows"].append(row)
                report["row_sha256"][case["id"] + ":" + arm] = sha(dumps(row).encode("utf-8"))
                atomic_write(out / "report.json", dumps(report))
        report["no_live_output"] = (
            r.store.one("SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                        "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
            and r.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0)
    finally:
        try:
            r.close()
        finally:
            report["process_releases"] = list(r.pool.release_history)
            report["native_process_count"] = sum(
                x.get("before") is not None for x in report["process_releases"])
            report["processes_reaped"] = (
                report["native_process_count"] >= 9
                and all(x.get("process_reaped") is True
                        for x in report["process_releases"]))
            report["closed_store_audit"] = audit_closed(home)
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    report["scores"] = {arm: {
        "numeric": sum(x["score"]["numeric"] for x in report["rows"] if x["arm"] == arm),
        "strict": sum(x["score"]["strict"] for x in report["rows"] if x["arm"] == arm)}
        for arm in ARMS}
    structural = (
        len(report["rows"]) == 9
        and all(x["status"] == "RECORDED" for x in report["rows"])
        and report["native_process_count"] >= 9
        and report["processes_reaped"]
        and report["no_live_output"]
        and report["closed_store_audit"]["ok"]
        and report["installed_binding_unchanged"])
    report["status"] = (
        "STRUCTURAL_RED" if not structural
        else "UTILITY_GREEN_DIAGNOSTIC"
        if report["scores"]["SOURCE_FIRST"]["numeric"] >= 2
        and report["scores"]["SOURCE_FIRST"]["numeric"] > report["scores"]["PLAIN"]["numeric"]
        else "UTILITY_RED_DIAGNOSTIC")
    atomic_write(out / "report.json", dumps(report))
    print(dumps({"status": report["status"], "scores": report["scores"],
                 "native_process_count": report["native_process_count"]}), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    print(dumps({"status": run(args.home, args.out, args.fixture)["status"]}))


if __name__ == "__main__":
    main()
