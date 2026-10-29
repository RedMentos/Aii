"""Run113 Atlas CQP/s20: serial Linux-native one-fixture STEP2 + bounded tool replay.

A single preregistered pilot. No canonical STEP2 gate or age/learning promotion.
Never run while another native owner is active. All failed raw evidence retained.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from scripts import run111_step2_fresh_native_preflight as pre
from scripts import step2_longnote_tp27_native_pilot as tp
from v13.common import atomic_write, digest, dumps, file_hash

ROOT = Path(__file__).resolve().parents[1]
z2, z2b = pre.z2, pre.z2b
ARM = "CQP"
SEED = 20
FIXTURE_ID = "Atlas"
VARIANTS = pre.VARIANTS
FIXTURE_SHA256 = "b8896bfba0c6c323ba1dafd12bc788e7f378bbf5d23c96e5074b3b1d058ef1d1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prereg():
    dry = pre.dry_run()
    reg = dry["registration"]
    require(dry["native_execution"] is False and
            reg["fixture_sha256"] == FIXTURE_SHA256 and
            reg["projects"][0] == FIXTURE_ID and
            reg["seeds"] == [20, 21, 22] and
            reg["arms"][ARM]["body"] == "two_distinct" and
            reg["arms"][ARM]["pointer"] is True and
            reg["arms"][ARM]["query"] is True and
            reg["arms"][ARM]["settings_by_seed"]["20"] == pre.settings(ARM, SEED) and
            reg["registered_native_rows"] == 378 and
            tuple(reg["variants"]) == VARIANTS, "RUN113_PREREG_DRIFT")
    return dry


def verify_source(report, counts, model_hashes):
    rows = report.get("rows", [])
    require(
        report.get("status") == "DIAGNOSTIC_INCOMPLETE"
        and report.get("canonical_gate_pass") is False
        and report.get("phone_measured") is False
        and report.get("all_structural_checks_passed") is True
        and report.get("source_unchanged") is True
        and report.get("installed_artifacts_unchanged") is True
        and report.get("distinct_bodies") is True
        and report.get("fixture_sha256") == FIXTURE_SHA256
        and len(report.get("fixtures", [])) == 6
        and len(report.get("preparations", [])) == 1
        and report["preparations"][0].get("fixture") == FIXTURE_ID
        and report["preparations"][0].get("status") == "RECORDED"
        and report["preparations"][0].get("model_sha256") == model_hashes
        and counts == {"offers": 12, "with_question": 12}
        and len(rows) == len(VARIANTS)
        and {(row.get("fixture"), row.get("variant")) for row in rows}
            == {(FIXTURE_ID, v) for v in VARIANTS},
        "RUN113_SOURCE_STRUCTURAL_FAIL")
    for row in rows:
        key = row["fixture"] + ":" + row["variant"]
        require(report["row_sha256"].get(key) == digest(dumps(row))
                and row.get("status") == "RECORDED"
                and row.get("processes_reaped") is True
                and row.get("oracle_visible_to_native") is False
                and row.get("native_consumer_metrics", {}).get("status") == "FINAL"
                and isinstance(row.get("consumer_messages"), list),
                "RUN113_SOURCE_ROW_FAIL:" + key)
    return {"rows": len(rows), "status": "PASS_SCOPED_ONE_FIXTURE_SOURCE_ONLY"}


def private_tool_replay():
    """Private copy; adapt ONLY the input status guard for the sealed 7-row pilot.

    Original step2_tool_replay.recorded continues to require full cohort.
    """
    spec = importlib.util.spec_from_file_location(
        "run113_private_tool_replay", ROOT / "scripts/step2_tool_replay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def one_fixture_recorded(report_path):
        report = json.loads(Path(report_path).read_text())
        require(report.get("status") == "DIAGNOSTIC_INCOMPLETE"
                and report.get("all_structural_checks_passed") is True
                and report.get("canonical_gate_pass") is False
                and report.get("fixture_sha256") == FIXTURE_SHA256
                and len(report.get("rows", [])) == len(VARIANTS)
                and {r.get("fixture") for r in report["rows"]} == {FIXTURE_ID}
                and {r.get("variant") for r in report["rows"]} == set(VARIANTS)
                and report.get("wire_arm", {}).get("arm") == "w1",
                "RUN113_REPLAY_INPUT_REFUSED")
        for row in report["rows"]:
            key = row["fixture"] + ":" + row["variant"]
            require(report["row_sha256"].get(key) == digest(dumps(row))
                    and row.get("oracle_visible_to_native") is False
                    and row.get("native_consumer_metrics", {}).get("status") == "FINAL",
                    "RUN113_REPLAY_INPUT_ROW_REFUSED:" + key)
        return report

    module.recorded = one_fixture_recorded
    return module


def verify_tool(source, tool):
    require(tool.get("status") == "TOOL_UTILITY_FAIL"
            and tool.get("canonical_gate_pass") is False
            and tool.get("phone_measured") is False
            and tool.get("installed_artifacts_unchanged") is True
            and len(tool.get("rows", [])) == len(VARIANTS)
            and tool.get("paired_tool", {}).get("complete") is False,
            "RUN113_TOOL_STRUCTURAL_FAIL")
    by_variant = {r["variant"]: r for r in source["rows"]}
    for row in tool["rows"]:
        key = row["fixture"] + ":" + row["variant"]
        require(row["fixture"] == FIXTURE_ID
                and row["variant"] in VARIANTS
                and row["status"] == "RECORDED"
                and row["oracle_visible_to_native"] is False
                and row.get("consumer_metrics", {}).get("status") == "FINAL"
                and row["consumer_messages_sha256"]
                    == digest(dumps(by_variant[row["variant"]]["consumer_messages"]))
                and tool["row_sha256"].get(key) == digest(dumps(row)),
                "RUN113_TOOL_ROW_FAIL:" + key)
    wrong = sum(v["wrong_committed"] for v in tool["summary"]["tool"].values())
    require(wrong == 0, "RUN113_TOOL_WRONG_COMMIT")
    return {"rows": len(tool["rows"]), "wrong_committed": wrong,
            "status": "PASS_SCOPED_ONE_FIXTURE_TOOL_NO_GATE"}


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
        "schema": "v13.run113.atlas_cqp_s20.native_pilot.v1",
        "status": "RUNNING", "arm": ARM, "seed": SEED,
        "fixture_id": FIXTURE_ID, "fixture_limit": 1,
        "registration_sha256": dry["registration_sha256"],
        "fixture_sha256": FIXTURE_SHA256,
        "model_hashes_before": model_before,
        "scope": "LINUX_NATIVE_ONE_FIXTURE_SEVEN_SOURCE_PLUS_SEVEN_TOOL",
        "age_authority": 0, "jepa_weight": 0,
        "weight_updates": False, "redmi_measured": False,
        "canonical_gate_pass": False, "whole_system_complete": False,
    }
    receipt_path = evidence_dir / "RECEIPT.json"
    def save():
        atomic_write(receipt_path, dumps(receipt))
    save()
    try:
        with pre.configured():
            step2 = z2.harness()
            require(z2 is z2b.z2 and step2.FIXTURES is z2.FIXTURES
                    and step2.FIXTURES[0]["id"] == FIXTURE_ID,
                    "PRIVATE_FIXTURE_ALIAS_DRIFT")
            with z2b.Patches(step2, query=True) as patch:
                arm_home = z2.sibling_home(
                    installed_home, evidence_dir / "cqp20-home", pre.settings(ARM, SEED))
                source_path = evidence_dir / "STEP2_RAW.json"
                source = step2.run_locked(arm_home, source_path, fixture_limit=1)
                counts = dict(patch.count)
        receipt["source_report_sha256"] = file_hash(source_path)
        receipt["source_guard"] = verify_source(source, counts, model_before)
        receipt["queried_offers"] = counts
        receipt["source_variant_utility"] = {
            r["variant"]: r["score"]["utility"] for r in source["rows"]}
        replay = private_tool_replay()
        tool_path = evidence_dir / "TOOL_RAW.json"
        tool = replay.run(arm_home, source_path, tool_path)
        receipt["tool_report_sha256"] = file_hash(tool_path)
        receipt["tool_guard"] = verify_tool(source, tool)
        receipt["tool_variant_utility"] = {
            r["variant"]: r["score"]["utility"] for r in tool["rows"]}
        receipt["model_hashes_after"] = tp.pinned_models(installed_home)
        require(receipt["model_hashes_after"] == model_before,
                "PINNED_MODEL_BYTES_CHANGED")
        receipt["status"] = "PASS_SCOPED_ATLAS_CQP20_NATIVE_NO_UTILITY_GATE"
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
    result = run(args.installed_home, args.evidence_dir)
    print(json.dumps({"status": result["status"], "fixture": FIXTURE_ID,
                      "source": result["source_guard"],
                      "tool": result["tool_guard"]}, sort_keys=True))
    return 0 if result["status"].startswith("PASS_SCOPED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
