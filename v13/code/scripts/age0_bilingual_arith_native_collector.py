"""Serial real Runtime collector for the frozen bilingual Age0 heldout cohort.

No native inference happens on import or in unit tests. Only an explicit call to
run() with an already bootstrapped, isolated home may launch model processes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

from scripts.age0_bilingual_arith_scorer import (
    BASELINE_PROMPT, CANDIDATE_PROMPT, CATALOG_BLOB, ROLE_MODELS,
    _git_blob, evaluate, fixture,
)
from v13.common import APP, file_hash

MODEL_ROLES = ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
C2_SHA = "c9d915eca282ed42d1a09b143b592adb4cc6744ffe2d294adf5cfc5548170c38"


def preflight(home, prompt_blob):
    """Check immutable source/model identity before the first native call."""
    from v13.models import ModelManager
    if prompt_blob not in (BASELINE_PROMPT, CANDIDATE_PROMPT):
        raise ValueError("Unregistered prompt cohort")
    if _git_blob((APP / "specs/models.json").read_bytes()) != CATALOG_BLOB:
        raise ValueError("Frozen model catalog drift")
    if _git_blob((APP / "v13/prompts.py").read_bytes()) != prompt_blob:
        raise ValueError("Prompt source differs from selected cohort")
    settings = json.loads((home / "config/settings.json").read_text())
    if (settings.get("learning_mode") != "RECORD_ONLY"
            or settings.get("system_stage") != 0
            or settings.get("jepa_weight", 0) != 0
            or settings.get("latents_enabled", False)):
        raise ValueError("Age0 authority/config mismatch")
    if settings.get("b2_control", "two_body") != "two_body":
        raise ValueError("Shared-body control is a separate cohort")
    manager = ModelManager(home, b2_control="two_body")
    verified = manager.verify(deep=True)
    if not all(verified.get(k, {}).get("ok") and verified[k].get("hash_checked")
               for k in ("needle", "language", "body", "gist")):
        raise ValueError("Installed model integrity unavailable")
    for role, want in ROLE_MODELS.items():
        if file_hash(manager.path_for(role)) != want:
            raise ValueError("Pinned role model mismatch: " + role)
    if file_hash(manager.path_for("C2_CONTROL")) != C2_SHA:
        raise ValueError("Pinned C2 model mismatch")
    source = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=APP.parents[1], text=True).strip()
    if len(source) != 40 or any(ch not in "0123456789abcdef" for ch in source):
        raise ValueError("Cannot bind source commit")
    return source


def row_from_message(item, message):
    """Read actual persisted answer metadata; no synthetic success defaults."""
    meta = json.loads(message["metadata"]) if message else {}
    runner = meta.get("runner") or {}
    role = runner.get("role") if isinstance(runner, dict) else None
    return {
        "id": item["id"], "prompt": item["prompt"],
        "answer": message["text"] if message else "",
        "status": message["status"] if message else "MISSING",
        "runner_role": role,
        "runner_model_sha256": ROLE_MODELS.get(role),
        "tool_call": meta.get("tool_call"),
        "tool_shadow": meta.get("tool_shadow"),
        "learning_mode": "RECORD_ONLY",
        "jepa_weight": 0,
    }


def _append_fsynced(path, obj):
    with open(path, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _atomic_json(path, obj):
    tmp = path.with_name(path.name + ".partial")
    with open(tmp, "x", encoding="utf-8") as stream:
        json.dump(obj, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    # Hardlink publish is atomic and refuses an existing destination; unlike
    # os.replace it cannot silently overwrite earlier evidence.
    os.link(tmp, path)
    tmp.unlink()


def collect(home, out, prompt_blob, seconds=120):
    from v13.runtime import Runtime
    home, out = Path(home), Path(out)
    if out.exists():
        raise FileExistsError("Fresh output directory required")
    if not 10 <= seconds <= 240:
        raise ValueError("Turn timeout must be 10..240 seconds")
    source = preflight(home, prompt_blob)
    items = fixture()
    out.mkdir(parents=True)
    raw_path = out / "RAW_ROWS.jsonl"
    manifest_path = out / "ANSWERS.json"
    started = time.monotonic()
    rows = []
    runtime = None
    try:
        runtime = Runtime(home)
        if (runtime.cfg.get("learning_mode") != "RECORD_ONLY"
                or runtime.cfg.get("system_stage") != 0
                or runtime.cfg.get("jepa_weight", 0) != 0
                or runtime.cfg.get("latents_enabled", False)):
            raise ValueError("Live Age0 authority drift")
        for item in items:
            if not runtime.idle():
                raise RuntimeError("Previous turn still active")
            runtime.session = runtime.store.new_session("heldout-" + item["id"])
            runtime.cfg["answer_language"] = item["lang"]
            eid = None
            error = None
            t0 = time.monotonic()
            try:
                eid = runtime.submit(item["prompt"])
                while not runtime.idle() and time.monotonic() - t0 < seconds:
                    time.sleep(.05)
                if not runtime.idle():
                    runtime.cancel()
                    deadline = time.monotonic() + 15
                    while not runtime.idle() and time.monotonic() < deadline:
                        time.sleep(.05)
                    error = "TURN_TIMEOUT_CANCELLED"
                    if not runtime.idle():
                        raise RuntimeError("Native turn did not reap after cancellation")
            except Exception as exc:
                error = type(exc).__name__ + ":" + str(exc)[:160]
            message = (runtime.store.one(
                "SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",
                (eid,)) if eid else None)
            row = row_from_message(item, message)
            row["learning_mode"] = runtime.cfg.get("learning_mode")
            row["jepa_weight"] = runtime.cfg.get("jepa_weight", 0)
            meta = json.loads(message["metadata"]) if message else {}
            raw = {
                "id": item["id"], "event_id": eid, "lang": item["lang"],
                "prompt": item["prompt"], "answer": row["answer"],
                "answer_sha256": hashlib.sha256(row["answer"].encode()).hexdigest(),
                "status": row["status"], "runner_role": row["runner_role"],
                "runner_model_sha256": row["runner_model_sha256"],
                "metadata": {k: meta.get(k) for k in (
                    "runner", "route", "fallback", "tool_call", "tool_shadow",
                    "action_selection", "model_revision", "turn_stage")},
                "elapsed_s": round(time.monotonic() - t0, 3),
                "error": error,
            }
            _append_fsynced(raw_path, raw)
            rows.append(row)
            if error and not runtime.idle():
                raise RuntimeError("Unreaped native turn; partial raw preserved")
        manifest = {
            "schema": "v13.age0.bilingual_numeric_answers.v1",
            "prompt_git_blob": prompt_blob,
            "source_commit": source,
            "model_catalog_git_blob": CATALOG_BLOB,
            "rows": rows,
        }
        _atomic_json(manifest_path, manifest)
        score = evaluate(manifest_path)
        _atomic_json(out / "SCORE.json", score)
        report = {
            "schema": "v13.age0.bilingual_numeric_native_capture.v1",
            "evidence_kind": "LINUX_NATIVE_AGE0_IF_VERIFIED",
            "source_commit": source, "prompt_git_blob": prompt_blob,
            "catalog_git_blob": CATALOG_BLOB, "host": platform.platform(),
            "rows": len(rows), "final_rows": sum(r["status"] == "FINAL" for r in rows),
            "elapsed_s": round(time.monotonic() - started, 3),
            "raw_sha256": file_hash(raw_path), "manifest_sha256": file_hash(manifest_path),
            "source_input_unverified_by_scorer": True,
            "same_brain_fresh_sessions_not_global_state_isolation": True,
            "phone_measured": False, "jepa_weight": 0,
            "whole_system_complete": False,
        }
        _atomic_json(out / "CAPTURE_RESULT.json", report)
        return report
    finally:
        if runtime is not None:
            runtime.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--prompt-git-blob", required=True)
    ap.add_argument("--seconds-per-turn", type=int, default=120)
    args = ap.parse_args(argv)
    result = collect(args.home, args.out, args.prompt_git_blob, args.seconds_per_turn)
    print(json.dumps({"evidence_kind": result["evidence_kind"],
                      "final_rows": result["final_rows"], "rows": result["rows"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
