"""Isolated real Needle/C2 auto-route provenance probe; no C3/Body or gate."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import tempfile
import time
import traceback
from pathlib import Path

from v13.config import initialize, save_config
from v13.models import ModelManager
from v13.runtime import Runtime

SCHEMA = "v13.c2.native_route_provenance_pilot.v1"
SEED = 43
PROMPTS = (
    "Compare two local options and reason about their budget and timing.",
    "Summarize the previous context in one sentence without inventing details.",
    "Hello. Is this a simple greeting?",
)
PROMPT_SHA256 = "c952103c6f36bff983659977783f2b6447264bc72e93f76412a69f91ca1fde25"
ROUTES = frozenset({"simple", "detail", "gist", "both"})


def prompt_hash():
    return hashlib.sha256(json.dumps(PROMPTS, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def valid_control_evidence(event, text, route, info, *, context_packet=None):
    """Conservative software shape check; native truth requires actual raw run."""
    if (type(event) is not dict or type(text) is not str
            or type(route) is not str or route not in ROUTES
            or type(info) is not dict
            or info.get("source") not in {"BOOT_SCAFFOLD", "NATIVE_C2_ADVISORY"}
            or info.get("executive_control_policy") != "LOCAL_PROCESSING_ONLY"
            or "control_unavailable" in info
            or type(info.get("native_control")) is not dict
            or type(info.get("native_control_metrics")) is not dict):
        return False
    m = info["native_control_metrics"]
    if (m.get("role") != "C2_CONTROL" or m.get("operation") != "C"
            or m.get("status") != "FINAL"
            or type(m.get("duration_s")) not in (int, float)
            or not 0 < m["duration_s"] <= 30
            or type(m.get("memory")) is not dict
            or m["memory"].get("measurement_status") != "MEASURED"
            or type(m["memory"].get("pid")) is not int):
        return False
    if (type(context_packet) is not dict
            or context_packet.get("packet_id") !=
                info.get("executive_control_context_id")
            or context_packet.get("session_id") != event.get("session_id")
            or context_packet.get("event_id") != event.get("event_id")
            or context_packet.get("query_ref") != event.get("source_ref")
            or context_packet.get("external_action_authority") is not False):
        return False
    return True


def _turn(base_home, base_cfg, text, index, out):
    with tempfile.TemporaryDirectory(dir=base_home / "tmp",
                                     prefix="c2-route-native-") as td:
        home = Path(td)
        cfg = initialize(home)
        cfg.update(base_cfg)
        cfg.update(learning_mode="RECORD_ONLY", system_stage=0,
                   user_stage_cap=0, teacher_enabled=False,
                   latents_enabled=False, jepa_weight=0,
                   seed=SEED, history_turns=0,
                   route_override="auto", observer_mode="off",
                   control_seconds=20.0)
        save_config(home, cfg)
        for name in ("models", "bin"):
            shutil.rmtree(home / name)
            (home / name).symlink_to(base_home / name, target_is_directory=True)
        shutil.copyfile(base_home / "config/models.json",
                        home / "config/models.json")
        r = Runtime(home)
        proc = None
        try:
            e = r.store.event(r.session, text)
            route, info = r._route(text, e, time.monotonic() + 25.0)
            proc = r.needle.proc
            ctx_id = info.get("executive_control_context_id")
            row = r.store.one(
                "SELECT payload FROM packets WHERE id=? AND kind='ExecutiveControlContext'",
                (ctx_id,)) if ctx_id else None
            context = json.loads(row["payload"]) if row else None
            # Store source identity is checked independently from native text.
            source_exact = r.store.read_source(e["source_ref"]) == text
            # Actual process is retained until after the evidence is read.
            valid = (source_exact and valid_control_evidence(
                {**e, "session_id": r.session}, text, route, info,
                context_packet=context)
                and proc is not None and proc.poll() is None)
            record = {
                "index": index, "prompt": text,
                "event_id": e["event_id"], "session_id": r.session,
                "source_ref": e["source_ref"], "route": route,
                "route_info": info, "context_packet": context,
                "source_exact": source_exact,
                "native_c2_invocation_valid_before_release": bool(valid),
                "native_c2_selected_route": info.get("source") == "NATIVE_C2_ADVISORY",
                "c3_called": False, "body_called": False,
                "no_live_answer": True, "jepa_weight": 0,
            }
            return record
        finally:
            r.needle.unload()
            reaped = proc is not None and proc.poll() is not None
            if 'record' in locals():
                record["needle_process_reaped"] = reaped
                (out / "raw" / f"{index:02d}_C2_ROUTE.json").write_text(
                    json.dumps(record, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n")
            r.close()


def run(base_home, out):
    base_home, out = Path(base_home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_DIRECTORY_REQUIRED")
    if prompt_hash() != PROMPT_SHA256 or len(PROMPTS) != 3:
        raise ValueError("PREREG_PROMPTS_CHANGED")
    out.mkdir(parents=True)
    (out / "raw").mkdir()
    report = {
        "schema": SCHEMA, "status": "INCOMPLETE", "seed": SEED,
        "prompt_sha256": PROMPT_SHA256, "prompts": PROMPTS,
        "rows": [], "native_c2_proven": False,
        "integrated_c2_c3_proven": False, "step2_gate_promoted": False,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "scope": "ISOLATED_C2_ROUTE_ONLY_NO_LIVE_ANSWER",
    }
    try:
        cfg = initialize(base_home)
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg["latents_enabled"] or cfg.get("jepa_weight", 0) != 0):
            raise ValueError("BASE_NOT_AGE0")
        verified = ModelManager(base_home).verify(deep=True)
        if (not verified.get("needle", {}).get("ok")
                or verified["needle"].get("hash_checked") is not True):
            raise ValueError("NEEDLE_NATIVE_PIN_NOT_VERIFIED")
        report["needle_model_verified"] = {
            "ok": verified["needle"]["ok"],
            "hash_checked": verified["needle"]["hash_checked"],
        }
        for i, text in enumerate(PROMPTS):
            try:
                row = _turn(base_home, cfg, text, i, out)
            except BaseException as exc:
                row = {"index": i, "prompt": text,
                       "native_c2_invocation_valid_before_release": False,
                       "needle_process_reaped": False,
                       "error_type": type(exc).__name__,
                       "error": str(exc)[:320]}
                traceback.print_exc()
            report["rows"].append(row)
            (out / "progress.json").write_text(json.dumps(
                report, sort_keys=True, indent=2, ensure_ascii=False,
                allow_nan=False) + "\n")
        report["native_c2_proven"] = all(
            row.get("native_c2_invocation_valid_before_release") is True
            and row.get("needle_process_reaped") is True
            for row in report["rows"]) and len(report["rows"]) == 3
        report["status"] = ("NATIVE_C2_INVOCATION_PROVEN_3_OF_3"
                            if report["native_c2_proven"] else "PARTIAL_RED")
    except BaseException as exc:
        report.update(status="PILOT_ERROR", error_type=type(exc).__name__,
                      error=str(exc)[:320])
        traceback.print_exc()
    finally:
        (out / "report.json").write_text(json.dumps(
            report, sort_keys=True, indent=2, ensure_ascii=False,
            allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"],
                      "native_c2_proven": report["native_c2_proven"],
                      "integrated_c2_c3_proven": False}, sort_keys=True))
    return report["native_c2_proven"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    return 0 if run(args.home, args.out) else 2


if __name__ == "__main__":
    raise SystemExit(main())
