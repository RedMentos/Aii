"""Run13A prospective seed211 32-turn full-task native utility.

New disjoint seed211 cohort. Frozen Run11V score functions and model pins
unchanged; new witness explicitly requires zero observer offers in all arms.
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

from v13.cognition import scaffold_route
from v13.config import initialize, save_config
from v13.models import ModelManager, model_key
from v13.runtime import Runtime
from v13.proofs import audit_event
from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts.c2_strict_native_compat_run12k import classify
from scripts import c2_body_observer_off_run12n as prior12n
from scripts.c2_body_run12n_fulltask_readonly import explicit_faster_claim

SCHEMA = "v13.c2_c3_body.fulltask.run13a.v1"
FIXTURE_SCHEMA = "v13.c2_c3_body.fulltask.run13a.fixture.v1"
FIXTURE_SHA256 = "e6718093ccd83d556019223eca2d5317668d1ada25659519a699aee681a8b97f"
SEED = 211
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "F_NATIVE_AUTO")
ARM_ORDER = tuple(ARMS[i % 4:] + ARMS[:i % 4] for i in range(8))
ROUTES = {a: frozen.ROUTES[a] for a in ARMS}
ROLES = ("needle", "language", "body", "gist")


def fixture_hash(cases):
    return hashlib.sha256(json.dumps(tuple(cases), sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def load_fixture(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases")
    if (data.get("schema") != FIXTURE_SCHEMA or data.get("seed") != SEED
            or type(cases) is not list or len(cases) != 8
            or fixture_hash(cases) != FIXTURE_SHA256):
        raise ValueError("RUN13A_FROZEN_FIXTURE_MISMATCH")
    prior = {frozen.prompt(f) for f in frozen.FIXTURES}
    prior.update(frozen.prompt(f) for f in prior12n.load_fixture(
        Path(__file__).resolve().parents[1] /
        "docs/fixtures/c2_body_observer_off_run12n_20261030.json")["cases"])
    run12m = json.loads((Path(__file__).resolve().parents[1] /
        "docs/fixtures/c2_body_paired_run12m_20261030.json").read_text())
    prior.update(frozen.prompt(f) for f in run12m["cases"])
    projects = set()
    for f in cases:
        if (type(f) is not dict or set(f) != {
                "project", "budget", "a", "a_cost", "a_days",
                "b", "b_cost", "b_days"}
                or type(f["project"]) is not str or not f["project"]
                or f["project"] in projects or f["a"] == f["b"] or f["a_days"] == f["b_days"]
                or any(type(f[k]) is not int for k in (
                    "budget", "a_cost", "a_days", "b_cost", "b_days"))
                or not (0 < f["a_cost"] < f["budget"]
                        and 0 < f["b_cost"] < f["budget"]
                        and f["a_days"] > 0 and f["b_days"] > 0)):
            raise ValueError("RUN13A_SOURCE_SCHEMA")
        projects.add(f["project"])
        p = frozen.prompt(f)
        if p in prior or scaffold_route(p) != "simple":
            raise ValueError("RUN13A_SOURCE_NOT_DISJOINT_OR_SIMPLE")
        for side in ("a", "b"):
            remain = f["budget"] - f[side + "_cost"]
            if re.search(rf"(?<!\d){remain}(?!\d)", p):
                raise ValueError("RUN13A_ANSWER_LEAK")
    return data


def zero_offer_witness(audit, arm, releases, **kwargs):
    """Prospective witness for observer OFF, not a patch to Run11V evidence."""
    original = frozen.row_evidence(audit, arm, releases, **kwargs)
    native_expected = arm == "F_NATIVE_AUTO"
    route = original["route"]
    final_role = original.get("runner_role")
    after_close = kwargs.get("release_capture_phase") == "after_close"
    offer_roles = original["body_offer_roles"]
    native_ok = (not native_expected or (
        kwargs.get("native_alive") is True
        and kwargs.get("native_reaped") is True
        and type(kwargs.get("native_pid")) is int
        and kwargs["native_pid"] > 0
        and original["native_c2_invocation"] is True))
    final_reaped = any(
        type(r) is dict and r.get("role") == final_role
        and r.get("process_reaped") is True for r in releases)
    all_reaped = (type(releases) is list and len(releases) > 0
                  and all(type(r) is dict and r.get("process_reaped") is True
                          for r in releases))
    process_ok = bool(
        after_close and native_ok and final_reaped and all_reaped
        and offer_roles == [])
    original.update({
        "expected_offer_roles": [], "observer_mode": "off",
        "witness_revision": "run12n-zero-offer-prospective-v1",
        "process_release_valid": process_ok,
        "valid_native": bool(
            process_ok and original["route_valid"]
            and original["output_valid"] and original["source_exact"]),
    })
    return original


def full_task_score(fixture, answer, numeric, valid_native):
    """Frozen explicit lexical faster component; no semantic calibration."""
    expected = fixture["a"] if fixture["a_days"] < fixture["b_days"] else fixture["b"]
    claim = (explicit_faster_claim(answer, fixture["a"], fixture["b"])
             if valid_native else "ABSTAIN")
    status = ("INVALID_NATIVE" if not valid_native else
              "ABSTAIN" if claim == "ABSTAIN" else
              "CONTRADICTORY" if claim == "CONTRADICTORY" else
              "CORRECT" if claim == expected else "WRONG")
    correct = status == "CORRECT"
    return {"expected": expected, "claim": claim, "status": status,
            "component_points": numeric["correct"] + int(correct),
            "strict_full": bool(numeric["correct"] == 2 and correct)}


def fresh_turn(base_home, base_cfg, fixture, arm, index, out):
    """Real Runtime API; fresh Store and native workers for each frozen arm."""
    text = frozen.prompt(fixture)
    with tempfile.TemporaryDirectory(
            dir=base_home / "tmp", prefix="c2-body-seed211-") as td:
        home = Path(td)
        cfg = initialize(home)
        cfg.update(base_cfg)
        cfg.update(
            learning_mode="RECORD_ONLY", system_stage=0, user_stage_cap=0,
            teacher_enabled=False, latents_enabled=False, jepa_weight=0,
            seed=SEED, history_turns=0, route_override=ROUTES[arm],
            observer_mode="off", b2_control="two_body", control_seconds=20.0)
        save_config(home, cfg)
        for name in ("models", "bin"):
            shutil.rmtree(home / name)
            (home / name).symlink_to(
                base_home / name, target_is_directory=True)
        shutil.copyfile(base_home / "config/models.json",
                        home / "config/models.json")
        runtime = Runtime(home)
        if runtime.models.b2_control != "two_body":
            runtime.close()
            raise ValueError("B2_CONTROL_CONFIG_MISMATCH")
        if (model_key("B1_DETAIL", runtime.models.b2_control)
                == model_key("B2_GIST", runtime.models.b2_control)):
            runtime.close()
            raise ValueError("BODY_MODEL_IDENTITY_MISMATCH")
        record = None
        needle_proc = None
        try:
            if arm == "A_C3_ONLY":
                runtime.models.installed.pop("body", None)
                runtime.models.installed.pop("gist", None)
                runtime.models.save()
            event_id = runtime.submit(text)
            deadline = (time.monotonic() + runtime.cfg["deadline_seconds"]
                        + 2 * runtime.cfg["observer_seconds"] + 15)
            while not runtime.idle():
                if time.monotonic() > deadline:
                    runtime.cancel()
                    raise TimeoutError("RUN13A_NATIVE_TURN_DEADLINE")
                time.sleep(0.05)
            audit = audit_event(runtime.store, event_id)
            meta = audit.get("output_metadata") or {}
            route_info = meta.get("route") or {}
            context_id = route_info.get("executive_control_context_id")
            packet = (runtime.store.one(
                "SELECT payload FROM packets "
                "WHERE id=? AND kind='ExecutiveControlContext'",
                (context_id,)) if context_id else None)
            context = json.loads(packet["payload"]) if packet else None
            source_exact = bool(
                context and runtime.store.read_source(context["query_ref"]) == text)
            needle_proc = runtime.needle.proc
            needle_alive = bool(
                needle_proc is not None and needle_proc.poll() is None)
            record = {
                "index": index, "fixture": fixture["project"], "arm": arm,
                "prompt": text, "session_id": runtime.session,
                "event_id": event_id, "seed": SEED, "observer_mode": "off",
                "native_c2_pid": needle_proc.pid if needle_proc else None,
                "native_c2_alive_before_close": needle_alive,
                "source_exact_before_close": source_exact,
                "context_packet": context,
                "body_process_releases_before_close":
                    list(runtime.pool.release_history),
                "raw_audit": audit, "route_info": route_info,
                "final_output": audit.get("output", ""),
            }
        finally:
            # Durable original preclose witness, even if close later fails.
            if record is not None:
                (out / "preclose" / f"{index:02d}_{arm}.json").write_text(
                    json.dumps(record, sort_keys=True,
                               ensure_ascii=False, allow_nan=False) + "\n")
            runtime.close()
        if record is None:
            raise ValueError("RUN13A_PRECLOSE_WITNESS_MISSING")
        after = list(runtime.pool.release_history)
        c2_reaped = bool(
            needle_proc is not None and needle_proc.poll() is not None)
        flags = zero_offer_witness(
            record["raw_audit"], arm, after,
            native_context=record["context_packet"],
            native_alive=record["native_c2_alive_before_close"],
            native_reaped=c2_reaped,
            native_pid=record["native_c2_pid"],
            source_exact=record["source_exact_before_close"],
            session=record["session_id"], event_id=record["event_id"],
            source_text=text, release_capture_phase="after_close")
        output = str(record["final_output"] or "")
        score = (frozen.score_pair(fixture, output)
                 if flags["valid_native"] else
                 {"a": False, "b": False, "correct": 0, "out_of": 2})
        secondary = (frozen.score_primary(fixture, output)
                     if flags["valid_native"] else
                     {"a": False, "b": False, "correct": 0, "out_of": 2})
        full_task = full_task_score(fixture, output, score, flags["valid_native"])
        raw = {
            **record, "body_process_releases": after,
            "native_c2_process_reaped": c2_reaped,
            "release_capture_phase": "after_close",
            "flags": flags, "score": score,
            "secondary_score": secondary, "full_task": full_task,
            "learning_mode": "RECORD_ONLY",
            "jepa_weight": 0,
            "step2_gate_promoted": False, "b3_promoted": False,
            "body_jepa_available": False, "redmi_measured": False,
            "whole_system_complete": False,
        }
        (out / "raw" / f"{index:02d}_{arm}.json").write_text(
            json.dumps(raw, sort_keys=True,
                       ensure_ascii=False, allow_nan=False) + "\n")
        return {k: v for k, v in raw.items()
                if k not in ("raw_audit", "context_packet", "prompt",
                             "route_info")}


def summarize(rows):
    totals = {a: sum(r.get("score", {}).get("correct", 0)
                     for r in rows if r.get("arm") == a) for a in ARMS}
    secondary = {a: sum(r.get("secondary_score", {}).get("correct", 0)
                        for r in rows if r.get("arm") == a) for a in ARMS}
    full = {a: sum(r.get("full_task", {}).get("strict_full") is True
                   for r in rows if r.get("arm") == a) for a in ARMS}
    components = {a: sum(r.get("full_task", {}).get("component_points", 0)
                         for r in rows if r.get("arm") == a) for a in ARMS}
    frows = [r for r in rows if r.get("arm") == "F_NATIVE_AUTO"]
    invoked = sum(r.get("flags", {}).get("native_c2_invocation") is True for r in frows)
    strict = sum(r.get("strict_admission", {}).get("matches") is True for r in frows)
    changed = sum(r.get("flags", {}).get("native_c2_selected") is True for r in frows)
    valid = bool(len(rows) == 32 and len(frows) == 8
                 and all(sum(r.get("arm") == a for r in rows) == 8 for a in ARMS)
                 and invoked == 8
                 and strict == 8 and all(
                     r.get("flags", {}).get("valid_native") is True
                     and r["flags"].get("body_offer_roles") == []
                     and r["flags"].get("expected_offer_roles") == []
                     and r["flags"].get("observer_mode") == "off" for r in rows))
    signal = bool(valid and changed >= 2
                  and totals["F_NATIVE_AUTO"] >= max(totals[a] for a in ARMS[:3]) + 3
                  and full["F_NATIVE_AUTO"] >= max(full[a] for a in ARMS[:3]) + 2)
    return {
        "status": "PILOT_COMPLETE_NO_GATE" if valid else "PILOT_PARTIAL_RED",
        "score_totals_out_of_16": totals,
        "secondary_totals_out_of_16": secondary,
        "component_totals_out_of_24": components,
        "strict_full_totals_out_of_8": full,
        "native_c2_invocations": invoked,
        "native_c2_strict_matches": strict,
        "native_c2_changed_routes": changed,
        "all_native_structurally_valid": valid,
        "native_auto_utility_pilot_signal_not_gate": signal,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "redmi_measured": False,
        "whole_system_complete": False, "comparative_utility_proven": False,
        "jepa_weight": 0, "learning_mode": "RECORD_ONLY",
    }


def run(home, out, fixture_path):
    home, out = Path(home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_DIRECTORY_REQUIRED")
    fixture = load_fixture(fixture_path)
    out.mkdir(parents=True)
    (out / "raw").mkdir()
    (out / "preclose").mkdir()
    report = {
        "schema": SCHEMA, "seed": SEED,
        "fixture_sha256": FIXTURE_SHA256,
        "fixtures": fixture["cases"], "arms": ARMS,
        "arm_order": ARM_ORDER, "rows": [],
        "model_verification": {}, "status": "INCOMPLETE",
    }
    try:
        cfg = initialize(home)
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg["latents_enabled"] or cfg.get("jepa_weight", 0) != 0):
            raise ValueError("BASE_NOT_AGE0")
        verified = ModelManager(home).verify(deep=True)
        if not all(verified.get(k, {}).get("ok") is True
                   and verified[k].get("hash_checked") is True for k in ROLES):
            raise ValueError("MODEL_PINS_UNVERIFIED")
        report["model_verification"] = {
            k: {"ok": True, "hash_checked": True} for k in ROLES}
        for i, f in enumerate(fixture["cases"]):
            for arm in ARM_ORDER[i]:
                index = len(report["rows"])
                try:
                    row = fresh_turn(home, cfg, f, arm, index, out)
                    if arm == "F_NATIVE_AUTO":
                        raw = json.loads((out / "raw" / f"{index:02d}_{arm}.json").read_text())
                        row["strict_admission"] = classify({
                            "route_info": raw["route_info"],
                            "route": raw["flags"]["route"]})
                        (out / "raw" / f"{index:02d}_STRICT_ADMISSION.json").write_text(
                            json.dumps(row["strict_admission"], sort_keys=True,
                                       allow_nan=False) + "\n")
                except BaseException as exc:
                    traceback.print_exc()
                    row = {"index": index, "fixture": f["project"], "arm": arm,
                           "error_type": type(exc).__name__,
                           "error": str(exc)[:240],
                           "flags": {"valid_native": False,
                                     "native_c2_invocation": False},
                           "score": {"a": False, "b": False,
                                     "correct": 0, "out_of": 2},
                           "full_task": full_task_score(
                               f, "", {"correct": 0}, False)}
                    raw_path = out / "raw" / f"{index:02d}_{arm}.json"
                    if not raw_path.exists():
                        raw_path.write_text(
                            json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                    else:
                        (out / "raw" / f"{index:02d}_{arm}_WRAPPER_ERROR.json").write_text(
                            json.dumps({"error_type": type(exc).__name__,
                                        "error": str(exc)[:240]},
                                       sort_keys=True, allow_nan=False) + "\n")
                report["rows"].append(row)
                (out / "progress.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True,
                               allow_nan=False) + "\n")
        report.update(summarize(report["rows"]))
    except BaseException as exc:
        traceback.print_exc()
        report.update(summarize(report["rows"]))
        report["status"] = "PILOT_SETUP_ERROR"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:240]
    finally:
        (out / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True,
                       allow_nan=False) + "\n")
    print(json.dumps({
        "status": report["status"],
        "totals": report["score_totals_out_of_16"],
        "strict_full": report["strict_full_totals_out_of_8"],
        "native_auto_signal": report["native_auto_utility_pilot_signal_not_gate"],
    }, sort_keys=True))
    return report["all_native_structurally_valid"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args()
    return 0 if run(a.home, a.out, a.fixture) else 2


if __name__ == "__main__":
    raise SystemExit(main())
