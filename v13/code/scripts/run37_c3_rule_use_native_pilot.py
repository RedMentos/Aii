"""Run37 C3-only native Elyndra action/rule prompt factorial, review-only.

Requires a fresh hash-verified installed C3 home and exclusive native owner.
No B1/B2 inference, Runtime/Store, learning, phone or STEP2 gate promotion.
"""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import threading
import time

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from scripts import run34_c3_native_quote_intervention_pilot as base
from scripts import run37_c3_rule_use_hint_envelopes as study
from tests import integration_step2_utility as frozen_consumer
from v13.common import atomic_write, dumps, file_hash

ROOT = Path(__file__).resolve().parents[1]
STUDY_SOURCE_BLOB = "071d65317794ddc621d7ea5abd4bae2a7d1536b7"
FIXTURE = study.FIXTURE
SEED = study.SEED
ARMS = study.ARMS
SCHEMA = "v13.run37.c3_rule_use.native_pilot.raw.v1"


def prereg():
    reg = study.prereg()
    base.prereg()
    if base._git_blob(ROOT / "scripts/run37_c3_rule_use_hint_envelopes.py") != STUDY_SOURCE_BLOB:
        raise ValueError("run37_study_source_changed")
    return {
        **reg, "schema": "v13.run37.c3_rule_use.native_pilot.prereg.v1",
        "scope": "LINUX_NATIVE_C3_ONLY_NEW_EXPLORATORY_INTERVENTION",
        "native_executed": False, "canonical_gate_pass": False,
        "phone_measured": False, "jepa_weight": 0,
        "whole_system_complete": False,
    }


def verify_report(report, model_sha, runner_sha):
    if (not isinstance(report, dict) or report.get("schema") != SCHEMA or
            report.get("fixture_id") != FIXTURE or report.get("seed") != SEED or
            report.get("model_sha256") != model_sha or
            report.get("runner_sha256") != runner_sha or
            report.get("canonical_gate_pass") is not False or
            report.get("phone_measured") is not False or
            report.get("jepa_weight") != 0 or
            report.get("failed_attempts") != []):
        raise ValueError("run37_native_header_invalid")
    rows = report.get("rows")
    if (not isinstance(rows, list) or len(rows) != len(ARMS) or
            [r.get("arm") for r in rows if isinstance(r, dict)] != list(ARMS) or
            not isinstance(report.get("row_sha256"), dict) or
            len(report["row_sha256"]) != len(ARMS)):
        raise ValueError("run37_native_rows_invalid")
    oracle = next(f["oracle"] for f in cf.FIXTURES if f["id"] == FIXTURE)
    for row in rows:
        if (row.get("native_status") != "FINAL" or
                not isinstance(row.get("native_metrics"), dict) or
                row["native_metrics"].get("status") != "FINAL" or
                row["native_metrics"].get("actual_model") !=
                "LFM2.5-350M-QAD-Q4_0.gguf" or
                row.get("process_reaped") is not True or
                row.get("oracle_visible_to_native") is not False or
                row.get("model_sha256") != model_sha or
                row.get("runner_sha256") != runner_sha or
                row.get("envelope_verified") is not True or
                type(row.get("raw_answer")) is not str or
                not row["raw_answer"] or
                row.get("raw_answer_sha256") !=
                base._sha(row["raw_answer"].encode("utf-8")) or
                row.get("score") != base.score_decision(row["raw_answer"], oracle) or
                report["row_sha256"].get(row["arm"]) !=
                base._sha(dumps(row).encode("utf-8"))):
            raise ValueError("run37_native_row_incomplete")
        env = row.get("envelope")
        if not study.verify_envelope(env):
            raise ValueError("run37_native_envelope_invalid")
        if (env.get("experiment_arm") != row["arm"] or
                env.get("fixture_id") != FIXTURE or env.get("seed") != SEED):
            raise ValueError("run37_native_envelope_arm_mismatch")
        context = json.loads(env["messages"][1]["content"])
        if set(context) != {"current_source", "analysts"}:
            raise ValueError("run37_oracle_or_hidden_context")
    return {
        "status": "PASS_SCOPED_C3_RULE_USE_NATIVE_NO_STEP2_GATE",
        "rows": len(rows), "canonical_gate_pass": False,
        "phone_measured": False, "jepa_weight": 0,
        "whole_system_complete": False,
    }


