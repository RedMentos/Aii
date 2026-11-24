"""One registered STEP2 arm/seed per durable native checkpoint (candidate).

Frozen 4 arms x 3 seeds, 10 fixtures x 7 variants, real B1/B2/C3 plus
frozen typed-value C3 tool replay. No automatic full-cohort gate promotion.
An interrupted arm retains partial original raw; the next arm uses a new dir.
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
from scripts.step2_fourarm_native_collector_candidate import (
    MAX_RAW, canonical, verify_native_reports,
)
from scripts.step2_longnote_fourarm_analysis import ARMS, SEEDS, VARIANTS
from v13.common import atomic_write, digest, dumps, file_hash

FIXTURE_IDS = ("Aquila", "Bellatrix", "Cetus", "Deneb", "Erebos",
               "Fomalhaut", "Ganymede", "Hyperion", "Icarus", "Janus")
FIXTURE_SHA256 = "b721650791284e4369d440d494de4aaf76da35fe4be11e34cb87bba1285e4040"
REGISTRATION_SHA256 = "d9d17ba23218c8d622ecb8ac3fcb0a0b6917fa1be72df2000256d8633d1b6eba"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prereg(arm, seed):
    require(arm in ARMS and type(seed) is int and seed in SEEDS,
            "Unregistered STEP2 arm/seed")
    dry = pre.dry_run()
    require(tuple(x["id"] for x in pre.corpus.FIXTURES) == FIXTURE_IDS and
            dry["registered"]["fixture_sha256"] == FIXTURE_SHA256 and
            dry["registration_sha256"] == REGISTRATION_SHA256 and
            dry["registered"]["seeds"] == list(SEEDS) and
            tuple(dry["registered"]["arms"]) == tuple(ARMS) and
            z2b.z2 is pre.z2 is pilot.z2,
            "Frozen STEP2 four-arm registration or module alias changed")
    spec = dry["registered"]["arms"][arm]
    require(spec["query"] is True and
            spec["pointer"] is arm.endswith("P") and
            spec["body"] == ("two_distinct" if arm.startswith("T") else "shared_dual_state"),
            "Registered STEP2 arm controls changed")
    return dry


def source_hashes():
    paths = (
        Path(__file__).resolve(),
        Path(pre.__file__).resolve(),
        Path(pre.corpus.__file__).resolve(),
        Path(z2b.__file__).resolve(),
        Path(z2b.z2.__file__).resolve(),
        ROOT / "scripts/step2_tool_replay.py",
        ROOT / "scripts/step2_fourarm_native_collector_candidate.py",
        ROOT / "tests/integration_step2_utility.py",
        ROOT / "v13/runtime.py",
        ROOT / "v13/cognition.py",
        ROOT / "v13/runners.py",
        ROOT / "v13/agi/eligibility.py",
        ROOT / "specs/models.json",
        ROOT / "specs/control_tools.json",
    )
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def installed_artifacts(home):
    return z2b.z2.harness().installed_artifacts(Path(home))


def expected_models(arm, base):
    result = dict(base)
    if arm.startswith("S"):
        result["B2_GIST"] = result["B1_DETAIL"]
    require((result["B1_DETAIL"] != result["B2_GIST"]) == arm.startswith("T"),
            "Distinct/shared B1/B2 model control incorrect")
    return result


def verify_pair(raw_source, raw_tool, tool_prereg, summary,
                arm, seed, base_artifacts):
    """Fail-closed native+tool row and source-message verification, no model calls."""
    prereg(arm, seed)
    source, tool = verify_native_reports(
        raw_source, raw_tool, FIXTURE_IDS, FIXTURE_SHA256)
    expected = dict(base_artifacts)
    expected["model_sha256"] = expected_models(arm, base_artifacts["model_sha256"])
    expected["model_revisions"] = dict(base_artifacts["model_revisions"])
    if arm.startswith("S"):
        expected["model_revisions"]["B2_GIST"] = expected["model_revisions"]["B1_DETAIL"]
    require(expected["runner_sha256"] == RUNNER_SHA256 and
            source["installed_artifacts"] == expected and
            source.get("distinct_bodies") is arm.startswith("T"),
            "Native distinct/shared model or runner identity changed")
    require(source["canonical_gate_pass"] is False and
            tool["canonical_gate_pass"] is False and
            source["phone_measured"] is False and
            tool["phone_measured"] is False and
            source.get("paired", {}).get("complete") is True and
            tool.get("paired_tool", {}).get("complete") is True,
            "Native utility evidence incomplete or gate promoted")
    settings = pre.candidate_settings(arm, seed)
    cfg = source["config"]
    require(all(cfg.get(k) == v for k, v in settings.items()),
            "Native STEP2 arm/seed settings changed")
    run = source.get("z2b_run")
    require(isinstance(run, dict) and run.get("arm") == arm and
            run.get("seed") == seed and run.get("enable") == settings,
            "Native source run identity changed")
    offers = source.get("z2b_queried_offers")
    require(isinstance(offers, dict) and type(offers.get("offers")) is int and
            offers["offers"] > 0 and offers.get("with_question") == offers["offers"],
            "Native fixed JEF question missing")
    require(summary.get("arm") == arm and summary.get("seed") == seed and
            summary.get("enable") == settings and summary.get("query") is True and
            summary.get("queried_offers") == offers and
            summary.get("step2_status") == source["status"] and
            summary.get("tool_status") == tool["status"],
            "Native summary identity mismatch")
    require(tool_prereg.get("source_report", {}).get("sha256") ==
            hashlib.sha256(raw_source).hexdigest() and
            tool_prereg.get("fixture_sha256") == FIXTURE_SHA256 and
            tool_prereg.get("seed") == 13,
            "C3 typed-value replay not source bound")
    original = {r["fixture"] + ":" + r["variant"]: r for r in source["rows"]}
    replayed = {r["fixture"] + ":" + r["variant"]: r for r in tool["rows"]}
    require(len(original) == len(replayed) == 70 and
            set(tool_prereg.get("consumer_messages_sha256", {})) == set(original),
            "Native C3 replay row coverage incomplete")
    for key, row in original.items():
        h = digest(dumps(row["consumer_messages"]))
        other = replayed[key]
        require(row.get("status") == "RECORDED" and
                row.get("processes_reaped") is True and
                row.get("restart_state_identical") is True and
                row.get("oracle_visible_to_native") is False and
                row.get("native_consumer_metrics", {}).get("status") == "FINAL" and
                other.get("status") == "RECORDED" and
                other.get("oracle_visible_to_native") is False and
                other.get("consumer_metrics", {}).get("status") == "FINAL" and
                other.get("consumer_messages_sha256") == h and
                tool_prereg["consumer_messages_sha256"].get(key) == h,
                "Native source/tool message or FINAL mismatch: " + key)
    return source, tool, expected


def sealed_summary(summary, raw_source, raw_tool, arm, seed, models, sources):
    """Canonical per-run summary accepted by existing four-arm scorer only in 12."""
    raw = (len(raw_source).to_bytes(8, "big") + raw_source +
           len(raw_tool).to_bytes(8, "big") + raw_tool)
    require(len(raw) <= MAX_RAW, "Combined native raw exceeds registered limit")
    record = {
        "arm": arm, "seed": seed,
        "registration_sha256": REGISTRATION_SHA256,
        "fixture_sha256": FIXTURE_SHA256,
        "source_sha256": sources,
        "model_sha256": models,
        "runner_sha256": RUNNER_SHA256,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "evidence_kind": "LINUX_NATIVE",
        "enable": summary["enable"],
        "queried_offers": summary["queried_offers"],
        "step2_status": summary["step2_status"],
        "tool_status": summary["tool_status"],
        "episode_utility_tool": summary["episode_utility_tool"],
        "error_profile_tool": summary["error_profile_tool"],
        "canonical_gate_pass": False,
        "step2_gate_promoted": False,
        "jepa_weight": 0,
        "age_authority": 0,
        "redmi_measured": False,
        "whole_system_complete": False,
        "claim_limit": "One of 12 Linux-native arm/seed checkpoints; never STEP2 acceptance alone",
    }
    return raw, record


def run(installed_home, evidence_dir, arm, seed):
    dry = prereg(arm, seed)
    installed_home = Path(installed_home).resolve()
    evidence_dir = Path(evidence_dir).resolve()
    require(installed_home.is_dir() and
            (installed_home / "config/models.json").is_file() and
            not evidence_dir.exists() and evidence_dir.parent.is_dir(),
            "Pinned installed home and fresh evidence directory required")
    models_before = pilot.pinned_models(installed_home)
    artifacts_before = installed_artifacts(installed_home)
    sources_before = source_hashes()
    require(artifacts_before["model_sha256"] == models_before and
            artifacts_before["runner_sha256"] == RUNNER_SHA256,
            "Pinned model/runner bytes changed")
    evidence_dir.mkdir(mode=0o700)
    receipt = {
        "schema": "v13.step2.staged12.single_arm.v1",
        "status": "RUNNING", "arm": arm, "seed": seed,
        "fixture_ids": list(FIXTURE_IDS),
        "registration_sha256": dry["registration_sha256"],
        "source_sha256": sources_before,
        "model_hashes_before": models_before,
        "installed_artifacts_before": artifacts_before,
        "scope": "LINUX_NATIVE_ONE_OF_TWELVE_70_PLUS_70",
        "age_authority": 0, "jepa_weight": 0, "weight_updates": False,
        "redmi_measured": False, "canonical_gate_pass": False,
        "whole_system_complete": False,
    }
    def save():
        atomic_write(evidence_dir / "RECEIPT.json", dumps(receipt))
    save()
    work = evidence_dir / "run"
    work.mkdir(mode=0o700)
    rid = f"{arm}_s{seed}"
    try:
        with pre.configured():
            require(z2b.z2.FIXTURES is pre.corpus.FIXTURES and
                    z2b.z2.harness().FIXTURES is pre.corpus.FIXTURES,
                    "Private native harness fixture alias changed")
            summary = z2b.run_one(installed_home, work, arm, seed)
        source_path = work / ("step2_" + rid + ".json")
        tool_path = work / ("tool_" + rid + ".json")
        summary_path = work / ("summary_" + rid + ".json")
        tool_prereg_path = tool_path.with_suffix(".preregistration.json")
        raw_source, raw_tool = source_path.read_bytes(), tool_path.read_bytes()
        tool_prereg = json.loads(tool_prereg_path.read_bytes())
        source, tool, actual = verify_pair(
            raw_source, raw_tool, tool_prereg, summary, arm, seed, artifacts_before)
        require(json.loads(summary_path.read_bytes()) == summary,
                "Persisted native summary differs from return")
        models_after = pilot.pinned_models(installed_home)
        artifacts_after = installed_artifacts(installed_home)
        require(models_before == models_after and
                artifacts_before == artifacts_after and
                sources_before == source_hashes(),
                "Native source/model/runner/library drift")
        raw, sealed = sealed_summary(summary, raw_source, raw_tool, arm, seed,
                                     actual["model_sha256"], sources_before)
        atomic_write(evidence_dir / "RAW_PAIR.bin", raw)
        atomic_write(evidence_dir / "SEALED_SUMMARY.json", dumps(sealed))
        receipt.update({
            "status": "PASS_SCOPED_ONE_OF_TWELVE_NO_CANON_GATE",
            "native_rows": len(source["rows"]), "tool_rows": len(tool["rows"]),
            "native_status": source["status"], "tool_status": tool["status"],
            "raw_pair_sha256": sealed["raw_sha256"],
            "sealed_summary_sha256": digest(dumps(sealed)),
            "model_hashes_after": models_after,
            "source_model_runner_unchanged": True,
            "native_c3_final": 70, "tool_c3_final": 70,
            "all_native_processes_reaped": True,
        })
    except BaseException as exc:
        receipt["status"] = "FAIL_RETAIN_RAW"
        receipt["error_type"] = type(exc).__name__
        save()
        raise
    save()
    return receipt


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--installed-home", required=True)
    p.add_argument("--evidence-dir", required=True)
    p.add_argument("--arm", choices=ARMS, required=True)
    p.add_argument("--seed", type=int, choices=SEEDS, required=True)
    args = p.parse_args(argv)
    receipt = run(args.installed_home, args.evidence_dir, args.arm, args.seed)
    print(json.dumps({k: v for k, v in receipt.items()
                      if k not in ("installed_artifacts_before", "source_sha256")},
                     sort_keys=True))
    return 0 if receipt["status"].startswith("PASS_SCOPED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
