#!/usr/bin/env python3
"""Run117CY one real-Store F1/F5/JEF source-only C3 native callback smoke.

Frozen Saffron source replay, not independent utility. No delivery or learning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from scripts import run117cn_c3_source_independence_fixture as frozen
from scripts.run115j_typed_jef_role_native import RUNNER_SHA
from v13.common import atomic_write, dumps, file_hash
from v13.config import DEFAULTS, initialize, save_config
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.runners import LlamaRunner
from v13.store import audit_closed
from v13 import jef_c3_source_callback_shadow_candidate as guard

SEED = 117041
MODEL_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REV = "657e078c94084481950a2d555a941481f715536b"
MODEL_FILE = "LFM2.5-350M-QAD-Q4_0.gguf"
SCHEMA = "v13.run117cy.live_store_native_c3_source_only.v1"
CONFIG = DEFAULTS | {
    "threads": 2, "temperature": 0.0, "seed": SEED,
    "observer_mode": "off", "answer_tokens": 96,
    "deadline_seconds": 120, "observer_seconds": 30,
    "body_residency_mb": 0, "history_turns": 0,
    "memory_top_k": 0, "teacher_enabled": False,
    "learning_mode": "RECORD_ONLY", "context_tokens": 2048,
    "native_cache_ram_mb": 0, "native_ctx_checkpoints": 0,
}
NEGATIVE = {
    "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
    "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
    "world_jepa": "SHADOW", "jepa_weight": 0,
    "redmi_measured": False, "whole_system_complete": False,
    "delivery_authority": 0, "learning_authority": 0,
    "tool_dispatches": 0, "output_committed": False,
    "native_body_calls": 0, "native_c2_calls": 0,
    "native_jef_calls": 0, "independent_generalization": False,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(installed):
    """Validate exact catalog model and canonical staged runner symlink."""
    installed = Path(installed)
    manager = ModelManager(installed)
    model = manager.path_for("C3_LANGUAGE")
    binary = installed / "bin/llama-server"
    manifest = installed / "config/runner.json"
    if (model.is_symlink() or not model.is_file()
            or model.name != MODEL_FILE
            or model.stat().st_size != 219312832
            or manager.revision("C3_LANGUAGE") != MODEL_REV
            or file_hash(model) != MODEL_SHA
            or not binary.is_symlink() or not manifest.is_file()
            or manifest.is_symlink()):
        raise ValueError("RUN117CY_MODEL_OR_RUNNER_PIN_RED")
    try:
        meta = json.loads(manifest.read_text())
        direct = Path(os.readlink(binary))
        target = binary.resolve(strict=True)
        rel = target.relative_to((installed / "bin").resolve(strict=True))
        if (meta.get("tag") != "b10964"
                or meta.get("platform") != "linux-x86_64"
                or meta.get("binary_sha256") != RUNNER_SHA
                or not direct.is_absolute() or direct.is_symlink()
                or direct != target or not target.is_file()
                or target.name != "llama-server"
                or len(rel.parts) < 3
                or not rel.parts[0].startswith(".llama-b10964-")
                or file_hash(binary) != RUNNER_SHA):
            raise ValueError("RUN117CY_RUNNER_BINDING_RED")
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError("RUN117CY_RUNNER_BINDING_RED") from exc
    return model


def run(installed, home, out, *, runner_factory=LlamaRunner, pin_factory=pin):
    installed, home, out = Path(installed), Path(home), Path(out)
    if (home.exists() or out.exists() or not home.parent.is_dir()
            or not out.parent.is_dir() or home.parent.is_symlink()
            or out.parent.is_symlink()):
        raise FileExistsError("RUN117CY_FRESH_HOME_AND_OUT_REQUIRED")
    model = pin_factory(installed)
    items = frozen.fixtures()
    if (len(items) != 9 or frozen.SEED != SEED
            or frozen.TABLE_SHA256 !=
            "fb5708c82f4d62338eb080264ec6c2cbf8234fc9b5845abc3c0e53e513597335"):
        raise ValueError("RUN117CY_FROZEN_SOURCE_RED")
    item = items[0]
    if item["project"] != "Saffron" or item["index"] != 0:
        raise ValueError("RUN117CY_CASE_RED")
    initialize(home)
    save_config(home, CONFIG)
    out.mkdir(mode=0o700)
    report = {
        "schema": SCHEMA, "status": "INCOMPLETE",
        "evidence_class": "LINUX_NATIVE_C3_REAL_STORE_SOURCE_ONLY_STRUCTURAL_REPLAY",
        "seed": SEED, "table_sha256": frozen.TABLE_SHA256,
        "project": item["project"], "model_sha256": MODEL_SHA,
        "model_revision": MODEL_REV, "runner_sha256": RUNNER_SHA,
        "native_c3_calls": 0, "native_final": False,
        "process_reaped": False, "source_rechecked": False,
        "closed_store_ok": False, "native_output": "",
        "native_metrics": {}, "guard": None,
        "error_type": None, **NEGATIVE,
    }
    def save():
        atomic_write(out / "report.json", dumps(report))
    save()
    runtime = None
    try:
        runtime = Runtime(home)
        mids = []
        topic = frozen.TABLE[0][1]
        for key, value in (
            (f"Project Saffron archived {topic} policy", item["policy_source"]),
            (f"Project Saffron latest {topic} option sheet", item["sheet_source"]),
        ):
            event = runtime.store.event(runtime.session, "Record: " + key)
            mid = runtime.memory.feedback(
                event["event_id"], "fact", value, permission="record",
                key=key, scope="session")
            runtime.memory.candidate(mid, runtime.session)
            mids.append(mid)
        current = runtime.store.event(runtime.session, item["current"])
        report["source_sha256"] = item["source_sha256"]
        report["current_ref_sha256"] = sha(dumps(current["source_ref"]).encode())
        report["source_ids"] = mids
        save()

        def generate(messages, schema):
            if schema != guard.SCHEMA or [m["role"] for m in messages] != ["system", "user"]:
                raise ValueError("RUN117CY_SCHEMA_OR_ROLE_RED")
            payload = json.loads(messages[1]["content"])
            if (payload.get("typed_jef_action_visible") is not False
                    or any(k in payload for k in (
                        "oracle", "expected_action", "suggested_action", "typed_jef_action"))):
                raise ValueError("RUN117CY_ORACLE_LEAK_RED")
            report["messages_sha256"] = sha(dumps(messages).encode())
            report["messages"] = messages
            save()
            native = runner_factory(installed, "C3_LANGUAGE", model, CONFIG)
            proc = None
            try:
                report["native_c3_calls"] += 1
                save()
                for chunk in native.generate(
                    messages, threading.Event(), time.monotonic() + 120,
                    96, schema, seed=SEED):
                    if type(chunk) is not str:
                        raise TypeError("RUN117CY_NONSTRING_CHUNK_RED")
                    report["native_output"] += chunk
                    save()
                report["native_metrics"] = dict(native.last_metrics)
                report["native_final"] = report["native_metrics"].get("status") == "FINAL"
                return report["native_output"]
            except Exception as exc:
                report["callback_error_type"] = type(exc).__name__
                raise
            finally:
                try:
                    proc = native.proc
                    report["native_release"] = native.unload()
                    report["process_reaped"] = (
                        proc is not None and proc.poll() is not None
                        and report["native_release"].get("process_reaped") is True)
                except Exception as exc:
                    report["native_release_error_type"] = type(exc).__name__
                save()

        report["guard"] = guard.invoke(
            runtime.memory, runtime.session, current["event_id"],
            current["source_ref"], mids, generate, operator_opt_in=True)
        report["source_rechecked"] = report["guard"].get("source_rechecked") is True
        report["offline_exact"] = bool(frozen.strict(
            report["native_output"], item["expected_for_offline_scorer_only"]))
        report["raw_sha256"] = sha(report["native_output"].encode())
        report["no_live_output"] = (
            runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0
            and runtime.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"] == 0)
    except BaseException as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:250]
    finally:
        if runtime is not None:
            try:
                runtime.close()
                report["closed_store_ok"] = audit_closed(home)["ok"] is True
            except Exception as exc:
                report["close_error_type"] = type(exc).__name__
        try:
            report["pins_unchanged"] = pin_factory(installed) == model
        except Exception:
            report["pins_unchanged"] = False
        report["status"] = (
            "NATIVE_SOURCE_CALLBACK_STRUCTURAL_COMPLETE_NONPROMOTING"
            if report["native_c3_calls"] == 1
            and report["native_final"] and report["process_reaped"]
            and report["source_rechecked"] and report["closed_store_ok"]
            and report.get("no_live_output") is True
            and report["native_metrics"].get("actual_model") == MODEL_FILE
            and report["pins_unchanged"]
            and report["guard"]["status"] in (
                guard.READY, "MODEL_OUTPUT_INVALID_RED")
            and report["error_type"] is None
            else "STRUCTURAL_RED")
        save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--installed", type=Path, required=True)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = run(a.installed, a.home, a.out)
    print(dumps({"status": result["status"],
                 "native_c3_calls": result["native_c3_calls"],
                 "native_final": result["native_final"],
                 "process_reaped": result["process_reaped"],
                 "guard_status": (result["guard"] or {}).get("status")}))
    return 0 if result["status"] != "STRUCTURAL_RED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
