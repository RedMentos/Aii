"""Run34 one-fixture C3-only native quote intervention, review-only.

Explicit native execution requires a preinstalled hash-verified V13 home and
fresh private evidence directory. No B1/B2 inference, Runtime/Store mutation,
learning, F5 authority, phone proof or STEP2 gate promotion.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import threading
import time

from scripts import run33_b2_c3_counterfactual_envelopes as cf
from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS
from v13.models import ModelManager, catalog
from v13.runners import LlamaRunner
from v13.utility import score_decision
from tests import integration_step2_utility as frozen_consumer

ROOT = Path(__file__).resolve().parents[1]
CATALOG_BLOB = "7af05962af41d0bc3f7dd18ef01d4eba55eabf99"
RUNNER_TAR_SHA256 = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
C3_GGUF_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
C3_REVISION = "657e078c94084481950a2d555a941481f715536b"
RUN33_SOURCE_BLOB = "b1d58d7e0c3937787cf15dd801e278de25845879"
FROZEN_RUNNERS_BLOB = "efda7aa1aa5729e974d0d641870d4da05d21c961"
FROZEN_UTILITY_BLOB = "f4a92dab9c4a40761d64394cdca1c052e9a76bfd"
FIXTURE = "Velaris"
SEED = 20261121
ARMS = cf.ARMS


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _git_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") +
                        b"\0" + data).hexdigest()


def prereg():
    source = cf.prereg()
    if (_git_blob(ROOT / "specs/models.json") != CATALOG_BLOB or
            _git_blob(ROOT / "scripts/run33_b2_c3_counterfactual_envelopes.py")
            != RUN33_SOURCE_BLOB or
            _git_blob(ROOT / "v13/runners.py") != FROZEN_RUNNERS_BLOB or
            _git_blob(ROOT / "v13/utility.py") != FROZEN_UTILITY_BLOB):
        raise ValueError("native_source_or_catalog_changed")
    specs = catalog()
    runner = specs["runner"]
    c3 = specs["models"]["language"]
    if (runner["tag"] != "b10964" or
            runner["linux_binaries"]["linux-x86_64"]["sha256"] != RUNNER_TAR_SHA256 or
            c3["revision"] != C3_REVISION or
            len(c3["files"]) != 1 or
            c3["files"][0]["sha256"] != C3_GGUF_SHA256 or
            c3["files"][0]["size"] != 219312832 or
            source["native_executed"] is not False or
            FIXTURE not in {f["id"] for f in cf.FIXTURES} or
            SEED not in cf.SEEDS):
        raise ValueError("native_artifact_or_source_prereg_changed")
    return {
        "schema": "v13.run34.c3_only.native_pilot.prereg.v1",
        "scope": "LINUX_NATIVE_ONE_FIXTURE_C3_ONLY_FUTURE",
        "fixture_id": FIXTURE, "seed": SEED, "arms": list(ARMS),
        "source_cases_sha256": cf.CASES_SHA256,
        "c3_model_sha256": C3_GGUF_SHA256, "c3_revision": C3_REVISION,
        "runner_tar_sha256": RUNNER_TAR_SHA256,
        "consumer_source_blob": cf.FROZEN_CONSUMER_BLOB,
        "run33_source_blob": RUN33_SOURCE_BLOB,
        "runner_source_blob": FROZEN_RUNNERS_BLOB,
        "scorer_source_blob": FROZEN_UTILITY_BLOB,
        "canonical_gate_pass": False, "native_executed": False,
        "phone_measured": False, "jepa_weight": 0,
        "whole_system_complete": False,
    }


def _installed(home):
    home = Path(home)
    if (not home.is_dir() or
            not (home / "config/models.json").is_file() or
            not (home / "config/runner.json").is_file() or
            not (home / "bin/llama-server").is_file()):
        raise ValueError("pinned_installed_home_required")
    manager = ModelManager(home)
    result = manager.verify(deep=True)
    if "language" not in result or result["language"]["ok"] is not True:
        raise ValueError("installed_c3_unverified")
    if manager.revision("C3_LANGUAGE") != C3_REVISION:
        raise ValueError("installed_c3_revision_changed")
    path = manager.path_for("C3_LANGUAGE")
    if file_hash(path) != C3_GGUF_SHA256:
        raise ValueError("installed_c3_bytes_changed")
    manifest = json.loads((home / "config/runner.json").read_text())
    runner = home / "bin/llama-server"
    binary_hash = file_hash(runner)
    if (manifest.get("tag") != "b10964" or
            manifest.get("binary_sha256") != binary_hash):
        raise ValueError("installed_runner_unverified")
    return manager, path, binary_hash


def verify_report(report, model_sha, binary_sha):
    if (not isinstance(report, dict) or
            report.get("schema") != "v13.run34.c3_only.native_pilot.raw.v1" or
            report.get("fixture_id") != FIXTURE or
            report.get("seed") != SEED or
            report.get("model_sha256") != model_sha or
            report.get("runner_sha256") != binary_sha or
            report.get("canonical_gate_pass") is not False or
            report.get("phone_measured") is not False or
            report.get("jepa_weight") != 0 or
            report.get("failed_attempts") != []):
        raise ValueError("native_report_header_invalid")
    rows = report.get("rows")
    if (not isinstance(rows, list) or len(rows) != len(ARMS) or
            [r.get("arm") for r in rows if isinstance(r, dict)] != list(ARMS) or
            len(report.get("row_sha256", {})) != len(ARMS)):
        raise ValueError("native_report_rows_invalid")
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
                row.get("runner_sha256") != binary_sha or
                row.get("envelope_verified") is not True or
                type(row.get("raw_answer")) is not str or
                not row["raw_answer"] or
                row.get("raw_answer_sha256") !=
                _sha(row["raw_answer"].encode("utf-8")) or
                row.get("score") != score_decision(row["raw_answer"], oracle) or
                report["row_sha256"].get(row["arm"]) != _sha(dumps(row).encode("utf-8"))):
            raise ValueError("native_row_incomplete")
        envelope = row.get("envelope")
        if not cf.verify_envelope(envelope):
            raise ValueError("native_envelope_invalid")
        context = json.loads(envelope["messages"][1]["content"])
        if set(context) != {"current_source", "analysts"}:
            raise ValueError("oracle_or_hidden_context_exposed")
    return {"status": "PASS_SCOPED_C3_ONLY_NATIVE_NO_STEP2_GATE",
            "rows": len(rows), "canonical_gate_pass": False,
            "phone_measured": False, "jepa_weight": 0,
            "whole_system_complete": False}


def _run_unlocked(installed_home, evidence_dir):
    reg = prereg()
    home = Path(installed_home).expanduser().resolve()
    evidence = Path(evidence_dir).expanduser().absolute()
    if (evidence.exists() or not evidence.parent.is_dir() or
            evidence.parent.is_symlink()):
        raise ValueError("fresh_private_evidence_dir_required")
    manager, model, runner_hash = _installed(home)
    cfg = dict(DEFAULTS)
    cfg["seed"] = SEED
    cfg["c3_decode_mode"] = "server"
    cfg["answer_tokens"] = 256
    cfg["context_tokens"] = 2048
    cfg["temperature"] = 0.1
    evidence.mkdir(mode=0o700)
    receipt_path = evidence / "RECEIPT.json"
    raw_path = evidence / "C3_NATIVE_RAW.json"
    report = {
        "schema": "v13.run34.c3_only.native_pilot.raw.v1",
        "fixture_id": FIXTURE, "seed": SEED,
        "model_sha256": C3_GGUF_SHA256,
        "runner_sha256": runner_hash,
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
            envelope = cf.build_envelope(FIXTURE, arm, SEED)
            cf.verify_envelope(envelope)
            context = json.loads(envelope["messages"][1]["content"])
            if set(context) != {"current_source", "analysts"}:
                raise ValueError("oracle_in_native_input")
            runner = LlamaRunner(home, "C3_LANGUAGE", model, cfg)
            raw = ""
            metrics = {}
            try:
                deadline = time.monotonic() + cfg["deadline_seconds"]
                for chunk in runner.generate(
                        envelope["messages"], threading.Event(), deadline,
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
                raise ValueError("native_c3_not_final_or_not_reaped")
            oracle = next(f["oracle"] for f in cf.FIXTURES
                          if f["id"] == FIXTURE)
            row = {
                "arm": arm, "envelope": envelope,
                "raw_answer": raw,
                "raw_answer_sha256": _sha(raw.encode("utf-8")),
                "score": score_decision(raw, oracle),
                "native_status": metrics["status"],
                "native_metrics": metrics,
                "process_reaped": True,
                "oracle_visible_to_native": False,
                "model_sha256": C3_GGUF_SHA256,
                "runner_sha256": runner_hash,
                "envelope_verified": True,
            }
            report["rows"].append(row)
            report["row_sha256"][arm] = _sha(dumps(row).encode("utf-8"))
            receipt["native_executed"] = True
            active_attempt = None
            save()
        result = verify_report(report, C3_GGUF_SHA256, runner_hash)
        after_manager, after_model, after_runner_hash = _installed(home)
        receipt["model_unchanged"] = (file_hash(after_model) == C3_GGUF_SHA256)
        receipt["runner_unchanged"] = (after_runner_hash == runner_hash)
        receipt["source_unchanged"] = (prereg() == reg)
        if not all((receipt["model_unchanged"], receipt["runner_unchanged"],
                    receipt["source_unchanged"])):
            raise ValueError("native_artifacts_or_source_changed")
        receipt["raw_report_sha256"] = _sha(raw_path.read_bytes())
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
    """Exclusive installed-home owner; never overlap active chat/native owner."""
    home = Path(installed_home).expanduser().resolve()
    lock_path = home / "data/coordinator.lock"
    if not lock_path.is_file():
        raise ValueError("existing_native_coordinator_lock_required")
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("active_native_owner") from exc
        return _run_unlocked(home, evidence_dir)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-home", required=True)
    parser.add_argument("--evidence-dir", required=True)
    args = parser.parse_args(argv)
    result = run(args.installed_home, args.evidence_dir)
    print(dumps({"status": result["status"], "rows": result["rows"],
                 "canonical_gate_pass": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
