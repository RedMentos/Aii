"""Seed59 disjoint simple-scaffold C2 native route-selection utility pilot.

Three arms per task: C3 forced simple, genuine native C2 auto, distinct Body
forced both. This is Age0 review-only; no original cohort or gate is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import time
import traceback

from v13.config import initialize, save_config
from v13.cognition import scaffold_route
from v13.models import ModelManager, model_key
from v13.proofs import audit_event
from v13.runtime import Runtime
from scripts.c2_body_controlled_utility_seed53_20261030 import (
    score_pair, row_evidence, pilot_signal as _unused_seed53_signal,
)

SCHEMA = "v13.c2.simple_scaffold.native_utility.seed59.v1"
SEED = 59
ARMS = ("A_FORCED_SIMPLE", "B_NATIVE_AUTO", "C_FORCED_BOTH")
ARM_ORDER = tuple(ARMS[i % 3:] + ARMS[:i % 3] for i in range(4))
ROUTES = {"A_FORCED_SIMPLE": "simple", "B_NATIVE_AUTO": "auto",
          "C_FORCED_BOTH": "both"}
EVIDENCE_ARM = {"A_FORCED_SIMPLE": "A_C3_ONLY", "B_NATIVE_AUTO": "F_NATIVE_AUTO",
                "C_FORCED_BOTH": "D_DISTINCT_BOTH"}
FIXTURES = (
    {"project": "Marlow59", "budget": 375, "a": "Citrine", "a_cost": 218,
     "a_days": 6, "b": "Sparrow", "b_cost": 332, "b_days": 3},
    {"project": "Peregrine59", "budget": 294, "a": "Nectar", "a_cost": 183,
     "a_days": 2, "b": "Saffron", "b_cost": 267, "b_days": 7},
    {"project": "Lantern59", "budget": 418, "a": "Beryl", "a_cost": 259,
     "a_days": 8, "b": "Cypress", "b_cost": 386, "b_days": 4},
    {"project": "Tide59", "budget": 236, "a": "Mistral", "a_cost": 174,
     "a_days": 5, "b": "Hearth", "b_cost": 211, "b_days": 9},
)
FIXTURE_SHA256 = "610b7b1c2b2d203b6388a7717394cd9c7c8460f434509167286e7bf7a972e651"


def fixture_hash():
    return hashlib.sha256(json.dumps(FIXTURES, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def prompt(f):
    return (f"For {f['project']}, I have a spending ceiling of {f['budget']} Euro. "
            f"{f['a']} uses {f['a_cost']} Euro and needs {f['a_days']} days. "
            f"{f['b']} uses {f['b_cost']} Euro and needs {f['b_days']} days. "
            "Everything stays local on my device; no cloud. How many Euro "
            "would remain after each named choice, and which one finishes sooner?")


def validate_fixtures():
    if fixture_hash() != FIXTURE_SHA256 or len(FIXTURES) != 4:
        raise ValueError("FIXTURE_PIN_CHANGED")
    if len({f["project"] for f in FIXTURES}) != 4:
        raise ValueError("DUPLICATE_PROJECT")
    for f in FIXTURES:
        if not (0 < f["a_cost"] < f["budget"] and 0 < f["b_cost"] < f["budget"]
                and f["a"] != f["b"] and f["a_days"] != f["b_days"]):
            raise ValueError("INVALID_FIXTURE")
        p = prompt(f)
        if scaffold_route(p) != "simple":
            raise ValueError("SCAFFOLD_NOT_SIMPLE")
        for remainder in (f["budget"] - f["a_cost"], f["budget"] - f["b_cost"]):
            if re.search(rf"(?<!\d){remainder}(?!\d)", p):
                raise ValueError("ANSWER_LEAKED_IN_PROMPT")
    return True


def pilot_signal(totals, valid, selected):
    if (type(valid) is not bool or type(selected) is not int or not 0 <= selected <= 4
            or type(totals) is not dict or set(totals) != set(ARMS)
            or any(type(x) is not int or not 0 <= x <= 8 for x in totals.values())):
        return False
    return bool(valid and selected >= 1
                and totals["B_NATIVE_AUTO"] >= totals["A_FORCED_SIMPLE"] + 2
                and totals["B_NATIVE_AUTO"] >= totals["C_FORCED_BOTH"])


def fresh_turn(base_home, base_cfg, fixture, arm, index, out):
    text = prompt(fixture)
    with tempfile.TemporaryDirectory(dir=base_home / "tmp",
                                     prefix="c2-simple-seed59-") as td:
        home = Path(td)
        cfg = initialize(home)
        cfg.update(base_cfg)
        cfg.update(learning_mode="RECORD_ONLY", system_stage=0, user_stage_cap=0,
                   teacher_enabled=False, latents_enabled=False, jepa_weight=0,
                   seed=SEED, history_turns=0, route_override=ROUTES[arm],
                   observer_mode=("off" if arm == "A_FORCED_SIMPLE" else "background"),
                   b2_control="two_body", control_seconds=20.0)
        save_config(home, cfg)
        for name in ("models", "bin"):
            shutil.rmtree(home / name)
            (home / name).symlink_to(base_home / name, target_is_directory=True)
        shutil.copyfile(base_home / "config/models.json", home / "config/models.json")
        runtime = Runtime(home)
        record = None
        proc = None
        try:
            if runtime.models.b2_control != "two_body":
                raise ValueError("B2_CONTROL_CHANGED")
            if arm == "A_FORCED_SIMPLE":
                runtime.models.installed.pop("body", None)
                runtime.models.installed.pop("gist", None)
                runtime.models.save()
            event_id = runtime.submit(text)
            end = time.monotonic() + runtime.cfg["deadline_seconds"] + 2 * runtime.cfg["observer_seconds"] + 15
            while not runtime.idle():
                if time.monotonic() > end:
                    runtime.cancel()
                    raise TimeoutError("NATIVE_SIMPLE_TURN_DEADLINE")
                time.sleep(.05)
            audit = audit_event(runtime.store, event_id)
            meta = audit.get("output_metadata") or {}
            route_info = meta.get("route") or {}
            context_id = route_info.get("executive_control_context_id")
            row = (runtime.store.one("SELECT payload FROM packets WHERE id=? AND kind='ExecutiveControlContext'",
                                     (context_id,)) if context_id else None)
            context = json.loads(row["payload"]) if row else None
            source_exact = bool(context and runtime.store.read_source(context["query_ref"]) == text)
            proc = runtime.needle.proc
            alive = proc is not None and proc.poll() is None
            releases = list(runtime.pool.release_history)
            record = {"index": index, "fixture": fixture["project"], "arm": arm,
                      "prompt": text, "event_id": event_id, "session_id": runtime.session,
                      "scaffold_route": scaffold_route(text), "route_info": route_info,
                      "context_packet": context, "raw_audit": audit,
                      "body_process_releases": releases,
                      "final_output": audit.get("output", ""),
                      "b2_control": runtime.models.b2_control,
                      "b1_model_key": model_key("B1_DETAIL", runtime.models.b2_control),
                      "b2_model_key": model_key("B2_GIST", runtime.models.b2_control),
                      "b1_revision": runtime.models.revision("B1_DETAIL"),
                      "b2_revision": runtime.models.revision("B2_GIST"),
                      "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                      "step2_gate_promoted": False, "b3_promoted": False,
                      "body_jepa_available": False, "redmi_measured": False,
                      "whole_system_complete": False,
                      "_needle_alive": alive, "_source_exact": source_exact}
        finally:
            runtime.close()
        if record is None:
            raise ValueError("MISSING_NATIVE_ROW")
        reaped = bool(proc is not None and proc.poll() is not None)
        record["native_c2_process_reaped"] = reaped
        record["native_c2_pid"] = proc.pid if proc is not None else None
        flags = row_evidence(record["raw_audit"], EVIDENCE_ARM[arm],
                             record["body_process_releases"],
                             native_context=record["context_packet"],
                             native_alive=record.pop("_needle_alive"),
                             native_reaped=reaped, native_pid=record["native_c2_pid"],
                             source_exact=record.pop("_source_exact"),
                             session=record["session_id"], event_id=record["event_id"],
                             source_text=text)
        record["flags"] = flags
        record["score"] = (score_pair(fixture, record["final_output"])
                           if flags["valid_native"] else {"a": False, "b": False,
                                                         "correct": 0, "out_of": 2})
        (out / "raw" / f"{index:02d}_{arm}.json").write_text(
            json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
        return {k: v for k, v in record.items() if k not in
                ("raw_audit", "context_packet", "prompt", "route_info")}


def run(base_home, out):
    base_home, out = Path(base_home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_DIRECTORY_REQUIRED")
    validate_fixtures()
    out.mkdir(parents=True)
    (out / "raw").mkdir()
    report = {"schema": SCHEMA, "status": "INCOMPLETE", "seed": SEED,
              "fixture_sha256": FIXTURE_SHA256, "fixtures": FIXTURES,
              "arms": ARMS, "arm_order": ARM_ORDER, "rows": [],
              "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
              "step2_gate_promoted": False, "b3_promoted": False,
              "body_jepa_available": False, "redmi_measured": False,
              "whole_system_complete": False, "comparative_utility_proven": False,
              "claim_limit": "12-turn small Linux-native route pilot, not STEP2 gate"}
    try:
        cfg = initialize(base_home)
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg["latents_enabled"] or cfg.get("jepa_weight", 0) != 0):
            raise ValueError("BASE_NOT_AGE0")
        verified = ModelManager(base_home).verify(deep=True)
        roles = ("needle", "language", "body", "gist")
        if not all(verified.get(k, {}).get("ok") is True
                   and verified[k].get("hash_checked") is True for k in roles):
            raise ValueError("MODEL_PINS_UNVERIFIED")
        report["model_verification"] = {
            k: {"ok": verified[k]["ok"], "hash_checked": verified[k]["hash_checked"]}
            for k in roles}
        for i, fixture in enumerate(FIXTURES):
            for arm in ARM_ORDER[i]:
                index = len(report["rows"])
                try:
                    row = fresh_turn(base_home, cfg, fixture, arm, index, out)
                except BaseException as exc:
                    traceback.print_exc()
                    row = {"index": index, "fixture": fixture["project"], "arm": arm,
                           "error_type": type(exc).__name__, "error": str(exc)[:320],
                           "flags": {"valid_native": False, "native_c2_invocation": False,
                                     "native_c2_selected": False},
                           "score": {"a": False, "b": False, "correct": 0, "out_of": 2}}
                    (out / "raw" / f"{index:02d}_{arm}.json").write_text(
                        json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
                report["rows"].append(row)
                (out / "progress.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True,
                               ensure_ascii=False, allow_nan=False) + "\n")
        totals = {arm: sum(row["score"]["correct"] for row in report["rows"]
                           if row["arm"] == arm) for arm in ARMS}
        valid = len(report["rows"]) == 12 and all(
            row["flags"].get("valid_native") is True for row in report["rows"])
        selected = sum(bool(row["flags"].get("native_c2_selected"))
                       for row in report["rows"] if row["arm"] == "B_NATIVE_AUTO")
        report["score_totals_out_of_8"] = totals
        report["native_c2_selected"] = selected
        report["native_c2_invocations"] = sum(
            bool(row["flags"].get("native_c2_invocation"))
            for row in report["rows"] if row["arm"] == "B_NATIVE_AUTO")
        report["pilot_signal_not_gate"] = pilot_signal(totals, valid, selected)
        report["status"] = "PILOT_COMPLETE_NO_GATE" if valid else "PILOT_PARTIAL_RED"
    except BaseException as exc:
        traceback.print_exc()
        report.update(status="PILOT_ERROR", error_type=type(exc).__name__,
                      error=str(exc)[:320])
    finally:
        (out / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True,
                       ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"],
                      "score_totals_out_of_8": report.get("score_totals_out_of_8"),
                      "native_c2_selected": report.get("native_c2_selected", 0),
                      "pilot_signal_not_gate": report.get("pilot_signal_not_gate", False)},
                     sort_keys=True))
    return report["status"] == "PILOT_COMPLETE_NO_GATE"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    return 0 if run(a.home, a.out) else 2


if __name__ == "__main__":
    raise SystemExit(main())
