"""Run115: six frozen fresh STEP2 fixtures, CQP/s20, serial genuine B1/B2 and C3.

Review-only Linux-native diagnostic. The seven-variant six-fixture source and
tool replays never promote the canonical STEP2, Age0 or learning gates.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from scripts import run111_step2_fresh_native_preflight as pre
from scripts import step2_longnote_tp27_native_pilot as tp
from v13.common import atomic_write, digest, dumps, file_hash

ROOT = Path(__file__).resolve().parents[1]
ARM = "CQP"
SEED = 20
FIXTURE_IDS = pre.EXPECTED_PROJECTS
VARIANTS = pre.VARIANTS
FIXTURE_SHA256 = pre.FIXTURE_SHA256
EXPECTED_ROWS = len(FIXTURE_IDS) * len(VARIANTS)
EXPECTED_OFFERS = len(FIXTURE_IDS) * 12


def require(ok, message):
    if not ok:
        raise ValueError(message)


def prereg():
    dry = pre.dry_run()
    reg = dry["registration"]
    require(dry["native_execution"] is False
            and reg["fixture_sha256"] == FIXTURE_SHA256
            and tuple(reg["projects"]) == FIXTURE_IDS
            and reg["seeds"] == [20, 21, 22]
            and reg["arms"][ARM]["body"] == "two_distinct"
            and reg["arms"][ARM]["pointer"] is True
            and reg["arms"][ARM]["query"] is True
            and reg["arms"][ARM]["settings_by_seed"]["20"] == pre.settings(ARM, SEED)
            and reg["registered_native_rows"] == 378
            and tuple(reg["variants"]) == VARIANTS,
            "RUN115_PREREG_DRIFT")
    return dry


def row_pairs(rows):
    return [(r.get("fixture"), r.get("variant")) for r in rows]


def exact_pairs():
    return {(f, v) for f in FIXTURE_IDS for v in VARIANTS}


def verify_source(report, counts, model_hashes):
    rows = report.get("rows", [])
    preps = report.get("preparations", [])
    require(report.get("status") in ("UTILITY_FAIL", "UTILITY_PASS_SCOPED")
            and report.get("canonical_gate_pass") is False
            and report.get("phone_measured") is False
            and report.get("all_structural_checks_passed") is True
            and report.get("source_unchanged") is True
            and report.get("installed_artifacts_unchanged") is True
            and report.get("distinct_bodies") is True
            and report.get("same_weight_file") is False
            and report.get("fixture_sha256") == FIXTURE_SHA256
            and len(report.get("fixtures", [])) == len(FIXTURE_IDS)
            and pre._canonical_sha(report["fixtures"]) == FIXTURE_SHA256
            and tuple(f["id"] for f in report["fixtures"]) == FIXTURE_IDS
            and report.get("paired", {}).get("complete") is True
            and len(preps) == len(FIXTURE_IDS)
            and {p.get("fixture") for p in preps} == set(FIXTURE_IDS)
            and all(p.get("status") == "RECORDED"
                    and p.get("model_sha256") == model_hashes for p in preps)
            and counts == {"offers": EXPECTED_OFFERS,
                           "with_question": EXPECTED_OFFERS}
            and len(rows) == EXPECTED_ROWS
            and len(set(row_pairs(rows))) == EXPECTED_ROWS
            and set(row_pairs(rows)) == exact_pairs(),
            "RUN115_SOURCE_STRUCTURAL_FAIL")
    for row in rows:
        key = row["fixture"] + ":" + row["variant"]
        require(report.get("row_sha256", {}).get(key) == digest(dumps(row))
                and row.get("status") == "RECORDED"
                and row.get("processes_reaped") is True
                and row.get("oracle_visible_to_native") is False
                and row.get("native_consumer_metrics", {}).get("status") == "FINAL"
                and isinstance(row.get("consumer_messages"), list),
                "RUN115_SOURCE_ROW_FAIL:" + key)
    return {"rows": EXPECTED_ROWS, "paired_complete": True,
            "status": "PASS_SCOPED_SIX_FIXTURE_SOURCE_STRUCTURAL_ONLY"}


def private_tool_replay():
    """Use frozen replay logic; override only its full-cohort input guard."""
    spec = importlib.util.spec_from_file_location(
        "run115_private_tool_replay", ROOT / "scripts/step2_tool_replay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def recorded(report_path):
        report = json.loads(Path(report_path).read_text())
        rows = report.get("rows", [])
        require(report.get("status") in ("UTILITY_FAIL", "UTILITY_PASS_SCOPED")
                and report.get("all_structural_checks_passed") is True
                and report.get("canonical_gate_pass") is False
                and report.get("fixture_sha256") == FIXTURE_SHA256
                and pre._canonical_sha(report.get("fixtures", [])) == FIXTURE_SHA256
                and report.get("paired", {}).get("complete") is True
                and len(rows) == EXPECTED_ROWS
                and len(set(row_pairs(rows))) == EXPECTED_ROWS
                and set(row_pairs(rows)) == exact_pairs()
                and report.get("wire_arm", {}).get("arm") == "w1",
                "RUN115_REPLAY_INPUT_REFUSED")
        for row in rows:
            key = row["fixture"] + ":" + row["variant"]
            require(report.get("row_sha256", {}).get(key) == digest(dumps(row))
                    and row.get("oracle_visible_to_native") is False
                    and row.get("native_consumer_metrics", {}).get("status") == "FINAL",
                    "RUN115_REPLAY_ROW_REFUSED:" + key)
        return report

    module.recorded = recorded
    return module


def verify_tool(source, tool):
    rows = tool.get("rows", [])
    require(tool.get("status") in ("TOOL_UTILITY_FAIL", "TOOL_UTILITY_PASS_SCOPED")
            and tool.get("canonical_gate_pass") is False
            and tool.get("phone_measured") is False
            and tool.get("installed_artifacts_unchanged") is True
            and tool.get("paired_tool", {}).get("complete") is True
            and len(rows) == EXPECTED_ROWS
            and len(set(row_pairs(rows))) == EXPECTED_ROWS
            and set(row_pairs(rows)) == exact_pairs(),
            "RUN115_TOOL_STRUCTURAL_FAIL")
    by_pair = {(r["fixture"], r["variant"]): r for r in source["rows"]}
    for row in rows:
        key = row["fixture"] + ":" + row["variant"]
        src = by_pair[(row["fixture"], row["variant"])]
        require(row.get("status") == "RECORDED"
                and row.get("oracle_visible_to_native") is False
                and row.get("consumer_metrics", {}).get("status") == "FINAL"
                and row.get("consumer_messages_sha256")
                    == digest(dumps(src["consumer_messages"]))
                and tool.get("row_sha256", {}).get(key) == digest(dumps(row)),
                "RUN115_TOOL_ROW_FAIL:" + key)
    summary = tool.get("summary", {}).get("tool", {})
    require(set(summary) == set(VARIANTS)
            and all(summary[v].get("rows") == len(FIXTURE_IDS) for v in VARIANTS),
            "RUN115_TOOL_SUMMARY_INCOMPLETE")
    wrong = sum(summary[v]["wrong_committed"] for v in VARIANTS)
    require(wrong == 0, "RUN115_TOOL_WRONG_COMMITTED")
    return {"rows": EXPECTED_ROWS, "wrong_committed": wrong,
            "paired_complete": True,
            "status": "PASS_SCOPED_SIX_FIXTURE_TOOL_STRUCTURAL_NO_GATE"}


def run(installed_home, evidence_dir):
    dry = prereg()
    installed_home = Path(installed_home).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    require(installed_home.is_dir()
            and (installed_home / "config/models.json").is_file()
            and not evidence_dir.exists() and evidence_dir.parent.is_dir(),
            "FRESH_INSTALLED_HOME_AND_EVIDENCE_REQUIRED")
    model_before = tp.pinned_models(installed_home)
    evidence_dir.mkdir(mode=0o700)
    receipt = {
        "schema": "v13.run115.six_fixture_cqp_s20.native.v1",
        "status": "RUNNING", "arm": ARM, "seed": SEED,
        "fixture_ids": list(FIXTURE_IDS), "fixture_limit": len(FIXTURE_IDS),
        "registration_sha256": dry["registration_sha256"],
        "fixture_sha256": FIXTURE_SHA256,
        "model_hashes_before": model_before,
        "scope": "LINUX_NATIVE_SIX_FIXTURES_42_SOURCE_PLUS_42_TOOL",
        "age_authority": 0, "jepa_weight": 0, "weight_updates": False,
        "redmi_measured": False, "canonical_gate_pass": False,
        "whole_system_complete": False,
    }
    receipt_path = evidence_dir / "RECEIPT.json"

    def save():
        atomic_write(receipt_path, dumps(receipt))

    save()
    try:
        with pre.configured():
            step2 = pre.z2.harness()
            require(pre.z2 is pre.z2b.z2
                    and step2.FIXTURES is pre.z2.FIXTURES
                    and tuple(f["id"] for f in step2.FIXTURES) == FIXTURE_IDS,
                    "PRIVATE_FIXTURE_ALIAS_DRIFT")
            with pre.z2b.Patches(step2, query=True) as patch:
                arm_home = pre.z2.sibling_home(
                    installed_home, evidence_dir / "cqp20-home",
                    pre.settings(ARM, SEED))
                source_path = evidence_dir / "STEP2_RAW.json"
                source = step2.run_locked(
                    arm_home, source_path, fixture_limit=len(FIXTURE_IDS))
                counts = dict(patch.count)
        source["wire_arm"] = {"arm": "w1", "note": "live wire"}
        source["z2b_queried_offers"] = counts
        atomic_write(source_path, dumps(source))
        receipt["source_report_sha256"] = file_hash(source_path)
        receipt["source_guard"] = verify_source(source, counts, model_before)
        receipt["queried_offers"] = counts
        receipt["source_variant_utility"] = {
            v: sum(r["score"]["utility"] for r in source["rows"]
                   if r["variant"] == v) / len(FIXTURE_IDS) for v in VARIANTS}
        receipt["source_paired"] = source["paired"]
        save()
        replay = private_tool_replay()
        tool_path = evidence_dir / "TOOL_RAW.json"
        tool = replay.run(arm_home, source_path, tool_path)
        receipt["tool_report_sha256"] = file_hash(tool_path)
        receipt["tool_guard"] = verify_tool(source, tool)
        receipt["tool_variant_utility"] = {
            v: tool["summary"]["tool"][v]["mean_utility"] for v in VARIANTS}
        receipt["source_no_tool_summary"] = tool["summary"]["no_tool_w1"]
        receipt["tool_summary"] = tool["summary"]["tool"]
        receipt["tool_paired"] = tool["paired_tool"]
        receipt["model_hashes_after"] = tp.pinned_models(installed_home)
        require(receipt["model_hashes_after"] == model_before,
                "PINNED_MODEL_BYTES_CHANGED")
        receipt["status"] = "PASS_SCOPED_SIX_FIXTURE_CQP20_NATIVE_NO_CANON_GATE"
    except BaseException as exc:
        receipt["status"] = "FAIL_RETAIN_RAW"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)[:500]
        save()
        raise
    save()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-home", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    receipt = run(args.installed_home, args.evidence_dir)
    print(json.dumps({"status": receipt["status"],
                      "source": receipt["source_guard"],
                      "tool": receipt["tool_guard"]}, sort_keys=True))
    return 0 if receipt["status"].startswith("PASS_SCOPED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
