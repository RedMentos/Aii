#!/usr/bin/env python3
"""Default-OFF local JEF/C3->C5/F3 DRAFT->C6 operator diagnostic.

No visible answer, TTY approval, output commit, tool dispatch or learning.
Native mode requires pinned installed model and runner; synthetic modes are
explicit software tests, not model evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from v13.common import dumps, file_hash
from v13.runtime import Runtime
from v13.jef_c3_typed_envelope_candidate import build_jef_c3_typed_envelope
from v13.jef_c3_c5_c6_fallback_draft_candidate import stage, preflight, STAGED

C3_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
FIELDS = frozenset(("project", "domain", "policy_source",
                    "sheet_source", "current"))
MODES = ("native", "synthetic_exact", "synthetic_wrong")
MAX_INPUT_BYTES = 16384


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _nonfinite(_):
    raise ValueError("NONFINITE_JSON")


def _read_input(path):
    # A FIFO without a writer must not block an opt-in diagnostic forever.
    # O_NOFOLLOW also prevents a final-path symlink redirect.
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("INPUT_NOFOLLOW_UNAVAILABLE")
    flags = (os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
             | getattr(os, "O_CLOEXEC", 0))
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("INPUT_NOT_REGULAR_RED")
        chunks = []
        remaining = MAX_INPUT_BYTES + 1
        while remaining:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
    finally:
        os.close(fd)
    if not 0 < len(raw) <= MAX_INPUT_BYTES:
        raise ValueError("INPUT_SIZE_RED")
    data = json.loads(raw.decode("utf-8", "strict"),
                      object_pairs_hook=_unique, parse_constant=_nonfinite)
    if type(data) is not dict or set(data) != FIELDS:
        raise ValueError("INPUT_FIELDS_RED")
    if not all(type(data[k]) is str for k in FIELDS):
        raise ValueError("INPUT_TYPE_RED")
    project, domain = data["project"], data["domain"]
    if (re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", project) is None
            or re.fullmatch(r"[A-Za-z][A-Za-z -]{0,39}", domain) is None):
        raise ValueError("PROJECT_DOMAIN_RED")
    for key in ("policy_source", "sheet_source", "current"):
        value = data[key]
        if not 0 < len(value) <= 2048:
            raise ValueError("SOURCE_SIZE_RED")
        if any(c in value for c in "\r\n\t\x00"):
            raise ValueError("SOURCE_CONTROL_RED")
    if (not data["policy_source"].startswith(
            f"Project {project} archived {domain} policy.")
            or not data["sheet_source"].startswith(
            f"Project {project} latest {domain} option sheet.")
            or not data["current"].startswith(f"Project {project}.")):
        raise ValueError("SOURCE_IDENTITY_RED")
    return data, _sha(raw)


def _result(status, *, mode=None, **extra):
    return {
        "schema": "v13.jef_c3_c5_c6_operator_cli_shadow.v1",
        "status": status, "mode": mode,
        "delivery_authority": 0, "output_committed": False,
        "tool_dispatches": 0, "learning_authority": 0,
        "native_proof": False, "real_tty_approved": False,
        "age0": "RECORD_ONLY", **extra,
    }


def _finalize_native_release(report, releases):
    """Fail closed when native process reaping cannot be evidenced.

    A software receipt check, not proof of actual native execution.
    """
    reaped = (
        report.get("native_model_called") is True
        and any(x.get("before") is not None for x in releases)
        and all(x.get("process_reaped") is True for x in releases)
    )
    report["native_process_reaped"] = bool(reaped)
    if (report.get("status") == "SHADOW_DRAFT_PREFLIGHT_READY"
            and not reaped):
        report["status"] = "NATIVE_RELEASE_RED"


def run(home, input_file, mode, *, operator_opt_in=False,
        callback_opt_in=False):
    """Return redacted diagnostic; do not log the operator's source values."""
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result("OFF", mode=mode, input_read=False, runtime_opened=False)
    if mode not in MODES:
        return _result("INVALID_MODE", mode=mode, input_read=False,
                       runtime_opened=False)
    try:
        data, input_sha = _read_input(input_file)
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError):
        return _result("INPUT_RED", mode=mode, input_read=True,
                       runtime_opened=False)
    try:
        runtime = Runtime(Path(home))
    except Exception:
        return _result("RUNTIME_RED", mode=mode, input_read=True,
                       runtime_opened=False)
    report = _result("ERROR", mode=mode, input_read=True,
                     runtime_opened=True, input_sha256=input_sha,
                     native_model_called=False,
                     native_process_reaped=None)
    try:
        runtime.sleep.cycle.set_policy("enabled", "off")
        if mode == "native":
            try:
                model_sha = file_hash(runtime.models.path_for("C3_LANGUAGE"))
                runner_path = Path(os.environ.get(
                    "V13_LLAMA_SERVER", str(Path(home)/"bin/llama-server")))
                runner_sha = file_hash(runner_path)
            except Exception:
                report["status"] = "NATIVE_BINDING_RED"
                return report
            report["native_model_sha256"] = model_sha
            report["runner_sha256"] = runner_sha
            if model_sha != C3_SHA256 or runner_sha != RUNNER_SHA256:
                report["status"] = "NATIVE_BINDING_RED"
                return report

        project, domain = data["project"], data["domain"]
        policy_key = f"Project {project} archived {domain} policy"
        sheet_key = f"Project {project} latest {domain} option sheet"

        def record(key, value):
            e = runtime.store.event(runtime.session, "Record: " + key)
            mid = runtime.memory.feedback(
                e["event_id"], "fact", value, permission="record",
                key=key, scope="session")
            runtime.memory.candidate(mid, runtime.session)
            return mid

        ids = [record(policy_key, data["policy_source"]),
               record(sheet_key, data["sheet_source"])]
        event = runtime.store.event(runtime.session, data["current"])
        envelope = build_jef_c3_typed_envelope(
            runtime.memory, runtime.session, event["event_id"],
            event["source_ref"], ids, operator_opt_in=True)
        if envelope.get("status") != "JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL":
            report["status"] = "SOURCE_ADMISSION_RED"
            report["source_status"] = envelope.get("status")
            return report
        action = envelope["typed_jef_action"]

        def generate(messages):
            if mode == "synthetic_exact":
                return action
            if mode == "synthetic_wrong":
                return "Option " + action
            if dumps(messages) != dumps(envelope["messages"]):
                raise ValueError("PROMPT_CHANGED")
            runner = runtime.pool.get("C3_LANGUAGE")
            report["native_model_called"] = True
            output = "".join(runner.generate(
                messages, runtime.cancel_event, time.monotonic() + 90,
                32, None, seed=13))
            report["native_output_sha256"] = _sha(output.encode("utf-8"))
            metrics = dict(runner.last_metrics)
            report["native_final"] = metrics.get("status") == "FINAL"
            report["actual_model"] = metrics.get("actual_model")
            if not report["native_final"]:
                raise RuntimeError("NATIVE_NOT_FINAL")
            return output

        staged = stage(
            runtime.memory, runtime.session, event["event_id"],
            event["source_ref"], ids, generate,
            operator_opt_in=True, callback_opt_in=True)
        report["stage_status"] = staged.get("status")
        if staged.get("status") != STAGED:
            report["status"] = "DRAFT_STAGE_RED"
            return report
        report["candidate_sha256"] = staged["candidate_sha256"]
        report["source_only_fallback"] = staged["source_only_fallback"]
        report["model_formatter_status"] = staged["model_formatter_status"]
        report["draft_message_id"] = staged["draft_message_id"]
        c6 = preflight(
            runtime.memory, runtime.session, event["event_id"],
            event["source_ref"], ids, staged, operator_opt_in=True)
        report["c6_status"] = c6.get("status")
        report["preflight_only"] = c6.get("preflight_only") is True
        report["shadow_draft_may_exist"] = True
        live = runtime.store.one(
            "SELECT COUNT(*) AS n FROM messages WHERE session_id=? "
            "AND role='assistant' AND status IN ('FINAL','OUTPUT_COMMITTED')",
            (runtime.session,))["n"]
        report["no_live_output"] = live == 0
        report["status"] = (
            "SHADOW_DRAFT_PREFLIGHT_READY"
            if c6.get("status") == "NEEDS_REAL_TTY_APPROVAL"
            and report["preflight_only"] and report["no_live_output"]
            else "C6_PREFLIGHT_RED")
        return report
    except Exception as exc:
        report["status"] = "CLI_EXECUTION_RED"
        report["error_type"] = type(exc).__name__
        return report
    finally:
        # A failed unload must never prevent the independent Store close.
        try:
            runtime.pool.unload()
        except Exception:
            report["pool_release_status"] = "UNLOAD_RED"
            report["status"] = "CLI_CLOSE_RED"
        if mode == "native":
            try:
                _finalize_native_release(
                    report, list(runtime.pool.release_history))
            except Exception:
                report["native_process_reaped"] = False
                report["status"] = "CLI_CLOSE_RED"
        try:
            runtime.close()
        except Exception:
            report["close_status"] = "CLOSE_RED"
            report["status"] = "CLI_CLOSE_RED"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--input-file", type=Path, required=True)
    p.add_argument("--mode", choices=MODES, required=True)
    p.add_argument("--operator-opt-in", action="store_true")
    p.add_argument("--callback-opt-in", action="store_true")
    a = p.parse_args()
    result = run(a.home, a.input_file, a.mode,
                 operator_opt_in=a.operator_opt_in,
                 callback_opt_in=a.callback_opt_in)
    print(dumps(result))
    raise SystemExit(0 if result["status"] in (
        "OFF", "SHADOW_DRAFT_PREFLIGHT_READY") else 1)


if __name__ == "__main__":
    main()
