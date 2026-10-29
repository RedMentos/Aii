"""Run126 serial matched C3 native replay of source-exact historical rule transport.

This is an isolated Linux-native diagnostic, NOT a runtime integration,
learning experiment, Redmi proof or canonical STEP2 promotion.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import time

from scripts import calc_tool_ablation as w2
from scripts import step2_exact_rule_native_replay_preflight as preflight
from scripts import step2_longnote_tp27_native_pilot as tp
from scripts import step2_tool_replay as tool
from v13.common import atomic_write, digest, dumps, file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.utility import score_decision
import integration_step2_utility as step2

C3_SEED = 13
BODY_SOURCE_SEED = 20
MODEL_HASHES = {
    "B1_DETAIL": "bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1",
    "B2_GIST": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
    "C3_LANGUAGE": "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d",
}
EXPECTED_ROWS = 84


def require(ok, message):
    if not ok:
        raise ValueError(message)


def execution_order(index):
    """Counterbalance deterministic prompt order without changing C3 seed."""
    return ("control", "treatment") if index % 2 == 0 else ("treatment", "control")


def verify_input(source_path, prepared_path):
    source = preflight.load_original(source_path)
    expected = preflight.transform(source)
    prepared_path = Path(prepared_path).resolve()
    require(prepared_path.is_file(), "MISSING_PREFLIGHT_REPORT")
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    require(digest(dumps(prepared)) == digest(dumps(expected))
            and prepared.get("status") == "SOFTWARE_PREPARED_NATIVE_NOT_LAUNCHED"
            and prepared.get("pair_count") == 42
            and prepared.get("native_calls") == 0
            and prepared.get("canonical_gate_pass") is False,
            "PREFLIGHT_BYTES_OR_STRUCTURE_DRIFT")
    return source, prepared


def action_from_answer(answer):
    try:
        value = json.loads(answer)
    except (TypeError, ValueError):
        return "INVALID"
    action = value.get("action") if isinstance(value, dict) else None
    return action if action in ("A", "B", "NONE", "UNKNOWN") else "INVALID"


def summarize(rows, fixtures):
    """Recompute summaries from rows, never from a stored success flag."""
    oracle = {f["id"]: f["oracle"]["action"] for f in fixtures}
    out = {}
    for mode in ("control", "treatment"):
        out[mode] = {}
        for variant in preflight.VARIANTS:
            subset = [r for r in rows if r["mode"] == mode and r["variant"] == variant]
            require(len(subset) == len(preflight.PROJECTS)
                    and {r["fixture"] for r in subset} == set(preflight.PROJECTS),
                    "INCOMPLETE_VARIANT_PAIR:" + mode + ":" + variant)
            actions = [r["action"] for r in subset]
            wrong = sum(a in ("A", "B", "NONE") and a != oracle[r["fixture"]]
                        for a, r in zip(actions, subset))
            exact = sum(a == oracle[r["fixture"]] for a, r in zip(actions, subset))
            unknown = sum(a == "UNKNOWN" for a in actions)
            mean = sum(r["score"]["utility"] for r in subset) / len(subset)
            out[mode][variant] = {
                "rows": len(subset), "decision_exact": exact,
                "unknown": unknown, "wrong_committed": wrong,
                "full_json_exact": sum(bool(r["score"]["exact"]) for r in subset),
                "mean_utility": mean,
            }
    return out


def run(installed_home, source_path, prepared_path, evidence_dir):
    installed_home = Path(installed_home).resolve()
    source_path = Path(source_path).resolve()
    prepared_path = Path(prepared_path).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    require(installed_home.is_dir()
            and (installed_home / "config/models.json").is_file()
            and not evidence_dir.exists()
            and evidence_dir.parent.is_dir(), "FRESH_HOME_AND_EVIDENCE_REQUIRED")
    source, prepared = verify_input(source_path, prepared_path)
    before = tp.pinned_models(installed_home)
    require(before == MODEL_HASHES, "PINNED_MODEL_HASH_DRIFT")
    require(tool.SEED == C3_SEED and len(prepared["rows"]) == 42
            and source["fixture_sha256"] == preflight.ORIGINAL_FIXTURE_SHA256,
            "FROZEN_C3_SEED_OR_FIXTURE_DRIFT")
    evidence_dir.mkdir(mode=0o700)
    receipt_path = evidence_dir / "RECEIPT.json"
    rows_path = evidence_dir / "NATIVE_ROWS.json"
    receipt = {
        "schema": "v13.step2.exact_rule_transport_matched_native.v1",
        "status": "RUNNING", "source_report_sha256": file_hash(source_path),
        "preflight_report_sha256": file_hash(prepared_path),
        "fixture_sha256": preflight.ORIGINAL_FIXTURE_SHA256,
        "model_hashes_before": before,
        "body_source_seed": BODY_SOURCE_SEED, "c3_seed": C3_SEED,
        "native_scope": "LINUX_C3_42_MATCHED_PAIRS_84_CALLS",
        "rows": 0, "canonical_gate_pass": False,
        "step2_status": "UTILITY_FAIL", "age_authority": 0,
        "jepa_weight": 0, "weight_updates": False,
        "redmi_measured": False, "whole_system_complete": False,
    }
    def save():
        atomic_write(receipt_path, dumps(receipt))
    save()
    cfg = dict(source["config"])
    home = evidence_dir / "fresh-home"
    initialize(home)
    save_config(home, cfg)
    step2.installed_links(home, installed_home)
    runtime = None
    raw = {"schema": "v13.step2.exact_rule_transport_native_rows.v1",
           "status": "RUNNING", "rows": [], "row_sha256": {},
           "canonical_gate_pass": False, "phone_measured": False}
    try:
        runtime = Runtime(home)
        runner = runtime.pool.get("C3_LANGUAGE")
        fixtures = {f["id"]: f for f in source["fixtures"]}
        for index, pair in enumerate(prepared["rows"]):
            for mode in execution_order(index):
                messages = pair[mode + "_messages"]
                require(digest(dumps(messages)) == pair[mode + "_sha256"],
                        "CONSUMER_MESSAGE_HASH_DRIFT")
                key = pair["fixture"] + ":" + pair["variant"] + ":" + mode
                row = {
                    "fixture": pair["fixture"], "variant": pair["variant"],
                    "mode": mode, "injected": pair["injected"] if mode == "treatment" else False,
                    "source_row_sha256": pair["source_row_sha256"],
                    "consumer_messages_sha256": pair[mode + "_sha256"],
                    "oracle_visible_to_native": False,
                    "raw_answer": "", "status": "RUNNING",
                }
                started = time.monotonic()
                try:
                    deadline = time.monotonic() + cfg["deadline_seconds"]
                    for chunk in runner.generate(
                            messages, runtime.cancel_event, deadline,
                            cfg["answer_tokens"], w2.EXTRACT_SCHEMA, seed=C3_SEED):
                        row["raw_answer"] += chunk
                    row["consumer_metrics"] = dict(runner.last_metrics)
                    answer, row["tool"] = tool.tool_answer(row["raw_answer"], messages)
                    row["answer"] = answer or row["raw_answer"]
                    row["action"] = action_from_answer(row["answer"])
                    row["score"] = score_decision(
                        row["answer"], fixtures[pair["fixture"]]["oracle"])
                    row["status"] = (
                        "RECORDED" if runner.last_metrics.get("status") == "FINAL"
                        else "STRUCTURAL_FAIL")
                except BaseException as exc:
                    row.update(status="ERROR", error_type=type(exc).__name__,
                               error=str(exc)[:500],
                               score={"utility": 0., "exact": False,
                                      "contradictions": ["native_exception"]},
                               action="INVALID")
                    row["elapsed_s"] = time.monotonic() - started
                    raw["rows"].append(row)
                    raw["row_sha256"][key] = digest(dumps(row))
                    atomic_write(rows_path, dumps(raw))
                    receipt["rows"] = len(raw["rows"])
                    receipt["status"] = "FAIL_RETAIN_RAW"
                    save()
                    raise
                row["elapsed_s"] = time.monotonic() - started
                raw["rows"].append(row)
                raw["row_sha256"][key] = digest(dumps(row))
                atomic_write(rows_path, dumps(raw))
                receipt["rows"] = len(raw["rows"])
                save()
        require(len(raw["rows"]) == EXPECTED_ROWS
                and len(raw["row_sha256"]) == EXPECTED_ROWS
                and all(r["status"] == "RECORDED"
                        and r["consumer_metrics"].get("status") == "FINAL"
                        for r in raw["rows"]), "NATIVE_84_ROWS_INCOMPLETE")
        summaries = summarize(raw["rows"], source["fixtures"])
        wrong = sum(v["wrong_committed"] for v in summaries["treatment"].values())
        receipt["summary"] = summaries
        receipt["treatment_wrong_committed"] = wrong
        receipt["model_hashes_after"] = tp.pinned_models(installed_home)
        require(receipt["model_hashes_after"] == before,
                "PINNED_MODEL_BYTES_CHANGED")
        raw["status"] = ("PASS_SCOPED_NATIVE_TRANSPORT_NO_GATE" if wrong == 0
                         else "FAIL_SCOPED_WRONG_COMMITTED_NO_GATE")
        atomic_write(rows_path, dumps(raw))
        receipt["native_rows_sha256"] = file_hash(rows_path)
        receipt["status"] = raw["status"]
    except BaseException as exc:
        receipt["status"] = "FAIL_RETAIN_RAW"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)[:500]
        save()
        raise
    finally:
        if runtime is not None:
            runtime.close()
    save()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-home", type=Path, required=True)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--preflight-report", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = run(args.installed_home, args.source_report,
                  args.preflight_report, args.evidence_dir)
    print(json.dumps({"status": receipt["status"], "rows": receipt["rows"],
                      "canonical_gate_pass": False}, sort_keys=True))
    return 0 if receipt["status"] == "PASS_SCOPED_NATIVE_TRANSPORT_NO_GATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
