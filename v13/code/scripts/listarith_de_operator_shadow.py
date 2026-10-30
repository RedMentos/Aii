"""Explicit one-source C3 German arithmetic operator probe; SHADOW_ONLY.

Two modes: user-supplied typed JSON software replay, or real local C3 only
after original seed83 model/binary/age/source pin verification. No ToolStep/C5,
no learning, approval or promotion. Raw is private 0600 and never printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time

from v13.agi import listarith
from v13.agi import listarith_de_shadow_pipeline as pipeline
from v13.agi import listarith_de_closedworld_candidate as closedworld
from v13.common import file_hash
from v13.config import initialize
from v13.models import ModelManager
from v13.runners import LlamaRunner
from scripts import listarith_de83_native_shadow as pilot

SCHEMA = "v13.c3.de.operator_shadow.v1"
RAW_MAX_BYTES = 16384

# This is an allowlist of observations, NOT authority fields. The native
# producer must never replace Age0/learning/gate/evidence-level constants.
NATIVE_OBSERVATIONS = frozenset((
    "native_final", "postclose_process_reaped", "native_metrics",
    "native_pid", "release", "error_type", "error_message",
    "release_error_type",
))


def _native_receipt_admissible(receipt):
    """Gate raw model text on complete, typed, postclose native evidence."""
    if not isinstance(receipt, dict):
        return False
    raw = receipt.get("raw_output")
    metrics = receipt.get("native_metrics")
    release = receipt.get("release")
    pid = receipt.get("native_pid")
    try:
        raw_ok = (type(raw) is str and bool(raw)
                  and len(raw.encode("utf-8")) <= RAW_MAX_BYTES)
    except UnicodeError:
        raw_ok = False
    return bool(
        raw_ok
        and receipt.get("native_attempted") is True
        and receipt.get("native_final") is True
        and receipt.get("postclose_process_reaped") is True
        and type(pid) is int and pid > 0
        and isinstance(metrics, dict) and metrics.get("status") == "FINAL"
        and isinstance(release, dict) and release.get("process_reaped") is True
        and receipt.get("error_type") is None
        and receipt.get("release_error_type") is None
    )


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read_text(path, *, max_bytes):
    p = Path(path)
    if not p.is_file():
        raise ValueError("INPUT_REGULAR_FILE_REQUIRED")
    data = p.read_bytes()
    if not data or len(data) > max_bytes:
        raise ValueError("INPUT_SIZE_OUT_OF_SCOPE")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("INPUT_UTF8_REQUIRED") from exc


def _native_preflight(home):
    # The original registered source/model/binary cohort is immutable.
    pilot.fixtures()
    home = Path(home)
    cfg = initialize(home)
    if (cfg["learning_mode"] != "RECORD_ONLY"
            or cfg["system_stage"] != 0 or cfg["latents_enabled"]
            or cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE_OR_JEPA_CONFIG_CHANGED")
    mm = ModelManager(home)
    verified = mm.verify(deep=True)
    if ("language" not in verified or not verified["language"]["ok"]
            or not verified["language"]["hash_checked"]):
        raise ValueError("LANGUAGE_MODEL_NOT_HASH_VERIFIED")
    if mm.revision("C3_LANGUAGE") != pilot.MODEL_REVISION:
        raise ValueError("C3_REVISION_CHANGED")
    model_path = mm.path_for("C3_LANGUAGE")
    if file_hash(model_path) != pilot.MODEL_SHA256:
        raise ValueError("MODEL_SHA256_CHANGED")
    manifest = json.loads((home / "config/runner.json").read_text(encoding="utf-8"))
    if (manifest.get("binary_sha256") != pilot.BINARY_SHA256
            or file_hash(home / "bin/llama-server") != pilot.BINARY_SHA256):
        raise ValueError("NATIVE_BINARY_SHA256_CHANGED")
    return home, cfg, model_path


def _native_one(home, text):
    """Return a closed process receipt; never mislabel fake/native failures."""
    raw = None
    runner = None
    receipt = {"native_attempted": True, "native_final": False,
               "postclose_process_reaped": False, "raw_output": None,
               "native_metrics": None, "native_pid": None, "release": None,
               "error_type": None}
    try:
        home, cfg, model_path = _native_preflight(home)
        runner = LlamaRunner(home, "C3_LANGUAGE", model_path, cfg)
        raw = "".join(runner.generate(
            [{"role": "system", "content": listarith.READ_SYSTEM},
             {"role": "user", "content": text}],
            threading.Event(), time.monotonic() + 75,
            max_tokens=192, schema=listarith.READ_SCHEMA, seed=83))
        receipt["native_metrics"] = runner.last_metrics
        receipt["native_pid"] = runner.proc.pid if runner.proc else None
        if (receipt["native_pid"] is None
                or runner.last_metrics.get("status") != "FINAL"):
            raise ValueError("NATIVE_FINAL_OR_PID_MISSING")
        receipt["native_final"] = True
    except BaseException as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["error_message"] = str(exc)[:200]
    finally:
        if runner is not None:
            try:
                receipt["release"] = runner.unload()
                receipt["postclose_process_reaped"] = bool(
                    receipt["release"]["process_reaped"] and runner.proc is None)
            except BaseException as exc:
                receipt["release_error_type"] = type(exc).__name__
        if not receipt["postclose_process_reaped"]:
            receipt["error_type"] = receipt["error_type"] or "NATIVE_RELEASE_RED"
        if receipt["native_final"] and receipt["postclose_process_reaped"]:
            receipt["raw_output"] = raw
    return receipt


def _write_private_new(path, report):
    """O_EXCL avoids overwrites/symlinks; no silent data loss on failure."""
    p = Path(path)
    data = (json.dumps(report, sort_keys=True, ensure_ascii=False,
                       indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(p, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=False) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    finally:
        os.close(fd)


def run(source_file, out, *, raw_json_file=None, home=None):
    if (raw_json_file is None) == (home is None):
        raise ValueError("EXACTLY_ONE_OF_RAW_REPLAY_OR_NATIVE_HOME")
    text = _read_text(source_file, max_bytes=4 * listarith.MAX_TEXT)
    if not text.strip() or len(text) > listarith.MAX_TEXT:
        raise ValueError("SOURCE_OUT_OF_SCOPE")
    report = {
        "schema": SCHEMA, "source_sha256": _sha(text.encode("utf-8")),
        "raw_output": None, "raw_sha256": None,
        "evidence_level": ("SOFTWARE_USER_SUPPLIED_RAW" if raw_json_file is not None
                           else "LOCAL_NATIVE_IF_VERIFIED"),
        "native_attempted": home is not None, "native_final": False,
        "postclose_process_reaped": False,
        "live_tool_execution": False, "external_action_authority": False,
        "learning_mode": "RECORD_ONLY", "step2_gate_promoted": False,
        "b3_promoted": False, "body_jepa_available": False,
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False,
    }
    if raw_json_file is not None:
        raw = _read_text(raw_json_file, max_bytes=RAW_MAX_BYTES)
    else:
        native = _native_one(home, text)
        if not isinstance(native, dict):
            native = {"error_type": "INVALID_NATIVE_RECEIPT"}
        # A malformed receipt cannot mutate hard negative gates or provenance.
        report.update({k: native[k] for k in NATIVE_OBSERVATIONS if k in native})
        report["native_receipt_admitted"] = _native_receipt_admissible(native)
        candidate = native.get("raw_output")
        raw = candidate if report["native_receipt_admitted"] else None
        if raw is None and candidate is not None:
            # Preserve a bounded, private quarantine for failed attempts.
            # It is never fed to arithmetic or presented as verified native.
            if type(candidate) is str:
                try:
                    candidate_bytes = candidate.encode("utf-8")
                except UnicodeError:
                    candidate_bytes = None
                if candidate_bytes is not None:
                    report["quarantined_raw_sha256"] = _sha(candidate_bytes)
                    report["quarantined_raw_bytes"] = len(candidate_bytes)
                    if len(candidate_bytes) <= RAW_MAX_BYTES:
                        report["quarantined_raw_output"] = candidate
            report["raw_output"] = None
            report["error_type"] = "NATIVE_RECEIPT_UNVERIFIED"
    if raw is None:
        report.update(status="SHADOW_ABSTAIN", reason=report.get("error_type") or
                      "NATIVE_UNAVAILABLE", baseline=None, closedworld=None)
    else:
        report["raw_output"] = raw
        report["raw_sha256"] = _sha(raw.encode("utf-8"))
        report["baseline"] = pipeline.evaluate(text, raw)
        report["closedworld"] = closedworld.evaluate(text, raw)
        report["status"] = report["closedworld"]["status"]
        report["reason"] = report["closedworld"]["reason"]
    _write_private_new(out, report)
    return {k: report[k] for k in
            ("status", "reason", "evidence_level", "native_attempted",
             "native_final", "postclose_process_reaped",
             "step2_gate_promoted", "whole_system_complete")}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-file", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--raw-json-file", type=Path)
    g.add_argument("--native", action="store_true")
    p.add_argument("--home", type=Path)
    args = p.parse_args(argv)
    if args.native != (args.home is not None):
        p.error("--native requires --home; --home forbidden for replay")
    try:
        result = run(args.source_file, args.out,
                     raw_json_file=args.raw_json_file,
                     home=args.home if args.native else None)
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error_type": type(exc).__name__}),
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
