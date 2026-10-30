"""Run12N prospective observer-OFF C2/C3/B1/B2 native utility.

New disjoint seed197 cohort. Frozen Run11V score functions and model pins
unchanged; new witness explicitly requires zero observer offers in all arms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import traceback

from v13.cognition import scaffold_route
from v13.config import initialize
from v13.models import ModelManager
from v13.runtime import Runtime
from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts.c2_strict_native_compat_run12k import classify

SCHEMA = "v13.c2_c3_body.observer_off.run12n.v1"
FIXTURE_SCHEMA = "v13.c2_c3_body.observer_off.run12n.fixture.v1"
FIXTURE_SHA256 = "94cce591dcf9ade126cfdb2d32261543c8334523b6d268295759d9ef7b691df1"
SEED = 197
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "F_NATIVE_AUTO")
ARM_ORDER = tuple(ARMS[i:] + ARMS[:i] for i in range(4))
ROUTES = {a: frozen.ROUTES[a] for a in ARMS}
ROLES = ("needle", "language", "body", "gist")


def fixture_hash(cases):
    return hashlib.sha256(json.dumps(tuple(cases), sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def load_fixture(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases")
    if (data.get("schema") != FIXTURE_SCHEMA or data.get("seed") != SEED
            or type(cases) is not list or len(cases) != 4
            or fixture_hash(cases) != FIXTURE_SHA256):
        raise ValueError("RUN12N_FROZEN_FIXTURE_MISMATCH")
    prior = {frozen.prompt(f) for f in frozen.FIXTURES}
    projects = set()
    for f in cases:
        if (type(f) is not dict or set(f) != {
                "project", "budget", "a", "a_cost", "a_days",
                "b", "b_cost", "b_days"}
                or type(f["project"]) is not str or not f["project"]
                or f["project"] in projects or f["a"] == f["b"]
                or any(type(f[k]) is not int for k in (
                    "budget", "a_cost", "a_days", "b_cost", "b_days"))
                or not (0 < f["a_cost"] < f["budget"]
                        and 0 < f["b_cost"] < f["budget"]
                        and f["a_days"] > 0 and f["b_days"] > 0)):
            raise ValueError("RUN12N_SOURCE_SCHEMA")
        projects.add(f["project"])
        p = frozen.prompt(f)
        if p in prior or scaffold_route(p) != "simple":
            raise ValueError("RUN12N_SOURCE_NOT_DISJOINT_OR_SIMPLE")
        for side in ("a", "b"):
            remain = f["budget"] - f[side + "_cost"]
            if re.search(rf"(?<!\d){remain}(?!\d)", p):
                raise ValueError("RUN12N_ANSWER_LEAK")
    return data


def zero_offer_witness(audit, arm, releases, **kwargs):
    """Prospective witness for observer OFF, not a patch to Run11V evidence."""
    original = frozen.row_evidence(audit, arm, releases, **kwargs)
    native_expected = arm == "F_NATIVE_AUTO"
    route = original["route"]
    final_role = frozen.ROLE_BY_ROUTE.get(route)
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


def fresh_turn(home, cfg, fixture, arm, index, out):
    turn_cfg = dict(cfg)
    turn_cfg.update(seed=SEED, route_override=ROUTES[arm],
                    observer_mode="off", learning_mode="RECORD_ONLY")
    session = f"run12n-{fixture['project']}-{arm}-{SEED}"
    text = frozen.prompt(fixture)
    runtime = Runtime(home, turn_cfg)
    audit = None
    preclose = None
    raw_path = out / "raw" / f"{index:02d}_{arm}.json"
    preclose_path = out / "preclose" / f"{index:02d}_{arm}.json"
    try:
        runtime.start()
        audit = runtime.submit(text, session_id=session)
        before = frozen.release_rows(runtime)
        c2_pid = runtime.c2_worker.process.pid if runtime.c2_worker.process else None
        c2_alive = bool(runtime.c2_worker.process and
                        runtime.c2_worker.process.poll() is None)
        context = dict(audit.get("c2_packet") or {})
        source_exact = frozen.source_ok(audit, text, session)
        preclose = {
            "index": index, "fixture": fixture["project"], "arm": arm,
            "prompt": text, "session_id": session,
            "event_id": audit.get("event_id"),
            "seed": SEED, "observer_mode": "off",
            "native_c2_pid": c2_pid,
            "native_c2_alive_before_close": c2_alive,
            "source_exact_before_close": source_exact,
            "context_packet": context,
            "body_process_releases_before_close": before,
            "raw_audit": audit,
            "route_info": audit.get("route_info"),
            "final_output": audit.get("output"),
        }
        preclose_path.write_text(
            json.dumps(preclose, sort_keys=True, allow_nan=False) + "\n")
    finally:
        runtime.close()
    if preclose is None:
        raise RuntimeError("RUN12N_PRECLOSE_WITNESS_MISSING")
    after = frozen.release_rows(runtime)
    c2_reaped = bool(runtime.c2_worker.process is None)
    flags = zero_offer_witness(
        audit, arm, after,
        native_context=preclose["context_packet"],
        native_alive=preclose["native_c2_alive_before_close"],
        native_reaped=c2_reaped,
        native_pid=preclose["native_c2_pid"],
        source_exact=preclose["source_exact_before_close"],
        session=session, event_id=preclose["event_id"],
        source_text=text, release_capture_phase="after_close")
    output = str(audit.get("output") or "")
    score = (frozen.score_pair(fixture, output) if flags["valid_native"]
             else {"a": False, "b": False, "correct": 0, "out_of": 2})
    secondary = (frozen.score_primary(fixture, output) if flags["valid_native"]
                 else {"a": False, "b": False, "correct": 0, "out_of": 2})
    record = {
        **preclose, "body_process_releases": after,
        "native_c2_process_reaped": c2_reaped,
        "release_capture_phase": "after_close",
        "flags": flags, "score": score,
        "secondary_score": secondary, "learning_mode": "RECORD_ONLY",
        "jepa_weight": 0,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "redmi_measured": False,
        "whole_system_complete": False,
    }
    raw_path.write_text(json.dumps(record, sort_keys=True,
                                   allow_nan=False) + "\n")
    return {k: v for k, v in record.items()
            if k not in ("raw_audit", "context_packet", "prompt", "route_info")}


def summarize(rows):
    totals = {arm: sum(r.get("score", {}).get("correct", 0)
                       for r in rows if r.get("arm") == arm)
              for arm in ARMS}
    secondary = {arm: sum(r.get("secondary_score", {}).get("correct", 0)
                          for r in rows if r.get("arm") == arm)
                 for arm in ARMS}
    frows = [r for r in rows if r.get("arm") == "F_NATIVE_AUTO"]
    invoked = sum(r.get("flags", {}).get("native_c2_invocation") is True
                  for r in frows)
    strict = sum(r.get("strict_admission", {}).get("matches") is True
                 for r in frows)
    changed = sum(r.get("flags", {}).get("native_c2_selected") is True
                  for r in frows)
    valid = bool(
        len(rows) == 16 and len(frows) == 4 and invoked == 4
        and strict == 4
        and all(r.get("flags", {}).get("valid_native") is True
                and r["flags"].get("body_offer_roles") == []
                and r["flags"].get("expected_offer_roles") == []
                and r["flags"].get("observer_mode") == "off"
                for r in rows))
    signal = bool(valid and changed >= 1 and
                  totals["F_NATIVE_AUTO"] >=
                  max(totals[a] for a in ARMS[:3]) + 2)
    return {
        "status": "PILOT_COMPLETE_NO_GATE" if valid else "PILOT_PARTIAL_RED",
        "score_totals_out_of_8": totals,
        "secondary_totals_out_of_8": secondary,
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
                                     "correct": 0, "out_of": 2}}
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
        "totals": report["score_totals_out_of_8"],
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
