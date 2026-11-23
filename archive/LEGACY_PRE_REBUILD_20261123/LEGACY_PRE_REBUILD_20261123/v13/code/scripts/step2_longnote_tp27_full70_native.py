"""Frozen TP/s27 ten-fixture STEP2 Linux-native arm plus C3 tool replay.

This is ONE preregistered arm, not the four-arm/three-seed STEP2 proof.
No live Runtime wiring, model update, Age authority or gate promotion.
Original partial reports remain on disk if any stage fails.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import step2_longnote_tp27_native_pilot as pilot
from scripts import step2_longnote_runner_preflight as pre
from scripts import step2_z2b_seeds as z2b
from scripts.step2_fourarm_native_collector_candidate import verify_native_reports
from v13.common import atomic_write, digest, dumps

ARM = "TP"
SEED = 27
FIXTURE_IDS = tuple(x["id"] for x in pre.corpus.FIXTURES)
EXPECTED_IDS = ("Aquila", "Bellatrix", "Cetus", "Deneb", "Erebos",
                "Fomalhaut", "Ganymede", "Hyperion", "Icarus", "Janus")
FIXTURE_SHA256 = "b721650791284e4369d440d494de4aaf76da35fe4be11e34cb87bba1285e4040"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
VARIANTS = pilot.VARIANTS


def require(ok, message):
    if not ok:
        raise ValueError(message)


def prereg():
    dry = pilot.prereg()
    require(FIXTURE_IDS == EXPECTED_IDS, "Registered TP27 fixture IDs changed")
    require(dry["registered"]["fixture_sha256"] == FIXTURE_SHA256,
            "Registered TP27 fixture content changed")
    require(dry["registered"]["arms"][ARM]["settings"]["seed"] == SEED,
            "Registered TP27 seed changed")
    require(z2b.z2 is pilot.z2, "Private harness module alias changed")
    return dry


def installed_artifacts(home):
    # The harness inventories runner bytes and all native runtime libraries.
    return z2b.z2.harness().installed_artifacts(Path(home))


def verify_pair(raw_source, raw_tool, before, summary, tool_prereg=None):
    """Independent fail-closed 70+70 row binding, no inference."""
    source, tool = verify_native_reports(
        raw_source, raw_tool, EXPECTED_IDS, FIXTURE_SHA256)
    require(source["installed_artifacts"] == before,
            "Source report does not bind pinned installed artifacts")
    require(before["runner_sha256"] == RUNNER_SHA256,
            "Native runner changed from frozen registration")
    require(before["model_sha256"]["B1_DETAIL"] != before["model_sha256"]["B2_GIST"],
            "TP must use distinct body weights")
    require(source["canonical_gate_pass"] is False and
            source["phone_measured"] is False and
            tool["canonical_gate_pass"] is False and
            tool["phone_measured"] is False,
            "Unexpected gate or device promotion")
    require(source.get("distinct_bodies") is True and
            source.get("paired", {}).get("complete") is True and
            tool.get("paired_tool", {}).get("complete") is True,
            "Ten-fixture paired evidence incomplete")
    cfg = source["config"]
    expected_settings = pre.candidate_settings(ARM, SEED)
    require(all(cfg.get(k) == v for k, v in expected_settings.items()),
            "TP/s27 native controls changed")
    run = source.get("z2b_run")
    require(isinstance(run, dict) and run.get("arm") == ARM and
            run.get("seed") == SEED and run.get("enable") == expected_settings,
            "Native run identity/controls mismatch")
    offers = source.get("z2b_queried_offers")
    require(isinstance(offers, dict) and type(offers.get("offers")) is int and
            offers["offers"] > 0 and offers.get("with_question") == offers["offers"],
            "Fixed JEF question not present on every offered body turn")
    require(summary.get("arm") == ARM and summary.get("seed") == SEED and
            summary.get("enable") == expected_settings and summary.get("query") is True and
            summary.get("queried_offers") == offers and
            summary.get("step2_status") == source["status"] and
            summary.get("tool_status") == tool["status"],
            "Native summary disagrees with original reports")
    source_rows = {r["fixture"] + ":" + r["variant"]: r for r in source["rows"]}
    tool_rows = {r["fixture"] + ":" + r["variant"]: r for r in tool["rows"]}
    require(len(source_rows) == len(tool_rows) == 70, "Native row count changed")
    for key, row in source_rows.items():
        require(row.get("status") == "RECORDED" and
                row.get("processes_reaped") is True and
                row.get("restart_state_identical") is True and
                row.get("oracle_visible_to_native") is False and
                row.get("native_consumer_metrics", {}).get("status") == "FINAL",
                "Native source row invalid: " + key)
        other = tool_rows[key]
        require(other.get("status") == "RECORDED" and
                other.get("oracle_visible_to_native") is False and
                other.get("consumer_metrics", {}).get("status") == "FINAL" and
                other.get("consumer_messages_sha256") ==
                    digest(dumps(row["consumer_messages"])),
                "C3 replay not bound to original native messages: " + key)
    if tool_prereg is not None:
        require(tool_prereg.get("source_report", {}).get("sha256") ==
                    hashlib.sha256(raw_source).hexdigest() and
                tool_prereg.get("fixture_sha256") == FIXTURE_SHA256 and
                tool_prereg.get("seed") == 13 and
                len(tool_prereg.get("consumer_messages_sha256", {})) == 70,
                "C3 replay prereg does not bind source raw")
        for key, row in source_rows.items():
            require(tool_prereg["consumer_messages_sha256"].get(key) ==
                    digest(dumps(row["consumer_messages"])),
                    "C3 prereg message binding changed: " + key)
    return source, tool


def run(installed_home, evidence_dir):
    dry = prereg()
    installed_home = Path(installed_home).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    require(installed_home.is_dir() and
            (installed_home / "config/models.json").is_file() and
            not evidence_dir.exists() and evidence_dir.parent.is_dir(),
            "Existing pinned home and fresh evidence directory required")
    model_before = pilot.pinned_models(installed_home)
    before = installed_artifacts(installed_home)
    require(before["model_sha256"] == model_before and
            before["runner_sha256"] == RUNNER_SHA256,
            "Pinned native model or runner mismatch")
    evidence_dir.mkdir(mode=0o700)
    receipt = {
        "schema": "v13.step2.tp27.full70.native_tool.v1",
        "status": "RUNNING", "arm": ARM, "seed": SEED,
        "fixture_ids": list(EXPECTED_IDS),
        "fixture_sha256": FIXTURE_SHA256,
        "registration_sha256": dry["registration_sha256"],
        "model_hashes_before": model_before,
        "installed_artifacts_before": before,
        "scope": "LINUX_NATIVE_STEP2_TP27_ONE_ARM_70_PLUS_70",
        "age_authority": 0, "jepa_weight": 0, "weight_updates": False,
        "redmi_measured": False, "canonical_gate_pass": False,
        "whole_system_complete": False,
    }
    receipt_path = evidence_dir / "RECEIPT.json"

    def save():
        atomic_write(receipt_path, dumps(receipt))

    save()
    work = evidence_dir / "run"
    work.mkdir(mode=0o700)
    try:
        with pre.configured():
            require(z2b.z2.FIXTURES is pre.corpus.FIXTURES and
                    z2b.z2.harness().FIXTURES is pre.corpus.FIXTURES,
                    "Wrong private STEP2 cohort alias")
            summary = z2b.run_one(installed_home, work, ARM, SEED)
        source_path = work / "step2_TP_s27.json"
        tool_path = work / "tool_TP_s27.json"
        summary_path = work / "summary_TP_s27.json"
        prereg_path = tool_path.with_suffix(".preregistration.json")
        raw_source, raw_tool = source_path.read_bytes(), tool_path.read_bytes()
        tool_prereg = json.loads(prereg_path.read_bytes())
        source, tool = verify_pair(raw_source, raw_tool, before, summary, tool_prereg)
        require(json.loads(summary_path.read_bytes()) == summary,
                "Persisted native summary changed")
        model_after = pilot.pinned_models(installed_home)
        after = installed_artifacts(installed_home)
        require(model_before == model_after and before == after,
                "Installed model/runner/library bytes changed")
        receipt.update({
            "status": "PASS_SCOPED_ONE_ARM_NATIVE_TOOL_NO_CANON_GATE",
            "native_rows": len(source["rows"]),
            "tool_rows": len(tool["rows"]),
            "native_status": source["status"],
            "tool_status": tool["status"],
            "native_offer_counts": source["z2b_queried_offers"],
            "model_hashes_after": model_after,
            "installed_artifacts_unchanged": True,
            "raw_source_sha256": hashlib.sha256(raw_source).hexdigest(),
            "raw_tool_sha256": hashlib.sha256(raw_tool).hexdigest(),
            "raw_summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
            "raw_tool_prereg_sha256": hashlib.sha256(prereg_path.read_bytes()).hexdigest(),
            "source_utility": source["paired"]["mean_utility"],
            "tool_utility": tool["paired_tool"]["mean_utility"],
            "source_scoped_utility_gate_pass": source["scoped_utility_gate_pass"],
            "tool_scoped_utility_gate_pass": tool["paired_tool"]["scoped_utility_gate_pass"],
            "all_native_processes_reaped": True,
            "native_c3_final": 70, "tool_c3_final": 70,
        })
    except BaseException as exc:
        receipt["status"] = "FAIL_RETAIN_RAW"
        receipt["error_type"] = type(exc).__name__
        save()
        raise
    save()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-home", required=True)
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args(argv)
    result = run(args.installed_home, args.evidence_dir)
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("installed_artifacts_before",)}, sort_keys=True))
    return 0 if result["status"].startswith("PASS_SCOPED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
