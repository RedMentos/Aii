"""Run33/Run25 fresh Lysoria EN STEP2 one-fixture native pilot (review-only).

This module implements the already preregistered Run33 source-only contract.
Import and prereg never load models. Native execution requires an existing
hash-verified installed home and a fresh private evidence directory.
No STEP2/Body-JEPA/B3/Redmi/age gate is promoted by this diagnostic.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path

from scripts import run15_step2_disjoint_bilingual_fixtures as fresh
from scripts import step2_z2b_seeds as z2b
from scripts import step2_longnote_tp27_native_pilot as native_pins
from scripts.step2_current_catalog_artifact_probe import git_blob_sha
from v13.common import atomic_write, dumps, file_hash

# Z2b imports its harness under a single top-level alias. Reuse that object.
z2 = z2b.z2
ROOT = Path(__file__).resolve().parents[1]
RUN15_SOURCE_BLOB = "635e5727a42cb1eac4f84441afda2977b0c8109c"
PINNED_SOURCE_BLOBS = {
    "scripts/step2_z2_timescale.py": "2ad62fbbf1f6463d99360cdb8198f1104cfdfaf7",
    "scripts/step2_z2b_seeds.py": "7c299616495450e4a38f9aab9921f7176ba67556",
    "scripts/step2_longnote_tp27_native_pilot.py": "7253b113b43de110059575cc14ef7b2ce7bccc43",
    "tests/integration_step2_utility.py": "a7ba12a8807a1ca8236f1c70d54dedb65c212caa",
    "v13/cognition.py": "1a9eb6f7c7cbfce83d91cc09b4ff9516cff310cf",
    "v13/runners.py": "efda7aa1aa5729e974d0d641870d4da05d21c961",
    "v13/models.py": "bd035cf8029850cce00b179edf533e53bf24358a",
    "specs/models.json": "7af05962af41d0bc3f7dd18ef01d4eba55eabf99",
}
PINNED_RUNNER_TAR_SHA256 = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
FIXTURE_ID = "Lysoria"
ARM = "CQ"
SEED = 20261115
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact",
            "both_control", "same_policy_dual", "prompt_only_dual")
SCOPE = "LINUX_NATIVE_RUN33_LYSORIA_EN_RULE_ONE_FIXTURE_ONLY"


def prereg():
    """Verify the already frozen new cohort and CQ controls, without inference."""
    path = ROOT / "scripts/run15_step2_disjoint_bilingual_fixtures.py"
    if (git_blob_sha(path.read_bytes()) != RUN15_SOURCE_BLOB or
            fresh.SEEDS != (20261115, 20261115, 20261116) or
            len(fresh.FIXTURES) != 6 or
            fresh.FIXTURES[1]["id"] != FIXTURE_ID or
            fresh.FIXTURES[1]["language"] != "EN" or
            fresh.FIXTURES[1]["type"] != "RULE" or
            fresh.CANONICAL_GATE_PASS is not False or
            fresh.JEPA_WEIGHT != 0):
        raise ValueError("Run15 fresh fixture preregistration changed")
    for relative, expected in PINNED_SOURCE_BLOBS.items():
        if git_blob_sha((ROOT / relative).read_bytes()) != expected:
            raise ValueError("Run33 frozen source pin changed: " + relative)
    catalog = json.loads((ROOT / "specs/models.json").read_text())
    if (catalog["runner"]["tag"] != "b10964" or
            catalog["runner"]["linux_binaries"]["linux-x86_64"]["sha256"]
            != PINNED_RUNNER_TAR_SHA256):
        raise ValueError("Run33 runner release pin changed")
    settings = z2b.settings(ARM, SEED)
    if (settings["seed"] != SEED or
            settings["b2_control"] != "two_body" or
            settings["b1_recent_source_chars"] != 600 or
            z2b.ARMS[ARM] != {"base": "C", "query": True}):
        raise ValueError("Run33 CQ arm/seed controls changed")
    return {"schema": "v13.step2.run33.keldara.pilot.prereg.v1",
            "scope": SCOPE, "fixture_id": FIXTURE_ID, "fixture_limit": 1,
            "fixture_sha256": fresh.FIXTURE_SHA256,
            "fixture_source_git_blob": RUN15_SOURCE_BLOB,
            "source_git_blobs": dict(PINNED_SOURCE_BLOBS),
            "runner_tar_sha256": PINNED_RUNNER_TAR_SHA256,
            "arm": ARM, "seed": SEED, "settings": settings,
            "variant_count": len(VARIANTS), "canonical_gate_pass": False,
            "phone_measured": False, "jepa_weight": 0,
            "age_authority": 0, "whole_system_complete": False}


@contextmanager
def private_harness():
    """Patch only the shared Z2b harness alias, then restore on every exit."""
    original = z2.FIXTURES
    try:
        z2.FIXTURES = fresh.FIXTURES[1:]
        harness = z2.harness()
        if (z2b.z2 is not z2 or
                harness.FIXTURES is not z2.FIXTURES or
                harness.FIXTURES[0]["id"] != FIXTURE_ID):
            raise ValueError("Run33 private fixture alias mismatch")
        yield harness
    finally:
        z2.FIXTURES = original


def verify_report(report, model_hashes, question_counts):
    """Strict structural evidence only, never a utility/age promotion."""
    if not isinstance(report, dict) or not isinstance(model_hashes, dict):
        raise ValueError("Invalid native report")
    if (set(model_hashes) != {"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"} or
            any(not isinstance(x, str) or len(x) != 64 or
                any(c not in "0123456789abcdef" for c in x)
                for x in model_hashes.values()) or
            model_hashes["B1_DETAIL"] == model_hashes["B2_GIST"]):
        raise ValueError("Native model hash identity invalid")
    rows = report.get("rows")
    expected = {(FIXTURE_ID, variant) for variant in VARIANTS}
    preparations = report.get("preparations")
    if (not isinstance(rows, list) or len(rows) != len(VARIANTS) or
            {(r.get("fixture"), r.get("variant")) for r in rows
             if isinstance(r, dict)} != expected or
            not isinstance(preparations, list) or len(preparations) != 1 or
            preparations[0].get("fixture") != FIXTURE_ID or
            preparations[0].get("status") != "RECORDED" or
            preparations[0].get("model_sha256") != model_hashes or
            report.get("fixture_sha256") != fresh.FIXTURE_SHA256 or
            report.get("source_unchanged") is not True or
            report.get("installed_artifacts_unchanged") is not True or
            report.get("all_structural_checks_passed") is not True or
            report.get("distinct_bodies") is not True or
            report.get("canonical_gate_pass") is not False or
            report.get("phone_measured", False) is not False or
            report.get("status") != "DIAGNOSTIC_INCOMPLETE" or
            question_counts != {"offers": 12, "with_question": 12}):
        raise ValueError("Run33 Lysoria one-fixture structural contract failed")
    for row in rows:
        if (row.get("status") != "RECORDED" or
                row.get("processes_reaped") is not True or
                row.get("oracle_visible_to_native") is not False or
                row.get("native_consumer_metrics", {}).get("status") != "FINAL"):
            raise ValueError("Run33 native row not fully verified")
    return {"status": "PASS_SCOPED_ONE_FIXTURE_NATIVE_NO_UTILITY_GATE",
            "rows": len(rows), "native_consumer_final": len(rows),
            "queried_offers": question_counts["with_question"],
            "models_unchanged": True, "processes_reaped": True,
            "canonical_gate_pass": False, "phone_measured": False,
            "jepa_weight": 0, "age_authority": 0,
            "whole_system_complete": False}


def run(installed_home, evidence_dir):
    """Explicitly invoked native pilot; no download, no destructive cleanup."""
    reg = prereg()
    installed_home = Path(installed_home).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    if (not installed_home.is_dir() or
            not (installed_home / "config/models.json").is_file() or
            not (installed_home / "bin/llama-server").is_file() or
            evidence_dir.exists() or not evidence_dir.parent.is_dir()):
        raise ValueError("Existing pinned home, runner and fresh evidence directory required")
    before = native_pins.pinned_models(installed_home)
    runner_before = file_hash(installed_home / "bin/llama-server")
    evidence_dir.mkdir(mode=0o700)
    receipt = {
        "schema": "v13.step2.run33.keldara.native_pilot.v1",
        "status": "RUNNING", "scope": SCOPE,
        "fixture_id": FIXTURE_ID, "fixture_limit": 1,
        "fixture_sha256": reg["fixture_sha256"],
        "fixture_source_git_blob": RUN15_SOURCE_BLOB,
        "arm": ARM, "seed": SEED, "model_hashes_before": before,
        "runner_sha256_before": runner_before,
        "age_authority": 0, "jepa_weight": 0,
        "weight_updates": False, "redmi_measured": False,
        "canonical_gate_pass": False, "whole_system_complete": False,
    }
    receipt_path = evidence_dir / "RECEIPT.json"
    def save():
        atomic_write(receipt_path, dumps(receipt))
    save()
    try:
        with private_harness() as harness:
            with z2b.Patches(harness, query=True) as patch:
                home = z2.sibling_home(
                    installed_home, evidence_dir / "run33-home", reg["settings"])
                raw_path = evidence_dir / "STEP2_RAW.json"
                report = harness.run_locked(home, raw_path, fixture_limit=1)
                counts = dict(patch.count)
        after = native_pins.pinned_models(installed_home)
        runner_after = file_hash(installed_home / "bin/llama-server")
        if prereg() != reg:
            raise ValueError("Run33 source preregistration changed during native run")
        receipt["model_hashes_after"] = after
        receipt["runner_sha256_after"] = runner_after
        receipt["model_hashes_unchanged"] = before == after
        receipt["runner_unchanged"] = runner_before == runner_after
        receipt["raw_report_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        receipt["native_offer_counts"] = counts
        if not receipt["model_hashes_unchanged"] or not receipt["runner_unchanged"]:
            raise ValueError("Pinned native artifacts changed during pilot")
        receipt.update(verify_report(report, before, counts))
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
    print(json.dumps({"status": result["status"], "rows": result["rows"],
                      "canonical_gate_pass": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