def _run_unlocked(installed_home, evidence_dir):
    reg = prereg()
    home = Path(installed_home).expanduser().resolve()
    evidence = Path(evidence_dir).expanduser().absolute()
    if (evidence.exists() or not evidence.parent.is_dir() or
            evidence.parent.is_symlink()):
        raise ValueError("run37_fresh_private_evidence_dir_required")
    manager, model, runner_hash = base._installed(home)
    cfg = dict(base.DEFAULTS)
    cfg.update(seed=SEED, c3_decode_mode="server", answer_tokens=256,
               context_tokens=2048, temperature=0.1)
    evidence.mkdir(mode=0o700)
    raw_path = evidence / "C3_RULE_USE_NATIVE_RAW.json"
    receipt_path = evidence / "RECEIPT.json"
    report = {
        "schema": SCHEMA, "fixture_id": FIXTURE, "seed": SEED,
        "model_sha256": base.C3_GGUF_SHA256, "runner_sha256": runner_hash,
        "rows": [], "row_sha256": {}, "failed_attempts": [],
        "canonical_gate_pass": False, "phone_measured": False,
        "jepa_weight": 0,
    }
    receipt = {
        **reg, "status": "RUNNING", "native_executed": False,
        "source_unchanged": None, "model_unchanged": None,
        "runner_unchanged": None, "raw_report_sha256": None,
    }

    def save():
        atomic_write(raw_path, dumps(report))
        atomic_write(receipt_path, dumps(receipt))

    save()
    active_attempt = None
    try:
        for arm in ARMS:
            active_attempt = {"arm": arm, "raw_answer": "",
                              "native_metrics": {}, "process_reaped": False}
            env = study.build_envelope(arm)
            if study.verify_envelope(env) is not True:
                raise ValueError("run37_native_envelope_invalid")
            context = json.loads(env["messages"][1]["content"])
            if set(context) != {"current_source", "analysts"}:
                raise ValueError("run37_oracle_in_native_input")
            runner = base.LlamaRunner(home, "C3_LANGUAGE", model, cfg)
            raw = ""
            metrics = {}
            try:
                deadline = time.monotonic() + cfg["deadline_seconds"]
                for chunk in runner.generate(
                        env["messages"], threading.Event(), deadline,
                        cfg["answer_tokens"], frozen_consumer.SCHEMA,
                        seed=SEED):
                    raw += chunk
                    active_attempt["raw_answer"] = raw
                metrics = dict(runner.last_metrics)
                active_attempt["native_metrics"] = metrics
            finally:
                release = runner.unload()
                active_attempt["process_reaped"] = release.get("process_reaped") is True
            if (metrics.get("status") != "FINAL" or
                    release.get("process_reaped") is not True):
                raise ValueError("run37_native_not_final_or_not_reaped")
            oracle = next(f["oracle"] for f in cf.FIXTURES if f["id"] == FIXTURE)
            row = {
                "arm": arm, "envelope": env, "raw_answer": raw,
                "raw_answer_sha256": base._sha(raw.encode("utf-8")),
                "score": base.score_decision(raw, oracle),
                "native_status": metrics["status"],
                "native_metrics": metrics, "process_reaped": True,
                "oracle_visible_to_native": False,
                "model_sha256": base.C3_GGUF_SHA256,
                "runner_sha256": runner_hash, "envelope_verified": True,
            }
            report["rows"].append(row)
            report["row_sha256"][arm] = base._sha(dumps(row).encode("utf-8"))
            receipt["native_executed"] = True
            active_attempt = None
            save()
        result = verify_report(report, base.C3_GGUF_SHA256, runner_hash)
        _, after_model, after_runner_hash = base._installed(home)
        receipt["model_unchanged"] = file_hash(after_model) == base.C3_GGUF_SHA256
        receipt["runner_unchanged"] = after_runner_hash == runner_hash
        receipt["source_unchanged"] = prereg() == reg
        if not all((receipt["model_unchanged"], receipt["runner_unchanged"],
                    receipt["source_unchanged"])):
            raise ValueError("run37_native_artifacts_or_source_changed")
        receipt["raw_report_sha256"] = base._sha(raw_path.read_bytes())
        receipt.update(result)
    except BaseException as exc:
        if active_attempt is not None:
            active_attempt["error_type"] = type(exc).__name__
            report["failed_attempts"].append(active_attempt)
        receipt["status"] = "FAIL_RETAIN_RAW"
        receipt["error_type"] = type(exc).__name__
        save()
        raise
    save()
    return receipt


def run(installed_home, evidence_dir):
    home = Path(installed_home).expanduser().resolve()
    lock_path = home / "data/coordinator.lock"
    if not lock_path.is_file():
        raise ValueError("run37_existing_native_lock_required")
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("run37_active_native_owner") from exc
        return _run_unlocked(home, evidence_dir)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-home", required=True)
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args(argv)
    receipt = run(args.installed_home, args.evidence_dir)
    print(dumps({"status": receipt["status"], "rows": receipt["rows"],
                 "canonical_gate_pass": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
