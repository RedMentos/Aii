"""One preregistered Aquila TP/s27 native STEP2 diagnostic; no utility promotion.

New current-source prereg: docs/coordination/AUTOMATION11_STEP2_LONGNOTE_TP27_NATIVE_PILOT_PREREG_20261028.md
Uses the frozen seven-variant harness with fixture_limit=1, never relabels
the resulting DIAGNOSTIC_INCOMPLETE as a STEP2 utility PASS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import step2_longnote_runner_preflight as pre
from scripts import step2_z2b_seeds as z2b
from scripts import step2_z2_timescale as z2
from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize
from v13.models import ModelManager

ARM = "TP"
SEED = 27
FIXTURE_ID = "Aquila"
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact",
            "both_control", "same_policy_dual", "prompt_only_dual")


def prereg():
    dry = pre.dry_run()
    reg = dry["registered"]
    if (dry["native_execution"] is not False
            or reg["seeds"] != [27, 28, 29]
            or reg["arms"][ARM]["body"] != "two_distinct"
            or reg["arms"][ARM]["query"] is not True
            or reg["arms"][ARM]["pointer"] is not True
            or reg["arms"][ARM]["settings"]["seed"] != SEED
            or len(pre.corpus.FIXTURES) != 10
            or pre.corpus.FIXTURES[0]["id"] != FIXTURE_ID
            or pre.corpus.FIXTURES[0]["type"] != "SPLIT"):
        raise ValueError("STEP2 TP27 source preregistration changed")
    return dry


def pinned_models(home):
    models = ModelManager(home, initialize(home)["b2_control"])
    verified = models.verify(deep=True)
    roles = ("body", "gist", "language", "needle")
    for role in roles:
        spec = models.specs["models"][role]
        installed = models.installed.get(role)
        if (not installed or not verified.get(role, {}).get("ok")
                or verified[role].get("hash_checked") is not True
                or installed.get("model_id") != spec["model_id"]
                or installed.get("exact_revision") != spec["revision"]
                or installed.get("license_id") != spec["license_id"]
                or installed.get("main_file") != spec["main_file"]):
            raise ValueError("Pinned model/catalog mismatch: " + role)
        for f in spec["files"]:
            saved = installed["files"].get(f["local_name"])
            if (not isinstance(saved, dict)
                    or saved.get("sha256") != f["sha256"]
                    or saved.get("size") != f["size"]):
                raise ValueError("Pinned model file mismatch: " + role)
    result = {role: file_hash(models.path_for(role))
              for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")}
    if result["B1_DETAIL"] == result["B2_GIST"]:
        raise ValueError("Distinct B1/B2 model weights required")
    return result


def verify_report(report, count, model_hashes):
    rows = report["rows"]
    if (len(rows) != len(VARIANTS)
            or {(row["fixture"], row["variant"]) for row in rows}
            != {(FIXTURE_ID, v) for v in VARIANTS}
            or len(report["preparations"]) != 1
            or report["preparations"][0]["fixture"] != FIXTURE_ID
            or report["preparations"][0]["status"] != "RECORDED"
            or report["preparations"][0]["model_sha256"] != model_hashes
            or report["source_unchanged"] is not True
            or report["installed_artifacts_unchanged"] is not True
            or report["all_structural_checks_passed"] is not True
            or report["distinct_bodies"] is not True
            or report["canonical_gate_pass"] is not False
            or report["phone_measured"] is not False
            or report["status"] != "DIAGNOSTIC_INCOMPLETE"
            or count != {"offers": 12, "with_question": 12}):
        raise ValueError("Native STEP2 one-fixture structural contract failed")
    for row in rows:
        if (row["status"] != "RECORDED"
                or row.get("processes_reaped") is not True
                or row.get("native_consumer_metrics", {}).get("status") != "FINAL"
                or row.get("oracle_visible_to_native") is not False):
            raise ValueError("Native STEP2 row failed: " + row["variant"])
    return {"status": "PASS_SCOPED_ONE_FIXTURE_NATIVE_NO_UTILITY_GATE",
            "rows": len(rows), "native_consumer_final": len(rows),
            "queried_offers": count["with_question"], "source_unchanged": True,
            "models_unchanged": True, "processes_reaped": True}


def run(installed_home, evidence_dir):
    dry = prereg()
    installed_home = Path(installed_home).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    if (not installed_home.is_dir()
            or not (installed_home / "config/models.json").is_file()
            or evidence_dir.exists()
            or not evidence_dir.parent.is_dir()):
        raise ValueError("Existing pinned home and fresh evidence directory required")
    before = pinned_models(installed_home)
    evidence_dir.mkdir(mode=0o700)
    receipt = {
        "schema": "v13.step2.tp27.aquila.native_pilot.v1",
        "status": "RUNNING", "arm": ARM, "seed": SEED,
        "fixture_id": FIXTURE_ID, "fixture_limit": 1,
        "registration_sha256": dry["registration_sha256"],
        "fixture_sha256": dry["registered"]["fixture_sha256"],
        "model_hashes_before": before,
        "scope": "LINUX_NATIVE_STEP2_ONE_FIXTURE_ONLY",
        "age_authority": 0, "jepa_weight": 0,
        "weight_updates": False, "redmi_measured": False,
        "canonical_gate_pass": False, "whole_system_complete": False,
    }
    path = evidence_dir / "RECEIPT.json"
    def save():
        atomic_write(path, dumps(receipt))
    save()
    try:
        with pre.configured():
            step2 = z2.harness()
            with z2b.Patches(step2, query=True) as patch:
                arm_home = z2.sibling_home(installed_home, evidence_dir / "tp27-home",
                                           pre.candidate_settings(ARM, SEED))
                report_path = evidence_dir / "STEP2_RAW.json"
                report = step2.run_locked(arm_home, report_path, fixture_limit=1)
                count = dict(patch.count)
        receipt["model_hashes_after"] = pinned_models(installed_home)
        receipt["model_hashes_unchanged"] = (
            receipt["model_hashes_before"] == receipt["model_hashes_after"])
        receipt["raw_report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
        receipt["raw_rows"] = len(report["rows"])
        receipt["native_offer_counts"] = count
        if receipt["model_hashes_unchanged"] is not True:
            raise ValueError("Pinned model bytes changed during native run")
        receipt.update(verify_report(report, count, before))
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
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"].startswith("PASS_SCOPED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
